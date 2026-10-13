# 🍔 McDonald's Toolkit — Self-hosted MCP Server (Alexa+ track)

> **Amazon Build, Ship, Shape · Alexa+ track submission.**
> A self-hosted **MCP server** (Streamable HTTP) that exposes practical
> McDonald's tools — lottery expected-value, nutrition lookup, coupons,
> campaigns, points mall — to an MCP client such as **Alexa+**.

Amazon adopted **MCP as the open standard** that powers Alexa+ integrations.
That means you don't write anything Alexa-specific: you write a normal MCP
server, and Alexa+ acts as the MCP client, calling your tools by voice. This
repo is exactly that server, plus a **no-Echo simulation** so the whole flow
can be demoed in a browser without a physical device.

---

## 🎯 Why this fits the Alexa+ track

| Requirement | How this repo satisfies it |
|---|---|
| **Self-hosted MCP server** (Streamable HTTP) | `server.py` runs a FastMCP server on `http://127.0.0.1:8000/mcp` |
| **Or an Agent Skill** | The same tool surface can be wrapped as an Agent Skill (tool schemas are skill-ready) |
| **Brand / service plugs into Alexa+** | McDonald's public data → voice-answerable tools |
| **Works without an Echo** | `simulator/` is a browser-based fake Alexa+ client (per Amazon's own guidance) |
| **Reproducible / open** | MIT licensed, `requirements.txt`, one-command `run_demo.sh` |

---

## 🏗️ Architecture

```
            ┌────────────────────────────┐
   voice ──▶│  Alexa+  (MCP client)      │   (simulated by simulator/ in this repo)
            │  routes intent → tool call │
            └──────────────┬─────────────┘
                           │  Streamable HTTP  (MCP, spec 2025-03-26+)
                           ▼
            ┌────────────────────────────┐
            │  server.py  (this repo)     │   FastMCP, self-hosted
            │  Tools:                     │
            │   • calculate_lottery_ev    │
            │   • lookup_nutrition        │
            │   • list_coupons            │
            │   • campaign_calendar       │
            │   • points_mall_search      │
            └──────────────┬─────────────┘
                           │  reads
                           ▼
            ┌────────────────────────────┐
            │  data/public_data.json      │   shipped public-data snapshot
            │  (no API key required)      │   (McDonald's MCP public slice)
            └────────────────────────────┘
```

In production, Alexa+ connects to the public URL of `server.py` the same way
the simulator does. The simulator exists only so reviewers can see the
voice→tool→answer loop without hardware.

---

## ✨ Tools exposed

| Tool | Purpose | Example voice trigger |
|---|---|---|
| `calculate_lottery_ev` | Monte-Carlo expected value of the points lottery (equal-probability assumption; McDonald's does not publish real odds) | "Is the points lottery worth it?" |
| `lookup_nutrition` | Calorie (kcal) lookup for any menu item, with fuzzy matching | "How many calories in fries?" |
| `list_coupons` | Coupons currently claimable | "What coupons can I claim?" |
| `campaign_calendar` | Recent / upcoming marketing campaigns | "Any new promotions?" |
| `points_mall_search` | Search the points-mall catalogue | "What can I redeem with points?" |

> Every number is grounded in a real public-data snapshot from McDonald's MCP.
> The lottery EV math is explicit about its assumptions and never spends points.

---

## 🚀 Quick start

```bash
# 1) install (Python 3.10+)
pip install -r requirements.txt

# 2) start the MCP server (Streamable HTTP on :8000)
python server.py

# 3) (optional) start the Alexa+ simulator (web UI on :8080)
python simulator/simulator.py

# 4) open http://127.0.0.1:8080 and type a command,
#    or click an example chip.
```

Or run both at once:

```bash
bash run_demo.sh
```

Programmatic client (proves the MCP contract):

```python
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
import asyncio

async def main():
    async with streamablehttp_client("http://127.0.0.1:8000/mcp/") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print([t.name for t in tools.tools])

asyncio.run(main())
```

---

## 🔌 Alexa+ integration notes

- **Transport:** Streamable HTTP — the transport Alexa+ requires. The endpoint
  is `/mcp` (the server issues a `307` to the canonical `/mcp/`; standard HTTP
  clients follow it automatically).
- **No device needed:** Amazon's own docs note you can build a *simulated*
  Alexa+ experience in a web app. `simulator/` is that simulation.
- **Deploy:** wrap `server.py` behind a public HTTPS endpoint (e.g. a container
  + reverse proxy), then register it with the Alexa+ MCP Toolkit
  (`alexa-ai deploy`). Tool names, schemas, and descriptions come straight from
  the `@mcp.tool()` definitions in `server.py`.

---

## 🎬 Demo video script (≤ 3 min, English)

> Record your screen while the simulator (http://127.0.0.1:8080) is open.

1. **(0:00–0:20) Problem.** "Alexa, is the McDonald's points lottery actually
   worth my points?" Today there's no voice-answerable, data-grounded way to
   answer that. Show the simulator's empty chat.
2. **(0:20–0:50) The build.** Open `server.py`, point at the `@mcp.tool()
   def calculate_lottery_ev` decorator. Explain: this is a plain MCP server
   over Streamable HTTP — Alexa+ becomes the client for free because Amazon
   adopted MCP as the standard.
3. **(0:50–1:40) Live demo #1 — lottery EV.** Type *"麦当劳积分抽奖值不值得玩？"*
   Show Alexa's spoken answer: expected coupon value, points returned, and the
   probability of winning. Highlight the "⚙️ called tool calculate_lottery_ev"
   card proving the MCP call.
4. **(1:40–2:20) Live demo #2 — nutrition & coupons.** Type *"薯条有多少卡路里？"*
   and *"现在有什么优惠券可以领？"* Show grounded, data-backed answers.
5. **(2:20–2:50) Why it's real.** Show the architecture: Alexa+ → Streamable
   HTTP → self-hosted MCP server → public-data snapshot. Note it runs with no
   API key and is MIT-licensed.
6. **(2:50–3:00) Close.** "One MCP server, five voice skills, zero hardware.
   That's the Alexa+ opportunity."

---

## 💬 Product feedback (for Amazon)

- **What worked:** Adopting MCP as the Alexa+ integration standard is the right
  call — reusing an existing MCP server took minutes, not weeks. Streamable HTTP
  is straightforward to self-host.
- **Friction (and a bonus opportunity):** Tool *discovery* for non-developer
  brands is still rough; a hosted "MCP server from a spreadsheet / no-code"
  path would unlock a huge long tail of skills. (We logged this as friction for
  the judging bonus.)
- **Wishlist:** A public sandbox Echo simulator in the developer console (the
  web-app simulation works, but an official one would standardize demos) and
  per-tool usage analytics in the Alexa+ MCP Toolkit dashboard.

---

## 📦 Files

```
server.py                 # self-hosted MCP server (Streamable HTTP)
simulator/simulator.py    # fake Alexa+ client (web, stdlib only)
simulator/simulator.html  # Alexa-style chat UI
data/public_data.json     # shipped public-data snapshot (no API key needed)
requirements.txt
run_demo.sh
LICENSE                  # MIT
```

## 📝 License

MIT — see [LICENSE](LICENSE).
