"""渲染器：生成 Spotify Wrapped 风格的单文件 HTML 年度报告。

输出为自包含 HTML（无外部依赖），手机宽度居中，方便长截图分享。
"""

from __future__ import annotations

import html
from typing import Any, Dict, List


def _e(v: Any) -> str:
    return html.escape(str(v))


def _bar_rows(top_items: List[Dict[str, Any]], max_qty: int) -> str:
    rows = []
    medals = ["1", "2", "3", "4", "5"]
    colors = ["#FFC72C", "#FFD968", "#FFE698", "#FFF3C4", "#FFF3C4"]
    for i, item in enumerate(top_items):
        pct = max(6, round(item["qty"] / max(max_qty, 1) * 100))
        rows.append(f"""
        <div class="bar-row">
          <span class="bar-rank" style="background:{colors[min(i, 4)]}">{medals[min(i, 4)]}</span>
          <div class="bar-body">
            <div class="bar-label"><span>{_e(item['name'])}</span><span class="bar-qty">{item['qty']} 次</span></div>
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
          </div>
        </div>""")
    return "".join(rows)


def _facts_html(facts: List[str]) -> str:
    lis = "".join(f"<li>{_e(f)}</li>" for f in facts)
    return f'<ul class="facts">{lis}</ul>'


def render_html(report: Dict[str, Any]) -> str:
    if report.get("empty"):
        return _render_empty(report)

    r = report
    demo_badge = '<span class="demo-badge">演示数据</span>' if r.get("demo") else ""
    delivery_pct = round(r["delivery"] / max(r["order_count"], 1) * 100)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>我的 {r['period_start'][:4]} 麦麦年度报告</title>
<meta property="og:title" content="我的麦麦年度报告 · {_e(r['title'])}">
<meta property="og:description" content="全年 {r['order_count']} 单 · {r['total_spend_fmt']} · 年度称号：{_e(r['title'])}">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #FFF8E7; color: #2B2A26;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    line-height: 1.6; -webkit-font-smoothing: antialiased;
  }}
  .page {{ max-width: 480px; margin: 0 auto; padding: 20px 16px 48px; }}
  .card {{
    background: #FFFFFF; border-radius: 20px; padding: 22px 20px;
    margin-bottom: 14px; box-shadow: 0 1px 0 rgba(43,42,38,.04);
  }}
  .kicker {{ font-size: 12px; letter-spacing: 2px; color: #B08D00; font-weight: 600; }}
  h1 {{ font-size: 30px; line-height: 1.25; font-weight: 800; margin: 6px 0 10px; }}
  h2 {{ font-size: 16px; font-weight: 700; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }}
  h2::before {{ content: ""; width: 4px; height: 16px; background: #FFC72C; border-radius: 2px; }}
  .sub {{ font-size: 13px; color: #8A8577; }}
  .big {{ font-size: 34px; font-weight: 800; letter-spacing: -.5px; }}
  .big small {{ font-size: 14px; font-weight: 600; color: #8A8577; margin-left: 2px; }}
  .grid4 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .metric {{ background: #FFF9E6; border-radius: 14px; padding: 14px; }}
  .metric .label {{ font-size: 12px; color: #8A8577; }}
  .metric .value {{ font-size: 24px; font-weight: 800; margin-top: 2px; }}
  .metric .value small {{ font-size: 12px; font-weight: 600; color: #8A8577; }}
  .bar-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
  .bar-row:last-child {{ margin-bottom: 0; }}
  .bar-rank {{ width: 22px; height: 22px; border-radius: 7px; flex: none;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: #2B2A26; }}
  .bar-body {{ flex: 1; }}
  .bar-label {{ display: flex; justify-content: space-between; font-size: 13px; font-weight: 500; margin-bottom: 4px; }}
  .bar-qty {{ color: #8A8577; font-size: 12px; }}
  .bar-track {{ height: 10px; background: #F4F0E4; border-radius: 5px; overflow: hidden; }}
  .bar-fill {{ height: 100%; background: #FFC72C; border-radius: 5px; }}
  .stat-row {{ display: flex; justify-content: space-between; align-items: baseline;
    padding: 9px 0; border-bottom: 1px dashed #EFEAD8; font-size: 14px; }}
  .stat-row:last-child {{ border-bottom: none; }}
  .stat-row .k {{ color: #8A8577; font-size: 13px; }}
  .stat-row .v {{ font-weight: 600; }}
  .split {{ display: flex; height: 14px; border-radius: 7px; overflow: hidden; margin: 6px 0 10px; }}
  .split .d {{ background: #FFC72C; }}
  .split .t {{ background: #E8E2CE; }}
  .split-legend {{ display: flex; gap: 16px; font-size: 12px; color: #8A8577; }}
  .dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }}
  .facts li {{ font-size: 14px; padding: 7px 0 7px 20px; position: relative; list-style: none; }}
  .facts li::before {{ content: ""; position: absolute; left: 2px; top: 14px;
    width: 7px; height: 7px; background: #FFC72C; border-radius: 50%; }}
  .title-card {{ background: #2B2A26; color: #FFF8E7; text-align: center; padding: 34px 20px; }}
  .title-card .kicker {{ color: #FFC72C; }}
  .title-card .title {{ font-size: 34px; font-weight: 800; margin: 8px 0 6px; }}
  .title-card .desc {{ font-size: 13px; opacity: .75; }}
  .demo-badge {{ display: inline-block; background: #DA291C; color: #fff; font-size: 11px;
    padding: 2px 10px; border-radius: 20px; vertical-align: middle; margin-left: 8px; font-weight: 600; }}
  .ending {{ text-align: center; padding: 26px 10px 8px; color: #8A8577; font-size: 12px; }}
  .ending .save {{ font-size: 15px; color: #2B2A26; font-weight: 700; margin-bottom: 6px; }}
  .cover-logo {{ width: 52px; height: 52px; background: #FFC72C; border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; font-weight: 800; color: #DA291C; margin-bottom: 14px; }}
</style>
</head>
<body>
<div class="page">

  <section class="card">
    <div class="cover-logo">M</div>
    <div class="kicker">MCDONALD'S WRAPPED {demo_badge}</div>
    <h1>你的 {r['period_start'][:4]}<br>麦麦年度报告</h1>
    <p class="sub">{r['period_start']} — {r['period_end']} · 共 {r['order_count']} 单 · {r['total_spend_fmt']}</p>
  </section>

  <section class="card">
    <h2>这一年，你的麦门战绩</h2>
    <div class="grid4">
      <div class="metric"><div class="label">下单</div><div class="value">{r['order_count']}<small> 单</small></div></div>
      <div class="metric"><div class="label">总花费</div><div class="value">{r['total_spend_fmt']}</div></div>
      <div class="metric"><div class="label">用券省下</div><div class="value" style="color:#DA291C">{r['total_saved_fmt']}</div></div>
      <div class="metric"><div class="label">摄入热量</div><div class="value">{r['total_kcal'] / 1000:.1f}<small> 千卡</small></div></div>
    </div>
  </section>

  <section class="card">
    <h2>你的年度挚爱餐品</h2>
    {_bar_rows(r['top_items'], r['max_item_qty'])}
  </section>

  <section class="card">
    <h2>热量，都去哪儿了</h2>
    <div class="big">{r['total_kcal']:,.0f}<small> 千卡</small></div>
    <p class="sub" style="margin:4px 0 12px">平均每单 {r['avg_kcal']:,.0f} 千卡，约 {round(r['total_kcal'] / 230)} 碗米饭</p>
    {_facts_html(r['facts'])}
  </section>

  <section class="card">
    <h2>你的吃麦时间画像</h2>
    <div class="stat-row"><span class="k">最常下单时段</span><span class="v">{r['busiest_slot'][0]} · {r['busiest_hour'][0]:02d}:00 档（{r['busiest_hour'][1]} 单）</span></div>
    <div class="stat-row"><span class="k">深夜下单（22 点后）</span><span class="v">{r['late_night']} 单 · 占 {round(r['late_ratio'] * 100)}%</span></div>
    <div class="stat-row"><span class="k">周末占比</span><span class="v">{round(r['weekend'] / max(r['order_count'], 1) * 100)}%</span></div>
    <div class="stat-row"><span class="k">最长连续吃麦</span><span class="v">{r['best_streak']} 天</span></div>
    <div class="stat-row"><span class="k">下单最勤的月份</span><span class="v">{r['busiest_month'][0]} 月 · {r['busiest_month'][1]} 单</span></div>
    <div class="stat-row"><span class="k">平均下单间隔</span><span class="v">{r['avg_days_between']} 天/单</span></div>
  </section>

  <section class="card">
    <h2>麦麦省，你是懂行的</h2>
    <div class="big" style="color:#DA291C">{r['total_saved_fmt']}</div>
    <p class="sub" style="margin:4px 0 12px">全年用券 {r['coupon_count']} 张，省下约 {round(r['total_saved'] / 24.5)} 个巨无霸，省钱率 {round(r['saved_ratio'] * 100)}%</p>
  </section>

  <section class="card">
    <h2>在哪里遇见麦麦</h2>
    <div class="split"><div class="d" style="width:{delivery_pct}%"></div><div class="t" style="width:{100 - delivery_pct}%"></div></div>
    <div class="split-legend">
      <span><span class="dot" style="background:#FFC72C"></span>麦乐送 {r['delivery']} 单（{delivery_pct}%）</span>
      <span><span class="dot" style="background:#E8E2CE"></span>到店自取 {r['takeout']} 单</span>
    </div>
    <div class="stat-row" style="margin-top:10px"><span class="k">年度最常光顾</span><span class="v">{_e(r['top_store'][0])} · {r['top_store'][1]} 次</span></div>
  </section>

  <section class="card">
    <h2>积分小金库</h2>
    <div class="stat-row"><span class="k">可用积分</span><span class="v">{r['points_available']:,}</span></div>
    <div class="stat-row"><span class="k">即将过期积分</span><span class="v" style="color:#DA291C">{r['points_expiring']:,}</span></div>
  </section>

  <section class="card title-card">
    <div class="kicker">你的年度称号</div>
    <div class="title">{_e(r['title'])}</div>
    <div class="desc">全年 {r['order_count']} 单 · 平均每 {r['avg_days_between']} 天就要见一次麦麦</div>
  </section>

  <div class="ending">
    <div class="save">长按保存这张报告，分享给你的饭搭子</div>
    <p>由 mcd-wrapped 生成 · 麦当劳程序员创意开发大赛参赛作品</p>
    <p>数据基于麦当劳中国 MCP 服务 · 仅供娱乐参考</p>
  </div>

</div>
</body>
</html>"""


def _render_empty(report: Dict[str, Any]) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>麦麦年度报告</title></head>
<body style="background:#FFF8E7;font-family:-apple-system,'PingFang SC',sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;">
<div style="text-align:center;color:#2B2A26;">
<div style="font-size:40px;font-weight:800;">暂无订单数据</div>
<p style="color:#8A8577;margin-top:8px;">先用 --token 拉取麦当劳 MCP 订单，或用 --demo 体验演示效果</p>
</div></body></html>"""
