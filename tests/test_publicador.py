import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("publisher", Path(__file__).parents[1] / "scripts/publicar_instagram.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.job = {"id": "test-job", "enabled": True,
                    "scheduled_at": (self.now - timedelta(seconds=5)).isoformat(),
                    "caption": "Teste", "images": [{"url": "x", "sha256": "y"}] * 5}
        self.tmp = tempfile.TemporaryDirectory()
        self.state_patch = patch.object(p, "STATE", Path(self.tmp.name))
        self.state_patch.start()
    def tearDown(self):
        self.state_patch.stop()
        self.tmp.cleanup()
    def test_future_disabled_and_expired_never_publish(self):
        self.assertEqual(p.eligibility(self.job, self.now - timedelta(minutes=1), self.now - timedelta(hours=1)), "FUTURE")
        self.job["enabled"] = False
        self.assertEqual(p.eligibility(self.job, self.now, self.now - timedelta(hours=1)), "RESERVE")
        self.job["enabled"] = True
        self.assertEqual(p.eligibility(self.job, self.now + timedelta(hours=1), self.now - timedelta(hours=1)), "MISSED")
    def test_activation_blocks_old_jobs(self):
        self.assertEqual(p.eligibility(self.job, self.now, self.now), "RESERVE")
    def test_published_job_is_not_sent_twice(self):
        p.save_state(self.job, {"status": "PUBLISHED", "media_id": "123"})
        api = FakeAPI()
        self.assertEqual(p.publish_job(api, self.job, self.now, self.now - timedelta(hours=1)), "ALREADY_PUBLISHED")
        self.assertEqual(api.posts, 0)
    def test_ambiguous_publish_is_reconciled_without_retry(self):
        api = FakeAPI(ambiguous=True)
        with patch.object(p, "prepare", return_value={"parent": "123", "status": "READY"}):
            with self.assertRaises(p.PublishError):
                p.publish_job(api, self.job, self.now, self.now - timedelta(hours=1))
        self.assertEqual(p.load(p.state_path(self.job))["status"], "NEEDS_REVIEW")
        self.assertEqual(p.publish_job(api, self.job, self.now, self.now - timedelta(hours=1)), "PUBLISHED")
        self.assertEqual(api.posts, 1)
    def test_changed_artwork_rebuilds_container(self):
        api = FakeAPI()
        old = {"parent": "obsolete", "fingerprint": "old", "created_at": self.now.isoformat(), "children": ["old"]*4}
        with patch.object(p, "verify_media"):
            fresh = p.prepare(api, self.job, old)
        self.assertNotEqual(fresh["parent"], "obsolete")
        self.assertEqual(len(fresh["children"]), 5)

class FakeAPI:
    uid = "123"
    def __init__(self, ambiguous=False):
        self.posts = 0
        self.count = 0
        self.ambiguous = ambiguous
    def ready(self, container):
        pass
    def request(self, endpoint, params=None, method="GET"):
        if endpoint.endswith("/media_publish"):
            self.posts += 1
            if self.ambiguous:
                raise p.PublishError("Network timeout")
            return {"id": "published-id"}
        if method == "POST":
            self.count += 1
            return {"id": "new-"+str(self.count)}
        return {"status_code": "PUBLISHED", "permalink": "https://instagram.com/p/test"}

if __name__ == "__main__":
    unittest.main()

