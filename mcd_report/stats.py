"""统计引擎：把订单/营养/优惠券/积分数据算成一份年度报告。

输入为归一化后的订单列表（见 demo_data.py 或 main.py 的归一化逻辑）：
order = {
    "ts": datetime, "channel": "delivery"|"takeout", "store": str,
    "items": [{"name": str, "qty": int, "price": float, "kcal": float}],
    "total": float, "saved": float,
}
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List

RICE_BOWL_KCAL = 230.0   # 一碗米饭约 230 千卡
RUN_KCAL_PER_HOUR = 550.0  # 60kg 成年人跑步每小时约消耗 550 千卡
BIGMAC_PRICE = 24.5        # 巨无霸参考单价

MEAL_SLOTS = [
    (5, 10, "早餐"),
    (10, 14, "午餐"),
    (14, 17, "下午茶"),
    (17, 21, "晚餐"),
    (21, 24, "夜宵"),
    (0, 5, "凌晨"),
]


def _slot_of(hour: int) -> str:
    for start, end, name in MEAL_SLOTS:
        if start <= hour < end:
            return name
    return "其他"


def _fmt_money(v: float) -> str:
    return f"¥{v:,.0f}" if v == int(v) else f"¥{v:,.1f}"


def compute_report(
    orders: List[Dict[str, Any]],
    nutrition: Dict[str, float],
    coupons: List[Dict[str, Any]],
    account: Dict[str, Any],
    period_start: str = "2026-01-01",
    period_end: str = "2026-10-22",
    demo: bool = False,
) -> Dict[str, Any]:
    n = len(orders)
    r: Dict[str, Any] = {"demo": demo, "order_count": n,
                         "period_start": period_start, "period_end": period_end}
    if n == 0:
        r["empty"] = True
        return r

    total_spend = sum(o["total"] for o in orders)
    total_saved = sum(o.get("saved", 0.0) for o in orders)

    # ---- 餐品统计 ----
    item_qty: Counter = Counter()
    item_orders: Counter = Counter()
    item_kcal: Dict[str, float] = {}
    for o in orders:
        for it in o["items"]:
            item_qty[it["name"]] += it["qty"]
            item_orders[it["name"]] += 1
            item_kcal.setdefault(it["name"], it.get("kcal", 0.0))
    total_kcal = sum(qty * kcal for name, kcal in item_kcal.items() for qty in [item_qty[name]])

    top_items = [
        {"name": name, "qty": qty, "kcal": item_kcal.get(name, 0.0)}
        for name, qty in item_qty.most_common(5)
    ]

    # ---- 时间画像 ----
    hour_counter: Counter = Counter(h["ts"].hour for h in orders)
    slot_counter: Counter = Counter(_slot_of(h["ts"].hour) for h in orders)
    late_night = sum(c for h, c in hour_counter.items() if h >= 22 or h < 4)
    weekend = sum(1 for o in orders if o["ts"].weekday() >= 5)
    busiest_hour = hour_counter.most_common(1)[0] if hour_counter else (0, 0)
    busiest_slot = slot_counter.most_common(1)[0] if slot_counter else ("午餐", 0)

    months: Counter = Counter(o["ts"].month for o in orders)
    busiest_month = months.most_common(1)[0]

    # ---- 连续吃麦天数 ----
    days = sorted({o["ts"].date() for o in orders})
    best_streak = cur = 1
    for i in range(1, len(days)):
        cur = cur + 1 if (days[i] - days[i - 1]).days == 1 else 1
        best_streak = max(best_streak, cur)

    # ---- 渠道与门店 ----
    delivery = sum(1 for o in orders if o.get("channel") == "delivery")
    store_counter: Counter = Counter(o.get("store", "") for o in orders if o.get("store"))
    top_store = store_counter.most_common(1)[0] if store_counter else ("", 0)

    # ---- 积分 ----
    points_available = account.get("available_points", 0)
    points_expiring = account.get("expiring_points", 0)

    # ---- 年度称号 ----
    late_ratio = late_night / n
    avg_kcal = total_kcal / n
    saved_ratio = total_saved / max(total_spend, 1)
    if n >= 40:
        title = "麦门终身荣誉会员"
    elif late_ratio >= 0.18:
        title = "深夜铲S官"
    elif total_saved >= 500:
        title = "麦麦省钱刺客"
    elif avg_kcal >= 850:
        title = "热量炸弹鉴赏家"
    elif n >= 25:
        title = "麦门忠实信徒"
    else:
        title = "麦麦干饭人"

    # ---- 趣味事实 ----
    facts: List[str] = []
    rice_bowls = round(total_kcal / RICE_BOWL_KCAL)
    run_hours = round(total_kcal / RUN_KCAL_PER_HOUR, 1)
    facts.append(f"全年摄入约 {total_kcal:,.0f} 千卡，约等于 {rice_bowls} 碗米饭，得连跑 {run_hours} 小时才能消耗掉")
    if total_saved > 0:
        facts.append(f"用券省下 {_fmt_money(total_saved)}，差不多是 {round(total_saved / BIGMAC_PRICE)} 个巨无霸")
    if late_ratio >= 0.1:
        facts.append(f"深夜（22 点后）下单 {late_night} 次，麦门是你随叫随到的深夜食堂")
    if best_streak >= 3:
        facts.append(f"最长连续 {best_streak} 天吃麦，麦门已融入你的生物钟")
    if weekend >= n * 0.3:
        facts.append(f"{round(weekend / n * 100)}% 的单下在周末，周末的快乐是麦麦给的")
    if points_expiring > 0:
        facts.append(f"有 {points_expiring:,} 积分即将过期，别让它们悄悄溜走")

    r.update({
        "total_spend": total_spend,
        "total_spend_fmt": _fmt_money(total_spend),
        "total_saved": total_saved,
        "total_saved_fmt": _fmt_money(total_saved),
        "saved_ratio": saved_ratio,
        "total_kcal": total_kcal,
        "avg_kcal": avg_kcal,
        "top_items": top_items,
        "max_item_qty": top_items[0]["qty"] if top_items else 1,
        "busiest_hour": busiest_hour,
        "busiest_slot": busiest_slot,
        "late_night": late_night,
        "late_ratio": late_ratio,
        "weekend": weekend,
        "delivery": delivery,
        "takeout": n - delivery,
        "top_store": top_store,
        "busiest_month": busiest_month,
        "best_streak": best_streak,
        "coupon_count": len(coupons),
        "points_available": points_available,
        "points_expiring": points_expiring,
        "title": title,
        "facts": facts,
        "avg_order_value": total_spend / n,
        "avg_days_between": round(
            (datetime.strptime(period_end, "%Y-%m-%d") - datetime.strptime(period_start, "%Y-%m-%d")).days / max(n, 1), 1
        ),
    })
    return r
