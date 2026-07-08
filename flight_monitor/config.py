"""监测规则 & 全局配置。

这里定义"要监测什么"和"什么条件下通知"。以后想加航线，
往 RULES 里再加一条即可。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Rule:
    """一条机票监测规则。"""

    name: str                       # 人类可读名字，出现在邮件标题里
    fly_from: list[str]             # 出发机场（可多个，比价取最便宜）
    fly_to: list[str]               # 到达机场
    depart_date: str                # 去程日期，ISO 格式 YYYY-MM-DD
    return_date: str                # 回程日期，ISO 格式 YYYY-MM-DD
    max_stopovers: int = 1          # 最多转机次数
    adults: int = 1                 # 成人数
    currency: str = "USD"

    # ── 触发条件（满足任意一个就通知） ──
    target_price: float | None = None   # 总价 ≤ 此值 → 通知
    drop_threshold: float | None = None  # 相比上次检测降幅 > 此值 → 通知

    @property
    def id(self) -> str:
        """规则唯一标识，用作历史存储的 key。"""
        return (
            f"{'-'.join(self.fly_from)}_{'-'.join(self.fly_to)}"
            f"_{self.depart_date}_{self.return_date}"
        )


# ────────────────────────────────────────────────
# 你的监测规则（我们聊定的那条）
# ────────────────────────────────────────────────
RULES: list[Rule] = [
    Rule(
        name="NY⇄SEA 往返",
        fly_from=["JFK", "LGA", "EWR"],
        fly_to=["SEA"],
        depart_date="2026-08-17",
        return_date="2026-08-22",
        max_stopovers=1,
        adults=1,
        currency="USD",
        target_price=360.0,     # 条件①：往返总价 ≤ $360
        drop_threshold=30.0,    # 条件②：比上次降 > $30
    ),
]


@dataclass
class Settings:
    provider: str = field(default_factory=lambda: os.getenv("PROVIDER", "mock"))
    kiwi_api_key: str = field(default_factory=lambda: os.getenv("KIWI_API_KEY", ""))
    travelpayouts_token: str = field(
        default_factory=lambda: os.getenv("TRAVELPAYOUTS_TOKEN", "")
    )
    serpapi_key: str = field(default_factory=lambda: os.getenv("SERPAPI_KEY", ""))
    # True 时每次查发 2 个请求以拿完整回程明细（默认开，免费额度够用）
    serpapi_full_roundtrip: bool = field(
        default_factory=lambda: os.getenv("SERPAPI_FULL_ROUNDTRIP", "1") == "1"
    )

    # 通知渠道：telegram（默认）| email
    notify_channel: str = field(
        default_factory=lambda: os.getenv("NOTIFY_CHANNEL", "telegram")
    )
    telegram_bot_token: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_chat_id: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", "")
    )

    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    notify_email: str = field(default_factory=lambda: os.getenv("NOTIFY_EMAIL", ""))

    # 同一触发原因在这么多小时内最多通知一次（防轰炸）
    notify_cooldown_hours: int = 24


SETTINGS = Settings()
