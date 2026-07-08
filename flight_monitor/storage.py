"""价格历史的持久化（一个 JSON 文件）。

存每条规则的：历史价格点、历史最低价、上次价格、上次各触发原因的通知时间。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "prices.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Storage:
    def __init__(self, path: Path = DATA_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"rules": {}}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))

    def state(self, rule_id: str) -> dict:
        return self._data["rules"].setdefault(
            rule_id,
            {"history": [], "min_price": None, "last_price": None, "last_notified": {}},
        )

    def record_price(self, rule_id: str, price: float) -> None:
        st = self.state(rule_id)
        st["history"].append({"ts": _now(), "price": price})
        st["history"] = st["history"][-500:]  # 只保留最近 500 个点
        st["last_price"] = price
        if st["min_price"] is None or price < st["min_price"]:
            st["min_price"] = price

    def last_price(self, rule_id: str) -> float | None:
        return self.state(rule_id)["last_price"]

    def can_notify(self, rule_id: str, reason: str, cooldown_hours: int) -> bool:
        """距上次同原因通知是否已超过冷却时间。"""
        last = self.state(rule_id)["last_notified"].get(reason)
        if last is None:
            return True
        elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(last)
        return elapsed.total_seconds() >= cooldown_hours * 3600

    def mark_notified(self, rule_id: str, reason: str) -> None:
        self.state(rule_id)["last_notified"][reason] = _now()
