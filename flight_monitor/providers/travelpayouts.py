"""Travelpayouts (Aviasales) 数据源。

注册 https://www.travelpayouts.com → Developers → 拿 API token（即时，无需审批）。
用 prices_for_dates 接口查指定日期往返价。数据为缓存价，可能有几小时延迟。
文档：https://support.travelpayouts.com/hc/en-us/articles/203956163
"""
from __future__ import annotations

import requests

from ..config import Rule
from ..models import FlightOffer, Leg
from .base import FlightProvider

URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


class TravelpayoutsProvider(FlightProvider):
    def __init__(self, token: str):
        if not token:
            raise ValueError("缺少 TRAVELPAYOUTS_TOKEN")
        self.token = token

    def cheapest(self, rule: Rule) -> FlightOffer | None:
        # prices_for_dates 的 origin 只接受单个代码，多机场就逐个查再取最便宜
        best: FlightOffer | None = None
        for origin in rule.fly_from:
            for dest in rule.fly_to:
                for item in self._query(origin, dest, rule):
                    # 客户端过滤转机数（接口没有 max_stopovers 参数）
                    if (item.get("transfers", 0) > rule.max_stopovers
                            or item.get("return_transfers", 0) > rule.max_stopovers):
                        continue
                    offer = self._parse(item, rule.currency)
                    if best is None or offer.price < best.price:
                        best = offer
        return best

    def _query(self, origin: str, dest: str, rule: Rule) -> list[dict]:
        params = {
            "origin": origin,
            "destination": dest,
            "departure_at": rule.depart_date,
            "return_at": rule.return_date,
            "currency": rule.currency.lower(),
            "sorting": "price",
            "one_way": "false",
            "direct": "false",
            "limit": 30,
            "token": self.token,
        }
        resp = requests.get(URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("success", True):
            raise RuntimeError(f"Travelpayouts 返回错误：{payload}")
        return payload.get("data", [])

    @staticmethod
    def _parse(item: dict, currency: str) -> FlightOffer:
        airline = item.get("airline", "")
        outbound = Leg(
            date=item["departure_at"][:10],
            from_airport=item.get("origin_airport", item["origin"]),
            to_airport=item.get("destination_airport", item["destination"]),
            dep_time=item["departure_at"][11:16],
            arr_time="",  # 该接口不提供每段到达时刻
            airlines=[airline] if airline else [],
            stops=item.get("transfers", 0),
        )
        inbound = None
        if item.get("return_at"):
            inbound = Leg(
                date=item["return_at"][:10],
                from_airport=item.get("destination_airport", item["destination"]),
                to_airport=item.get("origin_airport", item["origin"]),
                dep_time=item["return_at"][11:16],
                arr_time="",
                airlines=[airline] if airline else [],
                stops=item.get("return_transfers", 0),
            )
        link = item.get("link", "")
        return FlightOffer(
            price=float(item["price"]),
            currency=currency,
            outbound=outbound,
            inbound=inbound,
            booking_link=f"https://www.aviasales.com{link}" if link else "",
        )
