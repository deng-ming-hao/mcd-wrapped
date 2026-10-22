# MCP 集成说明

## 使用的 MCP Server

| 项目 | 说明 |
| --- | --- |
| 名称 | 麦当劳中国 MCP Server（mcd-mcp） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 鉴权方式 | 请求头 `Authorization: Bearer <MCP_TOKEN>` |
| Token 申请 | https://open.mcd.cn/mcp （手机号验证登录后免费激活） |
| 限流 | 每 Token 600 次/分钟 |

## 使用的 Tool 清单

| Tool | 用途 | 在本项目中的角色 |
| --- | --- | --- |
| `now-time-info` | 获取当前时间信息 | 确定报告统计周期的截止日期 |
| `order-list` | 查询历史订单（到店/外送） | **核心数据源**：下单次数、金额、餐品明细、下单时间、就餐方式、门店 |
| `list-nutrition-foods` | 餐品营养信息列表 | 热量计算：构建「餐品 → 千卡」索引，回填每笔订单热量 |
| `query-my-coupons` | 我的优惠券查询 | 统计全年用券情况 |
| `query-my-account` | 我的积分查询 | 可用积分、即将过期积分展示 |

## 调用流程

1. `initialize` → `notifications/initialized`，建立 MCP 会话
2. `now-time-info` → 解析当前日期，作为统计周期截止日
3. `order-list` → 原始响应经 `normalize_orders()` 归一化为统一订单结构：
   `{ts, channel(delivery/takeout), store, items[{name, qty, price, kcal}], total, saved}`
4. `list-nutrition-foods` → 构建餐品千卡索引，按餐品名回填订单热量
5. `query-my-coupons` / `query-my-account` → 优惠券张数、积分资产
6. `compute_report()` 统计 → `render_html()` 渲染单文件报告

## 业务价值

- **数据叙事化**：把碎片化的订单历史变成个人年度叙事，天然适合社交分享，是 UGC 传播的抓手
- **营养可视化**：`list-nutrition-foods` 提供的 158 个餐品营养数据从"查不到"变成"看得懂"——全年热量等价换算（多少碗米饭、跑多少小时）
- **资产提醒**：优惠券与即将过期积分的展示，直接降低用户的资产浪费

## 客户端实现说明

`mcd_report/mcp_client.py` 为纯标准库实现的最小 MCP 客户端（约 120 行），要点：

- JSON-RPC 2.0 over Streamable HTTP，兼容 `application/json` 与 `text/event-stream` 两种响应体
- 自动跟踪服务端返回的 `mcp-session-id`
- 401 / 429 错误码转换为可读提示

## 字段适配

官方接口响应字段以其文档为准。本项目对订单、餐品、积分响应做了递归式的常见字段匹配；如实际字段名不匹配，可用 `--raw-dump` 导出原始 JSON 后，参照 `main.py` 中 `normalize_orders()` 的字段清单微调：

```bash
python3 main.py --token YOUR_TOKEN --raw-dump raw.json
```
