#!/usr/bin/env python3
"""McDonald's Toolkit — self-hosted MCP Server (Streamable HTTP).

This is the deliverable for the **Amazon Build, Ship, Shape** hackathon,
Alexa+ track. Alexa+ acts as an MCP *client*: a customer says something like
"Alexa, is the McDonald's points lottery worth it?", Alexa+ routes the request
to this server over Streamable HTTP, and the server returns a grounded answer.

Tools exposed (all read from a shipped public-data snapshot, no API key needed):
  - calculate_lottery_ev : Monte-Carlo expected value of the points lottery
  - lookup_nutrition     : calorie (kcal) lookup for any menu item
  - list_coupons         : coupons currently claimable
  - campaign_calendar    : recent / upcoming marketing campaigns
  - points_mall_search   : search the points-mall catalogue

Transport: Streamable HTTP (the transport Alexa+ requires). Run:

    python3 server.py                # serves on http://127.0.0.1:8000/mcp
    python3 server.py --port 9000    # custom port
"""
import argparse
import json
import os
import random
import re
from datetime import datetime

from mcp.server.fastmcp import FastMCP

ROOT = os.path.abspath(os.path.dirname(__file__))
DATA = os.path.join(ROOT, "data", "public_data.json")

DISCOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*折")
CASH_RE = re.compile(r"立减\s*(\d+(?:\.\d+)?)\s*元")
POINTS_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*积分$")

# Discount vouchers are worth different amounts depending on what they apply to,
# so pick a basket price that matches the prize name before falling back.
BASE_HINTS = [
    ("麦旋风", 9.0), ("甜筒", 7.0), ("薯条", 13.0), ("麦辣鸡翅", 15.0),
    ("四件套", 46.0), ("三件套", 40.0), ("小食", 26.0), ("套餐", 36.0),
    ("咖啡", 18.0), ("早餐", 20.0),
]


def load_data():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def estimate_value(name, base_price):
    """Return (yuan, points, kind) parsed from a prize name.

    Yuan figures are estimates: the pool carries no prices, so discount
    vouchers are valued against a basket price inferred from the prize name.
    """
    name = (name or "").strip()
    m = POINTS_RE.match(name)
    if m:
        return 0.0, float(m.group(1)), "积分"
    m = CASH_RE.search(name)
    if m:
        return float(m.group(1)), 0.0, "立减券"
    m = DISCOUNT_RE.search(name)
    if m:
        rate = float(m.group(1)) / 10.0
        if 0 < rate < 1:
            price = base_price
            for hint, p in BASE_HINTS:
                if hint in name:
                    price = p
                    break
            return round(price * (1 - rate), 2), 0.0, "折扣券"
    return 0.0, 0.0, "未识别"


def simulate(prizes, trials, draws, seed=42):
    """Equal-probability Monte Carlo over `trials` runs of `draws` draws."""
    rnd = random.Random(seed)
    n = len(prizes)
    yuan_tot, point_tot = 0.0, 0.0
    hit_any = 0
    per_prize = {p["name"]: 0 for p in prizes}
    for _ in range(trials):
        got_yuan = got_points = 0.0
        got_any = False
        for _ in range(draws):
            p = prizes[rnd.randrange(n)]
            got_yuan += p["yuan"]
            got_points += p["points"]
            if p["kind"] != "未识别":
                got_any = True
            per_prize[p["name"]] += 1
        yuan_tot += got_yuan
        point_tot += got_points
        if got_any:
            hit_any += 1
    return {
        "avg_yuan": yuan_tot / trials,
        "avg_points": point_tot / trials,
        "p_any": hit_any / trials,
        "per_prize": {k: v / (trials * draws) for k, v in per_prize.items()},
    }


mcp = FastMCP(
    "McDonald's Toolkit MCP Server",
    host="127.0.0.1",
    port=8000,
)


@mcp.tool()
def calculate_lottery_ev(draws: int = 10, trials: int = 20000, base_price: float = 40.0) -> str:
    """Estimate whether McDonald's points lottery is worth playing.

    Runs a Monte-Carlo simulation under an explicit equal-probability
    assumption (McDonald's does not publish real odds). Returns the expected
    coupon value, points returned, and the probability of winning at least one
    prize across `draws` draws. Use this when a user asks if the lottery /
    draw is worth it, or what the expected value is.
    """
    data = load_data()
    lot = data.get("lottery") or {}
    prize_names = [p.get("name") for p in (lot.get("prizes") or [])
                   if isinstance(p, dict)]
    if not prize_names:
        return "没有拿到奖池数据。"
    prizes = []
    for name in prize_names:
        yuan, points, kind = estimate_value(name, base_price)
        prizes.append({"name": name, "yuan": yuan, "points": points, "kind": kind})
    sim = simulate(prizes, trials, draws)
    cost = float(lot.get("cost") or 0)
    spend = cost * draws
    lines = [
        f"麦当劳「{lot.get('name', '麦麦积分抽奖')}」抽奖期望值分析（等概率假设模拟 {trials:,} 轮）",
        f"单次消耗 {cost:g} 积分，每轮抽 {draws} 次，共花 {spend:g} 积分。",
    ]
    lines.append(
        f"每轮期望券面额：¥{sim['avg_yuan']:.2f}"
    )
    if spend:
        lines.append(
            f"每轮期望积分返还：{sim['avg_points']:.1f} 积分（回本率 "
            f"{100 * sim['avg_points'] / spend:.1f}%）"
        )
    else:
        lines.append(f"每轮期望积分返还：{sim['avg_points']:.1f} 积分")
    lines.append(f"至少中 1 个有效奖的概率：{100 * sim['p_any']:.1f}%")
    ranked = sorted(sim["per_prize"].items(), key=lambda x: x[1], reverse=True)[:5]
    lines.append("常见奖品中签率（前5）：")
    for name, rate in ranked:
        lines.append(f"  - {name}：{100 * rate:.1f}%")
    lines.append(
        "结论：只算积分返还会净亏；真实价值在券，且券要用掉才值钱。"
        "麦当劳未公布真实概率，本结果仅为等概率假设下的模拟。"
    )
    return "\n".join(lines)


@mcp.tool()
def lookup_nutrition(product: str) -> str:
    """Look up the calorie (kcal) content of a McDonald's menu item by name.

    Returns the kcal value, or the closest matches if the exact name is not
    found, or the highest-calorie items if nothing matches. Use when a user
    asks about calories, nutrition, or how many kcal something has.
    """
    data = load_data()
    nut = data.get("nutrition_kcal") or {}
    if product in nut:
        return f"{product}：{nut[product]:.0f} 千卡 (kcal)。"
    matches = [k for k in nut if product in k or k in product]
    if matches:
        return ("未找到精确匹配，但以下相近项可用：\n"
                + "\n".join(f"  - {k}：{nut[k]:.0f} kcal" for k in matches[:8]))
    top = sorted(nut.items(), key=lambda x: x[1], reverse=True)[:10]
    return ("未找到该单品。热量最高的几款：\n"
            + "\n".join(f"  - {k}：{v:.0f} kcal" for k, v in top))


@mcp.tool()
def list_coupons() -> str:
    """List coupons currently claimable from McDonald's 麦麦省.

    Use when a user asks about available coupons, vouchers, or current deals.
    """
    data = load_data()
    coupons = data.get("coupons") or []
    if not coupons:
        return "当前没有可领取的优惠券。"
    return ("当前可领取优惠券：\n"
            + "\n".join(f"  - {c.get('title')}（{str(c.get('status', '')).rstrip('\\\\').strip()}）"
                        for c in coupons))


@mcp.tool()
def campaign_calendar(limit: int = 10) -> str:
    """Return recent / upcoming McDonald's marketing campaigns (title + date).

    Use when a user asks about current promotions, events, or what's new.
    """
    data = load_data()
    camps = data.get("campaigns") or []
    if not camps:
        return "暂无活动信息。"
    camps = camps[:limit]
    return ("近期营销活动：\n"
            + "\n".join(f"  - [{c.get('date', '')}] {c.get('title', '')}" for c in camps))


@mcp.tool()
def points_mall_search(keyword: str = "", limit: int = 10) -> str:
    """Search the McDonald's points-mall catalogue by keyword (name/category).

    With an empty keyword returns currently on-sale items. Use when a user
    asks about redeeming points, the points mall, or what they can exchange.
    """
    data = load_data()
    mall = data.get("mall") or []
    if keyword:
        mall = [m for m in mall
                if keyword in (m.get("name", "") or "")
                or keyword in (m.get("cat", "") or "")]
    if not mall:
        return "积分商城没有匹配项。"
    mall = mall[:limit]
    return ("积分商城：\n"
            + "\n".join(f"  - {m.get('name')}：{m.get('points', 0):.0f}积分 / "
                        f"¥{m.get('price', 0):.0f}（{m.get('status', '')}）" for m in mall))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000, help="Streamable HTTP port")
    ap.add_argument("--host", default="127.0.0.1", help="bind host")
    args = ap.parse_args()
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
