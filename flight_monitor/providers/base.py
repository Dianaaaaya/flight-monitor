"""数据源抽象：任何 provider 只要能对一条规则返回"最便宜的往返报价"即可。

这样以后从 Kiwi 换到 Travelpayouts 或别的 API，只需新增一个子类，
monitor 主逻辑完全不用改。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Rule
from ..models import FlightOffer


class FlightProvider(ABC):
    @abstractmethod
    def cheapest(self, rule: Rule) -> FlightOffer | None:
        """返回符合规则的最便宜往返报价；查不到返回 None。"""
        raise NotImplementedError
