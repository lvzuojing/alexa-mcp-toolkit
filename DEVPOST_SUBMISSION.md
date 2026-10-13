# Devpost Submission — Amazon Build, Ship, Shape (Alexa+ track)

> Copy the sections below into the Devpost entry form. Replace the
> `DEMO_VIDEO_URL` placeholder with your uploaded video link.

---

**Project name:** McDonald's Toolkit — Self-hosted MCP Server for Alexa+

**Tagline (one line):** A self-hosted MCP server that turns McDonald's public
data into five voice-callable tools — lottery expected-value, nutrition,
coupons, campaigns, points mall — for Alexa+.

**Demo video URL:** `DEMO_VIDEO_URL`

**Built with:** Python · FastMCP (Model Context Protocol) · Streamable HTTP ·
Alexa+ (MCP client) · self-hosted on `http://127.0.0.1:8000/mcp`

---

## Story

### Inspiration
Amazon adopted **MCP as the open standard** that powers Alexa+ integrations.
That means you don't write anything Alexa-specific — you write a normal MCP
server and Alexa+ becomes the client. I wanted to prove how little glue that
takes by exposing a brand's public data (McDonald's) as voice-callable tools.

### What it does
A self-hosted MCP server (Streamable HTTP) exposing five tools:
- `calculate_lottery_ev` — Monte-Carlo expected value of the points lottery
  (equal-probability assumption; McDonald's publishes no real odds).
- `lookup_nutrition` — calorie (kcal) lookup for any menu item, fuzzy-matched.
- `list_coupons` — coupons currently claimable.
- `campaign_calendar` — recent / upcoming marketing campaigns.
- `points_mall_search` — search the points-mall catalogue.

### How we built it
- `server.py` — a FastMCP server over **Streamable HTTP** (the transport Alexa+
  requires), reading a shipped public-data snapshot so it runs with **no API
  key**.
- `simulator/` — a browser-based "fake Alexa+" so the full voice→tool→answer
  loop is demoable **without a physical Echo** (per Amazon's own guidance).
- Every number is grounded in real public data; the EV math states its
  assumptions and never spends points.

### Challenges we ran into
Tool *discovery* for non-developer brands is still rough — a hosted
"MCP-from-spreadsheet / no-code" path would unlock a huge long tail of skills.
(Logged as friction for the judging bonus.)

### Accomplishments we're proud of
A working, reproducible, MIT-licensed MCP server that an Alexa+ user could
literally talk to, built and demoed without any proprietary hardware.

### What's next
Wrap `server.py` behind a public HTTPS endpoint and register it with the Alexa+
MCP Toolkit (`alexa-ai deploy`); add a hosted no-code MCP builder as the
friction fix.

### What we learned
Adopting MCP as the integration standard is the right call — reusing an
existing MCP server took minutes, not weeks.

---

## Judging criteria mapping
- **Tech Implementation:** real Streamable HTTP MCP server + client, verified
  end-to-end (`initialize → list_tools → call_tool`).
- **Design:** clean tool schemas with descriptions that drive intent routing;
  a no-Echo simulation for accessibility.
- **Potential Impact:** any brand's public data → voice skills with near-zero
  glue; the friction fix (no-code MCP) scales it.
- **Quality of Idea:** demonstrates the core Alexa+ thesis — MCP as the
  integration standard.
