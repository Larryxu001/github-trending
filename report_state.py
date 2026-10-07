"""Persistent report state and Beijing time, shared by scheduled jobs."""
import datetime
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
BJ = datetime.timezone(datetime.timedelta(hours=8))


def now():
    return datetime.datetime.now(BJ)


def load(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)
