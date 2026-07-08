"""Kiwi Tequila API 数据源。

文档：https://tequila.kiwi.com/portal/docs/tequila_api/search_api
注意 Tequila 的日期格式是 dd/mm/yyyy，不是 ISO。
"""
from __future__ import annotations

from datetime import datetime

import requests

from ..config import Rule
from ..models import FlightOffer, Leg
from .base import FlightProvider

SEARCH_URL = "https://api.tequila.kiwi.com/v2/search"


def _to_kiwi_date(iso: str) -> str:
    """YYYY-MM-DD → dd/mm/yyyy。"""
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")


class KiwiProvider(FlightProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("缺少 KIWI_API_KEY")
        self.api_key = api_key

    def cheapest(self, rule: Rule) -> FlightOffer | None:
        params = {
            "fly_from": ",".join(rule.fly_from),
            "fly_to": ",".join(rule.fly_to),
            "date_from": _to_kiwi_date(rule.depart_date),
            "date_to": _to_kiwi_date(rule.depart_date),
            "return_from": _to_kiwi_date(rule.return_date),
            "return_to": _to_kiwi_date(rule.return_date),
            "flight_type": "round",
            "adults": rule.adults,
            "max_stopovers": rule.max_stopovers,
            "curr": rule.currency,
            "sort": "price",
            "limit": 5,
        }
        resp = requests.get(
            SEARCH_URL,
            params=params,
            headers={"apikey": self.api_key},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return None
        return self._parse(data[0], rule.currency)

    @staticmethod
    def _parse(item: dict, currency: str) -> FlightOffer:
        # Kiwi 的 route 是逐段航段，return=0 是去程，return=1 是回程
        outbound_segs = [s for s in item["route"] if s.get("return") == 0]
        inbound_segs = [s for s in item["route"] if s.get("return") == 1]

        offer = FlightOffer(
            price=float(item["price"]),
            currency=currency,
            outbound=KiwiProvider._leg(outbound_segs),
            inbound=KiwiProvider._leg(inbound_segs) if inbound_segs else None,
            booking_link=item.get("deep_link", ""),
        )
        return offer

    @staticmethod
    def _leg(segs: list[dict]) -> Leg:
        first, last = segs[0], segs[-1]
        return Leg(
            date=first["local_departure"][:10],
            from_airport=first["flyFrom"],
            to_airport=last["flyTo"],
            dep_time=first["local_departure"][11:16],
            arr_time=last["local_arrival"][11:16],
            airlines=sorted({s["airline"] for s in segs}),
            stops=len(segs) - 1,
        )
