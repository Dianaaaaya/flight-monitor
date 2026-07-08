"""根据配置返回对应的数据源实例。"""
from __future__ import annotations

from ..config import Settings
from .base import FlightProvider


def get_provider(settings: Settings) -> FlightProvider:
    if settings.provider == "serpapi":
        from .serpapi import SerpApiProvider
        return SerpApiProvider(settings.serpapi_key, settings.serpapi_full_roundtrip)
    if settings.provider == "travelpayouts":
        from .travelpayouts import TravelpayoutsProvider
        return TravelpayoutsProvider(settings.travelpayouts_token)
    if settings.provider == "kiwi":
        from .kiwi import KiwiProvider
        return KiwiProvider(settings.kiwi_api_key)
    if settings.provider == "mock":
        from .mock import MockProvider
        return MockProvider()
    raise ValueError(f"未知的 PROVIDER: {settings.provider}")
