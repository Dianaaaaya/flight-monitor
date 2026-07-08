"""数据源之间统一的机票结构，让不同 API 返回的结果长得一样。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Leg:
    """单向行程（去程或回程）。"""

    date: str            # YYYY-MM-DD
    from_airport: str    # 出发机场码
    to_airport: str      # 到达机场码
    dep_time: str        # 出发时间，如 "08:15"
    arr_time: str        # 到达时间，如 "11:30"
    airlines: list[str] = field(default_factory=list)  # 航司代码
    stops: int = 0       # 转机次数

    @property
    def stops_label(self) -> str:
        return "直飞" if self.stops == 0 else f"转{self.stops}次"


@dataclass
class FlightOffer:
    """一个完整的往返报价。"""

    price: float
    currency: str
    outbound: Leg
    inbound: Leg | None       # 单程时为 None
    booking_link: str = ""
