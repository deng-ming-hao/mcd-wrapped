# workbuddy.md — 使用 WorkBuddy 的开发记录

> 本文件记录本项目使用 WorkBuddy（赛事官方合作伙伴）完成开发的过程，用于核验 WorkBuddy 专项奖励条件。

## 开发时间线（2026-10-22）

**第 1 轮：活动解读与摸底。**
读取大赛规则，确认关键约束：报名截止 10-25 23:59、排名完全看 GitHub Star、仓库必须包含五个标准文件（README.md / CONTEST_DECLARATION.md / MCP_INTEGRATION.md / 源代码 / workbuddy.md）、报名走官方仓库 Issue 模板。

**第 2 轮：战况分析。**
分析 10-19 排行榜（104 个在榜项目）：前三名全部是优惠券省钱类（611 / 512 / 491 Star），第二梯队是营养配餐与卡路里估算类。结论：官方示例方向已成红海，需要换赛道。

**第 3 轮：能力盘点。**
读取麦当劳 MCP Server 官方仓库的完整工具列表，梳理出数据闭环：`order-list`（历史订单）+ `list-nutrition-foods`（158 个餐品营养数据）+ `query-my-coupons` + `query-my-account` + `now-time-info`，确定选题「麦麦年度报告」——Spotify Wrapped 式个人吃麦报告。

**第 4 轮：编码实现。**
在 WorkBuddy 中完成全部核心代码：MCP Streamable HTTP 最小客户端、统计引擎、模拟数据生成器、HTML 渲染器、CLI 入口。全程纯 Python 标准库、零第三方依赖。

**第 5 轮：演示与验证。**
运行 `python3 main.py --demo` 生成演示报告并验证：47 单模拟数据跑通全链路，年度称号正确计算为「麦门终身荣誉会员」，输出单文件 HTML（约 10KB，无外部依赖）。

## 关键开发决策

1. **选题逻辑**：官方示例是下限不是方向。Star 的唯一驱动力是"别人为什么转发你"——个人年度报告是这个比赛里传播性最强的形态，且榜单空白
2. **演示优先**：先做无 Token 也能看的静态演示页（本届已有项目验证过该打法），真实数据链路作为 CLI 模式并行提供
3. **零依赖**：只用标准库，保证"三行命令跑起来"，降低 Star 门槛
4. **可复现**：模拟数据固定 seed（1024），任何人 clone 后看到的演示报告一致
5. **演示数据诚实标注**：演示页带「演示数据」角标，避免误导

## 使用到的 WorkBuddy 能力

- 网页抓取与官方规则研读（GitHub 赛事仓库、MCP Server 仓库）
- 全栈编码与调试（Python 项目从零到可运行）
- 文件生成与项目管理（项目结构、参赛文档）

## 复现方式

```bash
git clone <本仓库>
cd mcd-wrapped
python3 main.py --demo        # 复现演示报告
python3 main.py --token <TOKEN>  # 生成真实报告
```
