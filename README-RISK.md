# Risk module

Portfolio risk management scaffold layered on top of this repo:

```
risk/             pure-numerical: VaR, CVaR, EWMA vol, drawdown, factor model, stress tests
llm/              Claude wrapper + scenario / briefing prompts (no math, no trade calls)
api/              FastAPI backend exposing risk/ + llm/ as JSON endpoints
web/              Vite + React + TS + Tailwind dashboard (consumes the API)
scripts/          dev.sh / dev.bat — start backend and frontend together
main_risk.py      synthetic-data CLI smoke test
```

Architectural rule: **the LLM never does math and never recommends trades.**
All numbers (VaR, betas, drawdown, stress-test impacts) are computed in
`risk/`. The LLM only enumerates adverse scenarios as JSON shocks (which
`risk.stress.apply_shock` then evaluates) and writes prose summaries of
already-computed numbers.

## Install

```bash
pip install -r requirements-risk.txt
```

## Smoke test

```bash
python main_risk.py
# enable LLM scenarios + briefing:
ANTHROPIC_API_KEY=sk-... python main_risk.py
```

`main_risk.py` builds 18 years of synthetic factor and sector returns, fits
the factor model, runs the stress tests against canonical historical windows
(GFC 2008, COVID 2020, Rate Hikes 2022, SVB 2023), and — if a key is set —
calls Claude for adverse scenarios and a prose briefing.

## API surface

```python
from risk import (
    value_at_risk, conditional_var, ewma_volatility,
    max_drawdown, sharpe_ratio, sortino_ratio, calmar_ratio,
    effective_n, portfolio_summary,
    estimate_factor_exposures, portfolio_factor_exposure,
    historical_factor_shocks, apply_shock, run_stress_tests,
    SCENARIO_WINDOWS,
)
from llm import ClaudeClient, generate_scenarios, generate_risk_briefing
```

## Conventions

- Returns are `pd.Series` (or `pd.DataFrame` per asset/factor) of **simple**
  periodic returns.
- VaR / CVaR use loss convention: a -3% return becomes +0.03.
- Max drawdown is a positive magnitude (0.30 = 30% drawdown).
- Annualization uses 252 trading days unless overridden.
- `estimate_factor_exposures` does OLS via `np.linalg.pinv` on raw arrays —
  pandas matmul on misaligned or near-collinear data silently propagates
  NaN coefficients, so the linear algebra deliberately drops to numpy.

## Plugging in real data

Replace `_build_synthetic_data()` in `main_risk.py` with a loader that
returns `(factor_returns, sector_returns)` as DataFrames indexed by date,
where columns are factor / sector names and values are simple daily returns.
For the API/dashboard, swap the loader passed to `init_context()` in
`api/main.py` (or call `init_context(my_loader)` before app startup).
Everything downstream is data-shape agnostic.

---

# Web dashboard

A FastAPI backend (`api/`) exposes the `risk/` and `llm/` modules as JSON
endpoints, and a Vite + React + TypeScript + Tailwind SPA (`web/`) consumes
them. Single local user — no auth, no DB, no global state library.

## Architecture

```
   browser (web/, :5173)
        │
        ▼  fetch JSON
   FastAPI (api/, :8000)
        │
        ▼  function calls
   risk/  (numerics)        llm/  (Claude — scenarios + briefings only)
```

The LLM still never does math and never recommends trades; the system
prompts in `llm/reports.py` encode that, and the API just routes through.

## Setup (one-time)

### macOS / Linux

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-risk.txt
pip install 'fastapi>=0.110' 'uvicorn[standard]>=0.29' 'pydantic>=2.5'

# Frontend
cd web && npm install && cd ..
```

### Windows (cmd / PowerShell)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-risk.txt
pip install fastapi "uvicorn[standard]" pydantic

cd web
npm install
cd ..
```

(PowerShell users: activate with `.venv\Scripts\Activate.ps1`.)

## Run

### Both processes together

```bash
# macOS/Linux
./scripts/dev.sh

# Windows
scripts\dev.bat
```

### Or separately

```bash
# terminal 1 — backend
uvicorn api.main:app --reload --port 8000

# terminal 2 — frontend
cd web && npm run dev
```

Then open http://localhost:5173.

The LLM endpoints are **opt-in**. They are off by default — the deterministic
risk pipeline (overview, exposures, historical stress tests) always works,
but the scenario generator and risk briefing only appear when the backend
is started with `ENABLE_LLM=true` *and* `ANTHROPIC_API_KEY` set. While
disabled, `/llm/scenarios` and `/llm/briefing` return HTTP 404 and the
front-end hides those UI affordances; `GET /capabilities` reports
`{"llm_enabled": false}` so the dashboard can adapt without probing.

`scripts/dev.sh` and `scripts/dev.bat` deliberately scrub
`ANTHROPIC_API_KEY` from the backend env unless `ENABLE_LLM` is set, so
having the key in your shell does not silently re-enable LLM calls.

To turn LLM features on:

```bash
# macOS / Linux
export ENABLE_LLM=true
export ANTHROPIC_API_KEY=sk-...
./scripts/dev.sh

# Windows (cmd)
set ENABLE_LLM=true
set ANTHROPIC_API_KEY=sk-...
scripts\dev.bat
```

To turn them off again, simply unset `ENABLE_LLM` (the dev scripts will then
strip the API key on launch).

## API endpoints

| Method | Path                    | Body                                                    | Returns                                |
| ------ | ----------------------- | ------------------------------------------------------- | -------------------------------------- |
| GET    | `/health`               | —                                                       | `{ok: true}`                           |
| GET    | `/capabilities`         | —                                                       | `{llm_enabled: bool}`                  |
| GET    | `/universe`             | —                                                       | `{sectors, factors}`                   |
| POST   | `/portfolio/summary`    | `{weights}`                                             | `portfolio_summary()` dict             |
| POST   | `/portfolio/exposures`  | `{weights}`                                             | `{factor: beta, ...}`                  |
| POST   | `/stress/historical`    | `{weights}`                                             | `{scenario: impact, ...}`              |
| POST   | `/stress/hypothetical`  | `{weights, shocks}`                                     | `{impact}`                             |
| POST   | `/llm/scenarios`†       | `{macro_context, n_scenarios}`                          | `{scenarios: [...]}` (JSON from Claude) |
| POST   | `/llm/briefing`†        | `{summary, exposures, stress_results, macro_context?}`  | `text/plain` stream                    |

† Only mounted when `ENABLE_LLM=true`; otherwise they 404.

Validation: weights must sum to ~1.00 (tolerance 0.01) — otherwise 422. Unknown
sector or factor names → 400.

> Note: I implemented `/stress/historical` as POST (not GET) because the body
> is JSON; GET-with-body is not supported well by `fetch()` or many HTTP
> clients. The frontend uses POST throughout for body-bearing endpoints.

## curl examples

```bash
# Universe
curl -s http://localhost:8000/universe

# Summary
curl -s -X POST http://localhost:8000/portfolio/summary \
  -H 'Content-Type: application/json' \
  -d '{"weights":{"Tech":0.30,"Financials":0.20,"Energy":0.15,"Healthcare":0.20,"Utilities":0.15}}'

# Exposures
curl -s -X POST http://localhost:8000/portfolio/exposures \
  -H 'Content-Type: application/json' \
  -d '{"weights":{"Tech":0.30,"Financials":0.20,"Energy":0.15,"Healthcare":0.20,"Utilities":0.15}}'

# Historical stress
curl -s -X POST http://localhost:8000/stress/historical \
  -H 'Content-Type: application/json' \
  -d '{"weights":{"Tech":0.30,"Financials":0.20,"Energy":0.15,"Healthcare":0.20,"Utilities":0.15}}'

# Hypothetical shock
curl -s -X POST http://localhost:8000/stress/hypothetical \
  -H 'Content-Type: application/json' \
  -d '{"weights":{"Tech":0.30,"Financials":0.20,"Energy":0.15,"Healthcare":0.20,"Utilities":0.15},
       "shocks":{"Equity":-0.20,"Rates":0.02,"Credit":-0.05,"Oil":-0.30}}'

# LLM scenarios (requires ANTHROPIC_API_KEY)
curl -s -X POST http://localhost:8000/llm/scenarios \
  -H 'Content-Type: application/json' \
  -d '{"macro_context":"persistent inflation, hawkish Fed","n_scenarios":3}'

# Streamed briefing (requires ANTHROPIC_API_KEY)
curl -N -X POST http://localhost:8000/llm/briefing \
  -H 'Content-Type: application/json' \
  -d '{"summary":{"var_95":0.02,"max_drawdown":0.18,"sharpe":-0.4},
       "exposures":{"Equity":0.9,"Rates":-0.4},
       "stress_results":{"GFC_2008":-0.55,"COVID_2020":-0.27}}'
```

## UI layout

- Left sidebar: per-sector weight inputs, live sum indicator (red if not
  ~1.00), Normalize / Equal-weight buttons, Analyze button.
- Main area, four stacked sections:
  1. **Overview** — metric cards (annualized return, vol, VaR, CVaR, max
     drawdown, Sharpe, Sortino, effective N) with amber/red highlights for
     elevated risk.
  2. **Factor Exposures** — horizontal bar chart, positive bars blue, negative
     red, with a one-line interpretation per factor.
  3. **Stress Tests** — historical table sorted worst-first; below it, a
     macro-context textarea + "Generate adverse scenarios" button that calls
     `/llm/scenarios`, runs each shock through `/stress/hypothetical`, and
     renders a combined chart (blue = historical, purple = LLM-proposed).
  4. **Risk Briefing** — button that streams prose from `/llm/briefing` chunk
     by chunk with a pulsing cursor while it's coming in.
- Footer (every page): "Analytical tool only. Not investment advice. Risk
  models can fail in regime changes."

## Notes / known limits

- Default data is synthetic. Plug a real loader into `api/deps.py` →
  `init_context(my_loader)`.
- The synthetic series compounds five injected crisis windows over 18
  years, so headline metrics like Sharpe are deliberately negative — the
  smoke test verifies plumbing, not portfolio quality.
- Briefing streaming is plain `text/plain`. If you want SSE later you'd
  swap the `StreamingResponse` media type and add an `event:` framing.
