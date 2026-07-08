"""通知模块：把提醒发到 Telegram（默认）或邮件。

通知内容都含去/回程日期、机场、航司、价格、订票链接。
渠道由 Settings.notify_channel 决定：telegram | email。
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from .config import Rule, Settings
from .models import FlightOffer, Leg


def _leg_line(label: str, leg: Leg) -> str:
    airlines = "/".join(leg.airlines) if leg.airlines else "?"
    seg = f"{leg.from_airport} {leg.dep_time} → {leg.to_airport}"
    if leg.arr_time:                      # 有些数据源不给到达时刻
        seg += f" {leg.arr_time}"
    return f"── {label} ──\n{leg.date}  {seg}  {airlines}  {leg.stops_label}"


def build_message(rule: Rule, offer: FlightOffer, reasons: list[str],
                  prev_price: float | None) -> tuple[str, str]:
    """返回 (主题, 正文)。"""
    cur = offer.currency
    drop_note = ""
    if prev_price is not None and offer.price < prev_price:
        drop_note = f"（较上次 {prev_price:.0f} 降了 {prev_price - offer.price:.0f}）"

    subject = f"✈️ {rule.name} 降价提醒 —— {cur} {offer.price:.0f}{drop_note}"

    lines = [
        f"往返总价：{cur} {offer.price:.2f}  {drop_note}".rstrip(),
        "",
        _leg_line("去程", offer.outbound),
    ]
    if offer.inbound:
        lines.append(_leg_line("回程", offer.inbound))
    else:
        # 单次请求的数据源（如 SerpApi）拿不到回程明细，至少给出回程日期
        lines.append(f"── 回程 ──\n{rule.return_date}  明细见下方链接")
    lines += [
        "",
        f"触发原因：{'；'.join(reasons)}",
    ]
    if offer.booking_link:
        lines.append(f"订票链接：{offer.booking_link}")
    return subject, "\n".join(lines)


def notify(settings: Settings, subject: str, body: str) -> None:
    """按配置的渠道发送通知。"""
    if settings.notify_channel == "telegram":
        send_telegram(settings, subject, body)
    elif settings.notify_channel == "email":
        send_email(settings, subject, body)
    else:
        raise ValueError(f"未知的通知渠道：{settings.notify_channel}")


def send_telegram(settings: Settings, subject: str, body: str) -> None:
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        raise ValueError(
            "Telegram 配置不完整，请在 .env 里填 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID"
        )
    text = f"{subject}\n\n{body}"
    resp = requests.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    resp.raise_for_status()


def send_email(settings: Settings, subject: str, body: str) -> None:
    if not (settings.smtp_user and settings.smtp_password and settings.notify_email):
        raise ValueError("邮件配置不完整，请在 .env 里填 SMTP_USER / SMTP_PASSWORD / NOTIFY_EMAIL")

    msg = MIMEMultipart()
    msg["From"] = settings.smtp_user
    msg["To"] = settings.notify_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
