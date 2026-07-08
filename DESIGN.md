# 设计文档 — 机票价格监测软件

## 需求

定时（每小时）检测一条固定航线的往返机票，满足条件时邮件通知。

- 航线：纽约（JFK/LGA/EWR）⇄ 西雅图（SEA），往返
- 日期：去 2026-08-17、回 2026-08-22
- 中转：最多 1 次
- 通知条件（满足任意一个）：① 往返总价 ≤ $360；② 相比上次检测降幅 > $30
- 通知方式：邮件，内容需含去/回程日期、机场、航司、价格、订票链接

## 关键决策与取舍

### 1. 数据源：SerpApi（Google Flights 真实时价）
用户要求"准 + 实时"。Google Flights / Skyscanner 没有面向个人的官方 API。候选：

| 方案 | 数据 | 免费额度 | 结论 |
|------|------|---------|------|
| **SerpApi（Google Flights）** | Google 真实时价 ✅ | 250 次/月 | ✅ 选用；靠降频匹配额度 |
| Kiwi Tequila | 免费、量大 | — | ❌ 现仅对 affiliate 开放，个人注册不了 |
| Travelpayouts | 缓存价、有延迟 | 免费 | 备用（保留 provider） |
| Amadeus | 实时正规 | 少量免费后收费 | 高频会超额 |

> 演进过程：Kiwi Tequila 实测已限 affiliate（登录报错、页面提示 become our
> affiliate）；Travelpayouts 是缓存价，用户要"准的实时"，故最终选 SerpApi
> （直接抓 Google Flights）。因为 provider 是抽象层，这几次切换都只是换个子类
> + 改 `PROVIDER`，主逻辑零改动。三个 provider（serpapi/travelpayouts/kiwi）均保留。
>
> SerpApi 说明：免费 250 次/月。往返查询是两步——首个请求拿去程（带
> departure_token），带 token 再发一次拿回程与往返总价。`SERPAPI_FULL_ROUNDTRIP=1`
> （默认）时发这 2 次请求，邮件里去程 + 回程都有完整明细；设为 0 则只发一次，
> 仅追踪往返总价 + 去程明细，回程给出日期 + Google Flights 链接。

### 1b. 检测时间表：贴着航司调价时点（而非平均撒）
航司通过 ATPCO 改价，工作日 **10:00 / 12:30 / 20:00 ET**、周末 **17:00 ET**，
其余时间价格基本静止（"周二/半夜最便宜"是过时传说）。因此把每天 14 次检测
集中在这几个调价窗口"前 + 后"各一次（前做基线、后抓新价，正好支撑"比上次降价"
的判断），并补几个夜间/清晨点抓库存重定价。一天 14 次、每次 2 个请求（完整往返），
一周 14×2×7 = 196 次，落在 SerpApi 免费额度（250/月）内。cron 见
`.github/workflows/monitor.yml`（写的是 UTC，= EDT + 4）。

用户场景是只监测一周（trip 8/17–8/22），一次性 196 次搜索即可覆盖，全程免费。

### 2. 运行形态：GitHub Actions 定时任务
免费、自带 cron、无需服务器。`cron: "5 * * * *"` 每小时触发。
代价：高峰期可能延迟几分钟或偶尔跳过——对机票监测无影响。

### 3. 状态存储：JSON 文件
`data/prices.json` 记录历史价格点、历史最低、上次价格、上次通知时间。
GitHub Actions 每次跑完把它 commit 回仓库，实现跨运行的状态持久化，
顺便积累数据以后可画价格曲线。

## 架构

```
GitHub Actions (每小时)
      │
      ▼
  run.py → monitor.run_once()
      │  ┌────────────────────────────────────────┐
      │  │ 对每条 Rule：                            │
      │  │ 1. provider.cheapest(rule) 查最低价      │
      │  │ 2. evaluate_triggers(prev_price 对比)   │
      │  │ 3. 冷却检查（同原因24h最多1次）           │
      │  │ 4. 满足 → notifier 发邮件                │
      │  │ 5. storage 记录价格、更新历史             │
      │  └────────────────────────────────────────┘
      ▼
  邮件 (Gmail SMTP)
```

## 模块职责

| 模块 | 职责 |
|------|------|
| `config.py` | `Rule` 数据类 + 你的监测规则 + 全局 `Settings`（读环境变量） |
| `models.py` | `FlightOffer` / `Leg`——各数据源统一的输出结构 |
| `providers/` | `FlightProvider` 抽象 + `travelpayouts`、`kiwi`、`mock` 实现，`get_provider` 工厂 |
| `storage.py` | 价格历史读写、历史最低、通知冷却判断 |
| `notifier.py` | 组装邮件正文 + Gmail SMTP 发送 |
| `monitor.py` | 编排：查价 → 触发判断 → 冷却 → 通知 → 存历史 |

## 触发逻辑（重点）

先用「上一次的价格」判断触发，**再**把当前价格写入历史，保证 `prev_price`
永远是上一轮的值：

```
prev_price = storage.last_price(rule.id)
reasons = evaluate_triggers(rule, offer, prev_price)
... 通知 ...
storage.record_price(rule.id, offer.price)   # 最后才更新
```

## 防轰炸

触发原因归为 `target` / `drop` 两类，每类 24 小时内最多通知一次
（`Settings.notify_cooldown_hours`），避免价格长期低于阈值时反复发邮件。

## 可扩展方向
- 加航线：往 `config.RULES` 加 `Rule`。
- 换/加数据源：在 `providers/` 加子类，改 `PROVIDER` 环境变量。
- 价格曲线：`data/prices.json` 已积累历史，后续可加网页/图表。
- 多渠道通知：`notifier` 里加 Telegram / 手机推送。
