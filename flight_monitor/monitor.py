"""主逻辑：对每条规则查价、判断触发、发邮件、存历史。"""
from __future__ import annotations

from .config import RULES, SETTINGS, Rule
from .models import FlightOffer
from .notifier import build_message, notify
from .providers import get_provider
from .storage import Storage


def evaluate_triggers(rule: Rule, offer: FlightOffer,
                      prev_price: float | None) -> list[str]:
    """返回被触发的原因列表（可能多个）。满足任意一个即需通知。"""
    reasons: list[str] = []

    # 条件①：低于目标价
    if rule.target_price is not None and offer.price <= rule.target_price:
        reasons.append(f"总价 {offer.price:.0f} ≤ 目标价 {rule.target_price:.0f}")

    # 条件②：相比上次检测降幅超过阈值
    if (rule.drop_threshold is not None and prev_price is not None
            and (prev_price - offer.price) > rule.drop_threshold):
        reasons.append(
            f"较上次降 {prev_price - offer.price:.0f} > {rule.drop_threshold:.0f}"
        )

    return reasons


def run_once() -> None:
    provider = get_provider(SETTINGS)
    storage = Storage()

    for rule in RULES:
        print(f"[检查] {rule.name} ({rule.id})")
        try:
            offer = provider.cheapest(rule)
        except Exception as e:  # noqa: BLE001 单条规则失败不影响其他
            print(f"  查询失败：{e}")
            continue

        if offer is None:
            print("  没查到符合条件的航班")
            continue

        prev_price = storage.last_price(rule.id)
        print(f"  当前最低：{offer.currency} {offer.price:.2f}"
              f"（上次 {prev_price}）")

        reasons = evaluate_triggers(rule, offer, prev_price)

        # 防轰炸：把「短语原因」归一到「target / drop」两类做冷却
        to_notify = []
        for r in reasons:
            key = "target" if "目标价" in r else "drop"
            if storage.can_notify(rule.id, key, SETTINGS.notify_cooldown_hours):
                to_notify.append((key, r))

        if to_notify:
            subject, body = build_message(
                rule, offer, [r for _, r in to_notify], prev_price
            )
            try:
                notify(SETTINGS, subject, body)
                for key, _ in to_notify:
                    storage.mark_notified(rule.id, key)
                print(f"  ✅ 已发通知：{subject}")
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠️ 通知发送失败：{e}")
        elif reasons:
            print(f"  命中触发但在冷却期内，跳过通知：{reasons}")
        else:
            print("  未触发通知条件")

        # 先算触发、后更新历史（保证 prev_price 是"上一次"的值）
        storage.record_price(rule.id, offer.price)

    storage.save()
    print("完成。")


if __name__ == "__main__":
    run_once()
