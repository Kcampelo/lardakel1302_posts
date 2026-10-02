"""Instagram carousel publisher. Credentials and mutable state remain local."""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlparse
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "agendamento/fila.json"
STATE = ROOT / "agendamento/estado"
TZ = timezone(timedelta(hours=-3), "America/Sao_Paulo")
MAX_DELAY = 600
ALLOWED_HOST = "raw.githubusercontent.com"

class PublishError(Exception):
    pass

def read_env():
    result = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result

def load(path, default=None):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

@contextmanager
def lock():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "publisher.lock").open("a+b") as f:
        if f.tell() == 0:
            f.write(b"0")
            f.flush()
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise PublishError("Outro executor está em andamento.")
        try:
            yield
        finally:
            f.seek(0)
            if os.name == "nt":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

class API:
    def __init__(self, cfg):
        self.cfg = cfg
        version = cfg.get("META_API_VERSION", "")
        if not re.fullmatch(r"v\d+\.\d+", version):
            raise PublishError("META_API_VERSION inválida.")
        self.base = "https://graph.instagram.com/" + version + "/"
        self.uid = cfg.get("INSTAGRAM_USER_ID", "")
        self.token = cfg.get("INSTAGRAM_ACCESS_TOKEN", "")
        if not self.uid.isdigit() or not self.token:
            raise PublishError("Credenciais incompletas.")

    def request(self, endpoint, params=None, method="GET"):
        params = params or {}
        url = self.base + endpoint
        data = None
        if method == "GET" and params:
            url += "?" + urlencode(params)
        elif method == "POST":
            data = urlencode(params).encode()
        req = Request(url, data=data, method=method,
                      headers={"Authorization": "Bearer " + self.token,
                               "Content-Type": "application/x-www-form-urlencoded",
                               "User-Agent": "LarDaKelPublisher/1.0"})
        try:
            with urlopen(req, timeout=45) as response:
                return json.load(response)
        except HTTPError as e:
            try:
                error = json.loads(e.read()).get("error", {})
            except Exception:
                error = {}
            # Never log raw response, request, token, or exception repr.
            raise PublishError("Meta HTTP %s; code=%s; subcode=%s" %
                               (e.code, error.get("code"), error.get("error_subcode"))) from None
        except (URLError, TimeoutError, OSError):
            raise PublishError("Falha de rede na API Meta; nenhuma credencial foi registrada.") from None

    def check_identity(self):
        me = self.request("me", {"fields": "user_id,username,account_type"})
        if str(me.get("user_id")) != self.uid or me.get("username") != self.cfg["INSTAGRAM_ACCOUNT_USERNAME"]:
            raise PublishError("Identidade da conta divergente; publicação bloqueada.")
        return me

    def ready(self, container):
        for _ in range(12):
            result = self.request(container, {"fields": "status_code"})
            status = result.get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED", "PUBLISHED"):
                raise PublishError("Contêiner não publicável: " + str(status))
            time.sleep(5)
        raise PublishError("Processamento pendente; não publicar.")

def verify_media(job):
    if not 3 <= len(job["images"]) <= 5:
        raise PublishError("Quantidade inesperada de páginas.")
    for media in job["images"]:
        u = urlparse(media["url"])
        if u.scheme != "https" or u.hostname != ALLOWED_HOST or not u.path.startswith("/Kcampelo/lardakel1302_posts/"):
            raise PublishError("URL fora do repositório autorizado.")
        try:
            with urlopen(Request(media["url"], headers={"User-Agent": "LarDaKelPublisher/1.0"}), timeout=30) as r:
                if r.headers.get_content_type() != "image/jpeg":
                    raise PublishError("A mídia pública não é JPEG.")
                data = r.read(8 * 1024 * 1024 + 1)
        except (URLError, OSError):
            raise PublishError("Não foi possível baixar a mídia pública.") from None
        if len(data) > 8 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != media["sha256"]:
            raise PublishError("A mídia pública não corresponde à arte aprovada.")

def state_path(job):
    if not re.fullmatch(r"[a-z0-9-]+", job["id"]):
        raise PublishError("ID de tarefa inválido.")
    return STATE / (job["id"] + ".json")

def save_state(job, state):
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    atomic(state_path(job), state)

def prepare(api, job, state):
    if state.get("status") in ("PUBLISHING", "NEEDS_REVIEW", "PUBLISHED"):
        raise PublishError("Tarefa já publicada ou aguardando reconciliação.")
    fingerprint = hashlib.sha256(json.dumps({"images": job["images"], "caption": job["caption"]}, sort_keys=True).encode()).hexdigest()
    if state.get("fingerprint") != fingerprint or (state.get("created_at") and datetime.now(timezone.utc) - datetime.fromisoformat(state["created_at"]) >= timedelta(hours=20)):
        state.clear()
    state["fingerprint"] = fingerprint
    if state.get("parent"):
        # A prepared container expires after 24h. Renew only if never submitted.
        made = datetime.fromisoformat(state["created_at"])
        if datetime.now(timezone.utc) - made < timedelta(hours=20):
            api.ready(state["parent"])
            return state
        state.clear()
    verify_media(job)
    state.setdefault("children", [])
    state.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    state["status"] = "PREPARING"
    save_state(job, state)
    for media in job["images"][len(state["children"]):]:
        child = api.request(api.uid + "/media",
                            {"image_url": media["url"], "is_carousel_item": "true"}, "POST")
        state["children"].append(child["id"])
        save_state(job, state)
    for child in state["children"]:
        api.ready(child)
    parent = api.request(api.uid + "/media",
                         {"media_type": "CAROUSEL",
                          "children": ",".join(state["children"]),
                          "caption": job["caption"]}, "POST")
    state["parent"] = parent["id"]
    state["status"] = "PROCESSING"
    save_state(job, state)
    api.ready(state["parent"])
    state["status"] = "READY"
    save_state(job, state)
    return state

def eligibility(job, now, active_from):
    when = datetime.fromisoformat(job["scheduled_at"])
    if not job.get("enabled") or when < active_from:
        return "RESERVE"
    delay = (now - when).total_seconds()
    if delay < 0:
        return "FUTURE"
    if delay > MAX_DELAY:
        return "MISSED"
    return "DUE"

def reconcile(api, job, state):
    status = api.request(state["parent"], {"fields": "status_code"}).get("status_code")
    if status == "PUBLISHED":
        state["status"] = "PUBLISHED"
        state["reconciled_container_status"] = status
        # Exact ID may be unavailable after a network interruption.
    else:
        state["status"] = "NEEDS_REVIEW"
    save_state(job, state)
    return state["status"]

def publish_job(api, job, now, active_from):
    state = load(state_path(job), {})
    if state.get("status") == "PUBLISHED":
        return "ALREADY_PUBLISHED"
    if state.get("status") in ("PUBLISHING", "NEEDS_REVIEW"):
        return reconcile(api, job, state)
    eligible = eligibility(job, now, active_from)
    if eligible != "DUE":
        return eligible
    state = prepare(api, job, state)
    if eligibility(job, datetime.now(timezone.utc), active_from) != "DUE":
        return "MISSED"
    # Write intent before transmitting. Never repeat a media_publish blindly.
    state["status"] = "PUBLISHING"
    save_state(job, state)
    try:
        response = api.request(api.uid + "/media_publish", {"creation_id": state["parent"]}, "POST")
        state["media_id"] = response["id"]
        state["status"] = "PUBLISHED"
        state["published_at"] = datetime.now(timezone.utc).isoformat()
        save_state(job, state)
    except Exception:
        state["status"] = "NEEDS_REVIEW"
        save_state(job, state)
        raise PublishError("Resposta de publicação inconclusiva; não repetir. Conferir estado do contêiner.") from None
    try:
        state["permalink"] = api.request(state["media_id"], {"fields": "permalink"}).get("permalink")
        save_state(job, state)
    except PublishError:
        pass
    return "PUBLISHED"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["check", "validate-media", "prepare", "run", "status"])
    parser.add_argument("--job")
    args = parser.parse_args()
    queue = load(QUEUE)
    if not queue:
        raise PublishError("Fila não encontrada.")
    cfg = read_env()
    jobs = queue["jobs"]
    if args.job:
        jobs = [j for j in jobs if j["id"] == args.job]
        if not jobs:
            raise PublishError("Tarefa não encontrada.")
    if args.action == "status":
        print(json.dumps([{"job": j["id"], "scheduled_at": j["scheduled_at"],
                           "enabled": j["enabled"], "state": load(state_path(j), {})}
                          for j in jobs], ensure_ascii=False))
        return
    if args.action == "validate-media":
        for job in jobs:
            verify_media(job)
        print(json.dumps({"media_validated": sum(len(j["images"]) for j in jobs)}))
        return
    api = API(cfg)
    identity = api.check_identity()
    if args.action == "check":
        print(json.dumps({"connected": True, "username": identity["username"],
                          "account_type": identity.get("account_type"), "api_version": cfg["META_API_VERSION"]}))
        return
    with lock():
        if args.action == "prepare":
            if len(jobs) != 1:
                raise PublishError("Informe --job para teste sem publicação.")
            state = prepare(api, jobs[0], load(state_path(jobs[0]), {}))
            print(json.dumps({"job": jobs[0]["id"], "container": state["parent"],
                              "status": state["status"], "published": False}))
            return
        if cfg.get("INSTAGRAM_PUBLISH_ENABLED", "").lower() != "true" or not queue.get("enabled"):
            raise PublishError("Publicação desativada.")
        now = datetime.now(timezone.utc)
        active_from = datetime.fromisoformat(queue["activated_at"])
        results = []
        for job in jobs:
            status = publish_job(api, job, now, active_from)
            if status not in ("FUTURE", "RESERVE", "ALREADY_PUBLISHED"):
                results.append({"job": job["id"], "status": status,
                                "media_id": load(state_path(job), {}).get("media_id")})
        print(json.dumps({"results": results}, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except PublishError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)
    except Exception:
        print(json.dumps({"ok": False, "error": "Falha interna; detalhes omitidos para proteger credenciais."}))
        sys.exit(2)

