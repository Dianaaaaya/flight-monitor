"""SerpApi 的 Google Flights 数据源 —— 最准的实时价（就是 Google Flights 上的数据）。

免费额度 250 次搜索/月。文档：https://serpapi.com/google-flights-api

往返查询是两步：
  1. 首个请求返回各"去程"选项，每个带一个 departure_token；
  2. 带 departure_token 再发一次，返回对应的"回程"选项与往返总价。
full_roundtrip=True 时会发第 2 次请求，从而拿到完整回程明细（多花一次额度）；
False 时只发一次，仅追踪往返总价 + 去程明细。
"""
from __future__ import annotations

from urllib.parse import quote

import requests

from ..config import Rule
from ..models import FlightOffer, Leg
from .base import FlightProvider

URL = "https://serpapi.com/search.json"

# SerpApi stops 取值：1=直飞, 2=最多1转, 3=最多2转
_STOPS_PARAM = {0: 1, 1: 2, 2: 3}


class SerpApiProvider(FlightProvider):
    def __init__(self, api_key: str, full_roundtrip: bool = True):
        if not api_key:
            raise ValueError("缺少 SERPAPI_KEY")
        self.api_key = api_key
        self.full_roundtrip = full_roundtrip

    def cheapest(self, rule: Rule) -> FlightOffer | None:
        params = {
            "engine": "google_flights",
            "departure_id": ",".join(rule.fly_from),   # 支持多机场逗号分隔
            "arrival_id": ",".join(rule.fly_to),
            "outbound_date": rule.depart_date,
            "return_date": rule.return_date,
            "type": 1,                                  # 1=往返
            "stops": _STOPS_PARAM.get(rule.max_stopovers, 3),
            "adults": rule.adults,
            "currency": rule.currency,
            "hl": "en",
        }

        # 第 1 步：拿最便宜的去程
        data = self._call(params)
        out_options = self._flights(data)
        if not out_options:
            return None
        cheapest_out = min(out_options, key=lambda f: f["price"])

        outbound = self._leg(cheapest_out["flights"])
        price = float(cheapest_out["price"])
        inbound = None

        # 第 2 步（可选）：用 departure_token 拿该去程对应的最便宜回程 + 往返总价
        token = cheapest_out.get("departure_token")
        if self.full_roundtrip and token:
            ret_data = self._call({**params, "departure_token": token})
            ret_options = self._flights(ret_data)
            if ret_options:
                cheapest_ret = min(ret_options, key=lambda f: f["price"])
                inbound = self._leg(cheapest_ret["flights"])
                price = float(cheapest_ret["price"])   # 这是往返总价

        return FlightOffer(
            price=price,
            currency=rule.currency,
            outbound=outbound,
            inbound=inbound,
            booking_link=self._google_link(rule),
        )

    def _call(self, params: dict) -> dict:
        resp = requests.get(URL, params={**params, "api_key": self.api_key}, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(f"SerpApi 返回错误：{data['error']}")
        return data

    @staticmethod
    def _flights(data: dict) -> list[dict]:
        flights = (data.get("best_flights") or []) + (data.get("other_flights") or [])
        return [f for f in flights if f.get("price") is not None]

    @staticmethod
    def _leg(segs: list[dict]) -> Leg:
        first, last = segs[0], segs[-1]
        return Leg(
            date=first["departure_airport"]["time"][:10],
            from_airport=first["departure_airport"]["id"],
            to_airport=last["arrival_airport"]["id"],
            dep_time=first["departure_airport"]["time"][11:16],
            arr_time=last["arrival_airport"]["time"][11:16],
            airlines=sorted({s["airline"] for s in segs if s.get("airline")}),
            stops=len(segs) - 1,
        )

    @staticmethod
    def _google_link(rule: Rule) -> str:
        q = (
            f"Flights from {'/'.join(rule.fly_from)} to {'/'.join(rule.fly_to)} "
            f"on {rule.depart_date} returning {rule.return_date}"
        )
        return f"https://www.google.com/travel/flights?q={quote(q)}"
