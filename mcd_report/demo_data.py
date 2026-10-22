"""演示数据：确定性生成一份看起来真实的 2026 吃麦订单历史。

数据为虚构，仅用于离线演示报告效果；真实数据请用 --token 拉取麦当劳 MCP。
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import Dict, List

# 餐品营养数据（千卡/份，参考麦当劳中国官方公开营养信息，演示近似值）
NUTRITION: Dict[str, float] = {
    "巨无霸": 530, "双层吉士堡": 450, "麦辣鸡腿堡": 545, "板烧鸡腿堡": 420,
    "麦香鱼": 380, "薯条(小)": 235, "薯条(中)": 325, "薯条(大)": 440,
    "麦乐鸡(5块)": 245, "可口可乐(中)": 175, "可口可乐(大)": 225,
    "零度可口可乐(中)": 0, "圆筒冰淇淋": 150, "麦旋风(奥利奥)": 300,
    "菠萝派": 235, "香芋派": 245, "脆薯饼": 145, "麦辣鸡翅(2块)": 230,
    "豆浆": 135, "阳光橙": 125, "猪柳蛋麦满分": 415, "吉士蛋麦满分": 335,
    "粟米棒": 185, "玉米杯(小)": 115,
}

PRICES: Dict[str, float] = {
    "巨无霸": 24.5, "双层吉士堡": 21.5, "麦辣鸡腿堡": 25.5, "板烧鸡腿堡": 23.5,
    "麦香鱼": 19.5, "薯条(小)": 9.5, "薯条(中)": 12.0, "薯条(大)": 14.5,
    "麦乐鸡(5块)": 12.5, "可口可乐(中)": 8.5, "可口可乐(大)": 10.5,
    "零度可口可乐(中)": 8.5, "圆筒冰淇淋": 6.0, "麦旋风(奥利奥)": 14.0,
    "菠萝派": 8.5, "香芋派": 8.5, "脆薯饼": 7.5, "麦辣鸡翅(2块)": 12.0,
    "豆浆": 8.0, "阳光橙": 9.0, "猪柳蛋麦满分": 17.5, "吉士蛋麦满分": 14.5,
    "粟米棒": 9.5, "玉米杯(小)": 8.0,
}

STORES = ["麦当劳(中关村大街餐厅)", "麦当劳(五道口购物中心餐厅)", "麦当劳(国贸 SKP 餐厅)"]

MAINS = ["麦辣鸡腿堡", "麦辣鸡腿堡", "麦辣鸡腿堡", "板烧鸡腿堡", "巨无霸", "巨无霸", "双层吉士堡", "麦香鱼"]
BREAKFAST_MAINS = ["猪柳蛋麦满分", "猪柳蛋麦满分", "吉士蛋麦满分"]


def _hour_weights() -> List[int]:
    hours = list(range(24))
    weights = []
    for h in hours:
        if h in (8, 9):
            weights.append(10)
        elif h in (12, 13):
            weights.append(14)
        elif h in (15, 16):
            weights.append(6)
        elif h in (18, 19):
            weights.append(12)
        elif h in (21, 22, 23):
            weights.append(8)
        else:
            weights.append(1)
    return [h for h in hours], weights


def _compose(rng: random.Random, hour: int) -> List[Dict]:
    items: List[Dict] = []

    def add(name: str, qty: int = 1) -> None:
        items.append({"name": name, "qty": qty, "price": PRICES[name], "kcal": NUTRITION[name]})

    if 5 <= hour < 10:  # 早餐
        add(rng.choice(BREAKFAST_MAINS))
        add(rng.choice(["豆浆", "阳光橙", "可口可乐(中)"]))
        if rng.random() < 0.5:
            add("脆薯饼")
    elif 14 <= hour < 17:  # 下午茶
        add(rng.choice(["圆筒冰淇淋", "麦旋风(奥利奥)"]))
        if rng.random() < 0.6:
            add(rng.choice(["菠萝派", "香芋派"]))
    elif hour >= 21 or hour < 4:  # 夜宵
        add(rng.choice(MAINS))
        add(rng.choice(["薯条(中)", "薯条(大)", "麦乐鸡(5块)"]))
        add(rng.choice(["可口可乐(中)", "可口可乐(大)", "零度可口可乐(中)"]))
    else:  # 午/晚餐
        add(rng.choice(MAINS))
        add(rng.choice(["薯条(中)", "薯条(中)", "薯条(大)"]))
        if rng.random() < 0.3:
            add("麦辣鸡翅(2块)")
        if rng.random() < 0.25:
            add(rng.choice(["菠萝派", "香芋派", "圆筒冰淇淋"]))
        add(rng.choice(["可口可乐(中)", "可口可乐(中)", "可口可乐(大)", "零度可口可乐(中)"]))
    return items


def generate_demo(seed: int = 1024, count: int = 47) -> Dict:
    rng = random.Random(seed)
    start, end = date(2026, 1, 6), date(2026, 10, 20)
    days = sorted(rng.sample(range((end - start).days + 1), count))

    hours, weights = _hour_weights()
    orders: List[Dict] = []
    for i, d in enumerate(days):
        day = start + timedelta(days=d)
        hour = rng.choices(hours, weights=weights, k=1)[0]
        ts = datetime(day.year, day.month, day.day, hour, rng.choice([0, 10, 20, 30, 40, 50]))
        items = _compose(rng, hour)
        total = round(sum(it["price"] * it["qty"] for it in items), 1)
        saved = round(rng.uniform(3, 16), 1) if rng.random() < 0.62 else 0.0
        orders.append({
            "order_id": f"MCD2026{i + 1:04d}",
            "ts": ts,
            "channel": "delivery" if rng.random() < 0.62 else "takeout",
            "store": rng.choice(STORES),
            "items": items,
            "total": total,
            "saved": saved,
        })

    coupons = [{"name": f"满 30 减 {c} 元券", "value": c} for c in (3, 5, 8)]
    account = {
        "available_points": 2847,
        "expiring_points": 360,
        "lottery_draws": 6,
        "lottery_wins": 2,
    }
    return {"orders": orders, "coupons": coupons, "account": account}
