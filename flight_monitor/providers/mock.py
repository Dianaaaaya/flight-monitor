"""假数据源，用来在没有 API key 的情况下本地跑通整条流程。

每次调用返回一个在 $320~$420 之间随机波动的价格，方便测试
"降价 > $30" 和 "低于目标价 $360" 两种触发是否正常工作。
"""
from __future__ import annotations

import random

from ..config import Rule
from ..models import FlightOffer, Leg
from .base import FlightProvider


class MockProvider(FlightProvider):
    def cheapest(self, rule: Rule) -> FlightOffer | None:
        price = round(random.uniform(320, 420), 2)
        return FlightOffer(
            price=price,
            currency=rule.currency,
            outbound=Leg(
                date=rule.depart_date,
                from_airport="EWR",
                to_airport="SEA",
                dep_time="08:15",
                arr_time="11:30",
                airlines=["UA"],
                stops=0,
            ),
            inbound=Leg(
                date=rule.return_date,
                from_airport="SEA",
                to_airport="JFK",
                dep_time="14:00",
                arr_time="22:10",
                airlines=["DL"],
                stops=1,
            ),
            booking_link="https://example.com/booking",
        )
