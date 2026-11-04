# Land Truth Agent

A multi-agent built with the [Strands Agents SDK](https://strandsagents.com) that
checks a land broker's claims against independent data, for villagers and small
buyers in Tamil Nadu, India.

## Problem

Brokers describe a plot as having "good rain" or "water available" and set the
price themselves. Buyers, especially in rural areas, have no easy way to check
these claims before paying an advance.

## What it does

You describe the village and the broker's claims. The agent:

1. Calls a **water analyst** sub-agent, which checks real rainfall history
   (Open-Meteo ERA5 reanalysis, live) and groundwater status.
2. Calls a **price analyst** sub-agent, which compares the quoted price per
   cent against the government guideline value.
3. Labels each claim as **supported**, **not supported**, or **not enough
   data** — it never asserts a claim it can't back with data.
4. Lists questions to ask the broker and documents to request (patta, chitta,
   EC, sale deeds, water source proof).
5. Remembers the conversation across restarts (`FileSessionManager`), so you
   can come back and compare a second plot.

## Architecture

```
          ┌───────────────────┐
  You ──▶ │   Coordinator      │
          │   (chat.py agent)  │
          └─────────┬──────────┘
            ┌────────┴─────────┐
            ▼                  ▼
   ┌─────────────────┐  ┌──────────────────┐
   │  water_analyst   │  │  price_analyst    │
   │  (sub-agent)     │  │  (sub-agent)       │
   └────────┬─────────┘  └─────────┬──────────┘
            ▼                      ▼
  get_rainfall_history      get_guideline_value
  get_groundwater_status    check_quoted_price
            │                      │
     Open-Meteo API         data/*.json (local)
```

## Data sources

- **Rainfall**: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
  — free, no key, ERA5 reanalysis grid (not a physical rain gauge).
- **Groundwater**: `data/groundwater.json` — fill from the
  [CGWB](https://cgwb.gov.in) / [India-WRIS](https://indiawris.gov.in) groundwater
  resource reports.
- **Guideline value**: `data/guideline_values.json` — fill from the
  [TN registration department guideline value site](https://tnreginet.gov.in).

Entries in the JSON files start as placeholders (`"verified": false`). The
agent explicitly tells the user when a figure hasn't been verified, instead of
presenting it as fact. Replace them with real sourced numbers before using
this for a real decision — see `data/README.md`.

## Honest limitations

- Rainfall is a model estimate for the grid cell, not the exact plot.
- There is no single authoritative "market price" source; the agent can only
  compare to the guideline value and flag outliers.
- This is not legal or valuation advice. It always tells the user to verify
  title with a registered surveyor/lawyer before paying any advance.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
aws sso login   # or aws configure, if Bedrock model access is set up
```

### Option A: web chatbot (recommended for demos and real users)

```powershell
streamlit run app.py
```

Opens a browser chat window at `http://localhost:8501`. Pick the reply
language and a session ID in the sidebar, then type a question like:
`A broker says Annur has good rain and water, and wants Rs 400000 per cent. Is that true?`

### Option B: terminal chat

```powershell
chcp 65001      # so emoji / ₹ display correctly in this terminal
python chat.py
```

### Tamil support

```powershell
python chat.py --lang ta   # always answer in Tamil, even if you type English
python chat.py --lang en   # always answer in English
python chat.py             # auto: answers in Tamil when you type Tamil script
```

The coordinator passes the language rule to both specialist agents, so the
whole report comes back in Tamil. Village names and document names (patta,
chitta, EC) stay recognisable, and numbers stay in digits.

To use a Nova model instead of the default Claude model (e.g. with
sponsored/hackathon AWS credits):

```powershell
$env:MODEL_ID = "amazon.nova-pro-v1:0"
python chat.py
```

## Built with

[Strands Agents SDK](https://strandsagents.com) — multi-agent delegation,
hooks, system-prompt steering, and `FileSessionManager` for persistent memory.
Built from the patterns in the
[Strands Agents Hands-On Workshop](https://github.com/aws-samples/sample-strands-agents-hands-on-workshop).
