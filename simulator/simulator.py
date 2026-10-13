#!/usr/bin/env python3
"""Alexa+ simulator — a no-Echo way to demo the MCP server.

Amazon's Alexa+ acts as an MCP *client*. To demo without a physical Echo, this
tiny server pretends to be the "Alexa+ brain": it takes a typed (or spoken)
command, routes it to the right MCP tool, calls our self-hosted MCP server over
Streamable HTTP, and returns Alexa's spoken answer plus a visual card.

    python3 simulator/simulator.py            # serves on http://127.0.0.1:8080
    python3 simulator/simulator.py --mcp http://127.0.0.1:8000/mcp/

Only the Python stdlib is used for the web layer; the MCP client uses the
official `mcp` SDK in the same venv.
"""
import argparse
import asyncio
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

HERE = os.path.abspath(os.path.dirname(__file__))
HTTP_DIR = HERE
DEFAULT_MCP = "http://127.0.0.1:8000/mcp/"

# ---------------------------------------------------------------------------
# intent routing: map a free-text command to (tool, arg-builder)
# ---------------------------------------------------------------------------
PRODUCT_HINTS = ["薯条", "麦旋风", "鸡块", "麦辣", "早餐", "咖啡", "套餐", "汉堡",
                 "派", "圆筒", "圣代", "可乐", "鸡翅", "粥", "馒头", "猪柳"]


def route(text):
    t = text.lower()
    if any(k in t for k in ["抽奖", "值不值", "期望", "lottery", "ev", "积分抽奖", "划不划算"]):
        # try to read an explicit draw count like "抽10次"
        m = re.search(r"(\d+)\s*次", text)
        draws = int(m.group(1)) if m else 10
        return "calculate_lottery_ev", {"draws": draws, "trials": 20000}
    if any(k in t for k in ["热量", "卡路里", "kcal", "营养", "calorie", "多少卡"]):
        product = text
        for w in ["热量", "卡路里", "kcal", "营养", "calorie", "多少卡", "查询", "查一下",
                  "看看", "的", "请问", "帮我", "一下", "一个", "里有"]:
            product = product.replace(w, "")
        for h in PRODUCT_HINTS:
            if h in text:
                product = h
                break
        product = product.strip(" ?？。.，,") or "薯条"
        return "lookup_nutrition", {"product": product}
    if any(k in t for k in ["优惠券", "券", "coupon", "领取", "优惠"]):
        return "list_coupons", {}
    if any(k in t for k in ["活动", "campaign", "促销", "新品", "推广", "最近"]):
        return "campaign_calendar", {"limit": 10}
    if any(k in t for k in ["积分商城", "mall", "兑换", "积分换", "商城"]):
        kw = text
        for w in ["积分商城", "mall", "兑换", "积分换", "商城", "查", "看", "有", "什么",
                  "请问", "帮我", "一下", "的", "里", "可以", "能", "呢", "吗",
                  "？", "?", "！", "!", "。", "，", "、"]:
            kw = kw.replace(w, "")
        kw = kw.strip(" ?？。.，,")
        return "points_mall_search", {"keyword": kw, "limit": 10}
    # default: lottery EV, the flagship tool
    return "calculate_lottery_ev", {"draws": 10, "trials": 20000}


async def call_mcp(mcp_url, tool, arguments):
    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
            text = ""
            for c in result.content:
                if getattr(c, "type", "") == "text" or hasattr(c, "text"):
                    text += getattr(c, "text", "")
            return text


class Handler(BaseHTTPRequestHandler):
    mcp_url = DEFAULT_MCP

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HTTP_DIR, "simulator.html"), encoding="utf-8") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        else:
            self._send(404, "not found")

    def do_POST(self):
        if self.path != "/ask":
            self._send(404, "not found")
            return
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        text = (payload.get("text") or "").strip()
        if not text:
            self._send(400, json.dumps({"error": "empty text"}))
            return
        tool, args = route(text)
        try:
            spoken = asyncio.run(call_mcp(self.mcp_url, tool, args))
        except Exception as e:  # noqa: BLE001
            spoken = "调用 MCP 工具时出错了：%s" % e
        self._send(200, json.dumps({
            "heard": text,
            "tool": tool,
            "args": args,
            "spoken": spoken,
        }, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080, help="simulator web port")
    ap.add_argument("--mcp", default=DEFAULT_MCP, help="MCP server streamable URL")
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    Handler.mcp_url = args.mcp
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("Alexa+ simulator  -> http://%s:%d  (MCP: %s)"
          % (args.host, args.port, args.mcp))
    print("Open the page and type a command, or click an example.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
