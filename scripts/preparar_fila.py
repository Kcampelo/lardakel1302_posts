"""Rebuild the queue from the source calendar, without locale-dependent date parsing."""
import hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=subprocess.check_output(["git","-c","safe.directory=C:/REPO/lardakel1302_posts","-C",str(root),"rev-parse","HEAD"],text=True).strip()
calendar=json.loads((root/"agendamento/calendario-2026-10-01-a-04.json").read_text(encoding="utf-8-sig"))
now=datetime.now(timezone.utc)
jobs=[]
for item in calendar["items"]:
    when=datetime.fromisoformat(item["date"]+"T"+item["time"]+":00-03:00")
    images=[]
    for i in range(1,6):
        rel=item["folder"]+"/carrossel/"+str(i).zfill(2)+".jpg"
        images.append({"url":"https://raw.githubusercontent.com/Kcampelo/lardakel1302_posts/"+sha+"/"+rel,"sha256":hashlib.sha256((root/rel).read_bytes()).hexdigest()})
    jobs.append({"id":item["date"]+"-"+item["time"].replace(":","")+"-"+item["category"],"scheduled_at":when.isoformat(),"enabled":when>now,"theme":item["theme"],"format":"CAROUSEL","caption":(root/item["folder"]/"legenda.txt").read_text(encoding="utf-8"),"images":images})
queue={"enabled":False,"activated_at":now.isoformat(),"timezone":"America/Sao_Paulo","media_commit":sha,"jobs":jobs}
(root/"agendamento/fila.json").write_text(json.dumps(queue,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps([{"id":j["id"],"scheduled_at":j["scheduled_at"],"enabled":j["enabled"]} for j in jobs]))

