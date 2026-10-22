# 麦麦年度报告 · mcd-wrapped

> 把你的麦当劳订单历史，变成一份 Spotify Wrapped 风格的年度报告——可截图、可分享、可炫耀。

2026 麦当劳程序员创意开发大赛（WorkBuddy × 麦当劳 1024 程序员节）参赛作品。基于麦当劳中国官方 MCP 服务开发，纯 Python 标准库、零第三方依赖，输出一个自包含的 HTML 文件。

## 效果预览

浏览器打开 [`examples/demo-report.html`](examples/demo-report.html)（47 单模拟数据，手机宽度，可长截图分享）。

报告包含：

| 模块 | 内容 |
| --- | --- |
| 封面 | 统计周期、下单数、总花费 |
| 年度战绩 | 下单数 / 总花费 / 用券省下 / 总摄入热量 |
| 年度挚爱餐品 | Top 5 餐品及点单次数条形图 |
| 热量去哪儿了 | 全年千卡、等价米饭碗数、趣味事实 |
| 时间画像 | 最常时段、深夜单、周末占比、连续吃麦天数 |
| 麦麦省战绩 | 省钱金额、省钱率、等价巨无霸数 |
| 遇见麦麦 | 麦乐送 vs 到店自取占比、年度最常光顾门店 |
| 积分小金库 | 可用积分、即将过期积分 |
| 年度称号 | 麦门终身荣誉会员 / 深夜铲S官 / 麦麦省钱刺客 / 热量炸弹鉴赏家…… |

## 快速开始

```bash
# 1. 申请 MCP Token（免费）：https://open.mcd.cn/mcp
# 2. 克隆即跑，无需安装任何依赖
git clone https://github.com/<your-name>/mcd-wrapped.git
cd mcd-wrapped

# 没有 Token？先用内置模拟数据体验完整效果
python3 main.py --demo
# 打开生成的 mcd-wrapped-report.html

# 有 Token？生成你的真实年度报告
python3 main.py --token YOUR_MCP_TOKEN
# 或使用环境变量
MCD_MCP_TOKEN=YOUR_TOKEN python3 main.py
```

> 想把自己的报告发布成在线链接？把 `examples/` 或生成的 HTML 推到仓库后用 GitHub Pages 发布即可。

## 工作原理

```
麦当劳 MCP (mcp.mcd.cn)
   │  now-time-info / order-list / list-nutrition-foods
   │  / query-my-coupons / query-my-account
   ▼
归一化订单（时间/渠道/门店/餐品/金额/用券）
   ▼
统计引擎（餐品偏好、热量、时间画像、省钱、积分、年度称号）
   ▼
单文件 HTML 渲染（手机宽度 · 无外部依赖 · 可长截图分享）
```

## 项目结构

```
mcd-wrapped/
├── main.py                  # CLI 入口
├── mcd_report/
│   ├── mcp_client.py        # 麦当劳 MCP 最小客户端（Streamable HTTP）
│   ├── stats.py             # 统计引擎
│   ├── demo_data.py         # 确定性模拟数据（seed=1024）
│   └── render.py            # HTML 渲染器
├── examples/
│   └── demo-report.html     # 演示报告
├── MCP_INTEGRATION.md       # MCP 集成说明
├── workbuddy.md             # 使用 WorkBuddy 的开发记录
└── CONTEST_DECLARATION.md   # 参赛声明（官方模板，内容未改动）
```

## 真实数据字段适配

官方 `order-list` 等接口的响应字段以其文档为准，本项目内置了尽力而为的归一化逻辑（递归匹配常见字段名）。如你的账号数据字段不匹配，导出原始响应后按需微调 `main.py` 中的 `normalize_orders`：

```bash
python3 main.py --token YOUR_TOKEN --raw-dump raw.json
```

## 参赛信息

- 赛事：2026 麦当劳程序员创意开发大赛（1024 程序员节）
- 必交文件：README.md、CONTEST_DECLARATION.md、MCP_INTEGRATION.md、源代码、workbuddy.md
- 报名方式：在官方仓库发布报名 Issue
- 排名规则：GitHub 公开 Star 数（2026-10-26 00:00 定榜）

## 免责声明

本项目为参赛作品，由参赛者独立开发，非麦当劳官方产品。报告输出仅供娱乐参考，不构成医疗、营养或其他专业建议；餐品信息、价格及供应状态以麦当劳官方渠道的实时结果为准。

## License

MIT
