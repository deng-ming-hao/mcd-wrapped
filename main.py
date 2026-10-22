#!/usr/bin/env python3
"""麦麦年度报告 CLI。

用法：
    python3 main.py --demo                      # 用内置模拟数据生成演示报告
    python3 main.py --token <MCP_TOKEN>         # 拉取麦当劳 MCP 真实数据生成报告
    python3 main.py --token <TOKEN> --raw-dump raw.json   # 导出原始 MCP 响应，便于适配字段

MCP Token 免费申请：https://open.mcd.cn/mcp
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcd_report.demo_data import NUTRITION, generate_demo
from mcd_report.mcp_client import MCPError, McDonaldsMCP
from mcd_report.render import render_html
from mcd_report.stats import compute_report

DEFAULT_OUTPUT = "mcd-wrapped-report.html"


# ---------- 真实数据归一化（尽力而为，字段名以 --raw-dump 实际响应为准微调） ----------

def _find_first(obj: Any, keys: List[str]) -> Any:
    """递归查找第一个包含目标键的值。"""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] not in (None, "", [], {}):
                return obj[k]
        for v in obj.values():
            found = _find_first(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_first(v, keys)
            if found is not None:
                return found
    return None


def _parse_ts(value: Any) -> Optional[datetime]:
    if isinstance(value, (int, float)) and value > 1e12:  # 毫秒时间戳
        return datetime.fromtimestamp(value / 1000)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
    return None


def normalize_orders(raw: Any) -> List[Dict[str, Any]]:
    """把 order-list 的原始响应归一化为统一订单结构。"""
    orders_raw = _find_first(raw, ["orders", "orderList", "list", "data", "records"])
    if isinstance(orders_raw, dict):
        orders_raw = orders_raw.get("list") or orders_raw.get("records") or [orders_raw]
    if not isinstance(orders_raw, list):
        orders_raw = [raw]

    orders: List[Dict[str, Any]] = []
    for o in orders_raw:
        if not isinstance(o, dict):
            continue
        ts = _parse_ts(_find_first(o, ["createTime", "orderTime", "payTime", "create_time", "time", "ts"]))
        if ts is None:
            continue
        items_raw = _find_first(o, ["products", "items", "meals", "productList", "orderItems", "dishes"]) or []
        items: List[Dict[str, Any]] = []
        for it in (items_raw if isinstance(items_raw, list) else []):
            if not isinstance(it, dict):
                continue
            name = _find_first(it, ["name", "productName", "title", "mealName"]) or "未知餐品"
            qty = _find_first(it, ["quantity", "qty", "count", "num"]) or 1
            price = _find_first(it, ["price", "salePrice", "amount", "currentPrice"]) or 0
            try:
                qty = int(qty)
                price = float(price)
            except (TypeError, ValueError):
                qty, price = 1, 0.0
            items.append({"name": str(name), "qty": qty, "price": price,
                          "kcal": NUTRITION.get(str(name), 0.0)})
        total = _find_first(o, ["totalPrice", "payAmount", "total", "amount", "orderAmount"]) or 0
        saved = _find_first(o, ["discount", "couponAmount", "discountAmount", "savedAmount"]) or 0
        channel_raw = str(_find_first(o, ["orderType", "beType", "channel", "deliveryType"]) or "").lower()
        channel = "delivery" if ("delivery" in channel_raw or "外送" in channel_raw or "麦乐送" in channel_raw) else "takeout"
        store = _find_first(o, ["storeName", "shopName", "store", "name"]) or ""
        try:
            total = float(total)
            saved = float(saved)
        except (TypeError, ValueError):
            total, saved = 0.0, 0.0
        if items:
            orders.append({"order_id": str(_find_first(o, ["orderId", "id", "orderNo"]) or ""),
                           "ts": ts, "channel": channel, "store": str(store),
                           "items": items, "total": total, "saved": saved})
    orders.sort(key=lambda x: x["ts"])
    return orders


def _call(client: McDonaldsMCP, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
    """带清晰上下文的工具调用，失败时知道是哪一步。"""
    try:
        return client.call_tool(name, arguments)
    except MCPError as e:
        raise MCPError(f"调用 {name} 失败：{e}")


def fetch_real(token: str, raw_dump: Optional[str] = None) -> Dict[str, Any]:
    client = McDonaldsMCP(token, verbose=True)
    try:
        client.connect()
    except MCPError as e:
        raise MCPError(f"连接 MCP 失败：{e}")
    print("已连接麦当劳 MCP，开始拉取数据…", file=sys.stderr)

    dump: Dict[str, Any] = {}

    now_raw = _call(client, "now-time-info")
    dump["now-time-info"] = now_raw
    now_text = str(now_raw)
    period_end = "2026-10-22"
    try:
        import re
        m = re.search(r"(\d{4}-\d{2}-\d{2})", now_text)
        if m:
            period_end = m.group(1)
    except Exception:
        pass

    orders_raw = _call(client, "order-list")
    dump["order-list"] = orders_raw
    orders = normalize_orders(orders_raw)
    print(f"归一化订单 {len(orders)} 笔", file=sys.stderr)

    nutrition_raw = _call(client, "list-nutrition-foods")
    dump["list-nutrition-foods"] = nutrition_raw
    foods = _find_first(nutrition_raw, ["foods", "list", "data", "nutritionFoods"]) or []
    kcal_index: Dict[str, float] = {}
    if isinstance(foods, list):
        for f in foods:
            if isinstance(f, dict):
                name = _find_first(f, ["name", "foodName", "title"])
                kcal = _find_first(f, ["energy", "kcal", "calorie", "energyKcal", "energy_kcal"])
                if name and kcal is not None:
                    try:
                        kcal_index[str(name)] = float(kcal)
                    except (TypeError, ValueError):
                        pass
    if kcal_index:
        for o in orders:
            for it in o["items"]:
                if it["name"] in kcal_index:
                    it["kcal"] = kcal_index[it["name"]]
        print(f"营养索引命中 {len(kcal_index)} 个餐品", file=sys.stderr)

    coupons_raw = _call(client, "query-my-coupons")
    dump["query-my-coupons"] = coupons_raw
    coupons_list = _find_first(coupons_raw, ["coupons", "list", "data"]) or []
    if not isinstance(coupons_list, list):
        coupons_list = []

    account_raw = _call(client, "query-my-account")
    dump["query-my-account"] = account_raw
    account = {
        "available_points": int(_find_first(account_raw, ["availablePoints", "available", "points", "balance"]) or 0),
        "expiring_points": int(_find_first(account_raw, ["expiringPoints", "expiring", "willExpirePoints"]) or 0),
    }

    if raw_dump:
        with open(raw_dump, "w", encoding="utf-8") as f:
            json.dump(dump, f, ensure_ascii=False, indent=2, default=str)
        print(f"原始响应已导出：{raw_dump}", file=sys.stderr)

    period_start = orders[0]["ts"].strftime("%Y-%m-%d") if orders else f"{period_end[:4]}-01-01"
    return {"orders": orders, "coupons": coupons_list, "account": account,
            "period_start": period_start, "period_end": period_end}


def main() -> None:
    parser = argparse.ArgumentParser(description="麦麦年度报告 · McDonald's Wrapped")
    parser.add_argument("--demo", action="store_true", help="使用内置模拟数据（无需 Token）")
    parser.add_argument("--token", default=os.environ.get("MCD_MCP_TOKEN"), help="麦当劳 MCP Token")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="输出 HTML 路径")
    parser.add_argument("--raw-dump", help="导出原始 MCP 响应 JSON，便于适配字段")
    parser.add_argument("--selftest", action="store_true",
                        help="仅做连通性自检（握手 + 拉取工具列表），不生成报告")
    args = parser.parse_args()

    if args.selftest:
        try:
            client = McDonaldsMCP(args.token, verbose=True)
            tools = client.selftest()
        except MCPError as e:
            print(f"自检失败：{e}", file=sys.stderr)
            sys.exit(1)
        print(f"连接成功，可用工具 {len(tools)} 个：")
        for name in tools:
            print(f"  - {name}")
        return

    if not args.demo and not args.token:
        parser.error("请使用 --demo 体验演示，或用 --token <TOKEN> 生成真实报告（Token 申请：https://open.mcd.cn/mcp）")

    if args.demo:
        data = generate_demo()
        period_start = data["orders"][0]["ts"].strftime("%Y-%m-%d")
        period_end = data["orders"][-1]["ts"].strftime("%Y-%m-%d")
        report = compute_report(data["orders"], NUTRITION, data["coupons"], data["account"],
                                period_start, period_end, demo=True)
    else:
        try:
            data = fetch_real(args.token, args.raw_dump)
        except MCPError as e:
            print(f"MCP 调用失败：{e}", file=sys.stderr)
            sys.exit(1)
        report = compute_report(data["orders"], NUTRITION, data["coupons"], data["account"],
                                data["period_start"], data["period_end"])

    html_text = render_html(report)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_text)
    print(f"报告已生成：{args.output}（{report.get('order_count', 0)} 单，年度称号：{report.get('title', '-')}）")


if __name__ == "__main__":
    main()
