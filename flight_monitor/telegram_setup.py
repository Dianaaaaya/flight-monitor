"""帮你拿到 Telegram chat id。

用法：
  1. 在 Telegram 里找 @BotFather → /newbot → 拿到 bot token
  2. 把 token 填进 .env 的 TELEGRAM_BOT_TOKEN
  3. 在 Telegram 里给你新建的 bot 发任意一句话（例如 "hi"）
  4. 运行：  .venv/bin/python -m flight_monitor.telegram_setup
     它会打印出你的 chat id，填进 .env 的 TELEGRAM_CHAT_ID 即可
"""
from __future__ import annotations

import requests

from .config import SETTINGS


def main() -> None:
    token = SETTINGS.telegram_bot_token
    if not token:
        print("请先在 .env 里填 TELEGRAM_BOT_TOKEN")
        return

    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates", timeout=30
    )
    resp.raise_for_status()
    updates = resp.json().get("result", [])
    if not updates:
        print("没收到任何消息。请先在 Telegram 里给你的 bot 发一句话，再重跑本命令。")
        return

    seen = {}
    for u in updates:
        msg = u.get("message") or u.get("edited_message") or {}
        chat = msg.get("chat", {})
        if chat.get("id") is not None:
            name = chat.get("username") or chat.get("first_name") or ""
            seen[chat["id"]] = name

    print("找到以下 chat id（把你自己的那个填进 .env 的 TELEGRAM_CHAT_ID）：")
    for cid, name in seen.items():
        print(f"  chat_id = {cid}   ({name})")


if __name__ == "__main__":
    main()
