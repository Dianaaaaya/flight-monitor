#!/usr/bin/env python3
"""入口：执行一次检测。GitHub Actions 和本地都跑这个。"""
from flight_monitor.monitor import run_once

if __name__ == "__main__":
    run_once()
