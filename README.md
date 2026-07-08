# 机票价格监测

定时检测 **纽约 ⇄ 西雅图** 往返机票，价格达标或降价时用 **Telegram** 通知你。

## 当前监测规则

| 项目 | 设置 |
|------|------|
| 航线 | NY（JFK + LGA + EWR）⇄ SEA 往返 |
| 日期 | 去 2026-08-17 / 回 2026-08-22 |
| 中转 | 最多 1 次 |
| 频率 | 每天 14 次，贴着航司调价时点分布（见下） |
| 通知条件（任一） | ① 总价 ≤ $360；② 比上次检测降 > $30 |
| 数据源 | SerpApi（Google Flights 真实时价，本地测试可用 mock） |
| 通知 | Telegram（邮件为备选渠道） |

## 为什么这样定检测时间

航司通过 ATPCO 改价：工作日 10:00 / 12:30 / 20:00 ET，周末 17:00 ET，
其余时间价格基本静止。所以检测集中在这几个时点"前+后"各一次
（前做基线、后抓新价，正好支撑"比上次降价"判断）。每天 14 次，每次查发 2 个
请求以拿完整往返明细，一周 14×2×7 = 196 次，在 SerpApi 免费额度（250/月）内。
具体时间表见 `.github/workflows/monitor.yml`。

规则定义在 `flight_monitor/config.py` 的 `RULES` 里，想加航线直接往里加。

## 本地跑（不需要任何 key）

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PROVIDER=mock .venv/bin/python run.py     # 用假数据跑通流程
```

## 正式使用

1. **拿数据源 key**：注册 [SerpApi](https://serpapi.com) →
   [API key 页面](https://serpapi.com/manage-api-key) 复制 `SERPAPI_KEY`（免费 250 次/月）。
2. **配 Telegram**：
   - Telegram 里找 `@BotFather` → `/newbot` → 拿到 `TELEGRAM_BOT_TOKEN`
   - 把 token 填进 `.env`，给你的 bot 发一句话，然后运行
     `.venv/bin/python -m flight_monitor.telegram_setup` 拿到 `TELEGRAM_CHAT_ID`
3. 复制 `.env.example` 为 `.env` 填好，本地测试：
   ```bash
   PROVIDER=serpapi .venv/bin/python run.py
   ```
4. **上云（GitHub Actions，按调价时点自动跑）**：
   - 把代码 push 到一个 GitHub 仓库
   - 仓库 Settings → Secrets and variables → Actions，添加：
     `SERPAPI_KEY`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`
   - `.github/workflows/monitor.yml` 会按时间表自动运行，并把价格历史提交回仓库

## 结构

```
run.py                     入口
flight_monitor/
  config.py                监测规则 + 全局配置
  models.py                统一的机票数据结构
  monitor.py               主逻辑：查价→判断→通知→存历史
  storage.py               价格历史（data/prices.json）
  notifier.py              通知（Telegram / 邮件）
  telegram_setup.py        辅助：拿 Telegram chat id
  providers/               数据源（serpapi / travelpayouts / kiwi / mock）
.github/workflows/monitor.yml   按调价时点的定时任务
```

细节设计见 [DESIGN.md](./DESIGN.md)。
