# StockGraphPrediction

Two related workstreams live in this repo:

1. **Economic-indicator regression pipeline** *(original)* — scrape macro
   indicators and sector prices, format them into aligned panels, and fit
   regression / time-series / ML models to study how indicators move
   sector-wise stock prices. Mostly Python (scraping, formatting) + R
   (analysis).
2. **Portfolio risk dashboard** *(new)* — FastAPI backend + React/Vite
   dashboard built on top of a deterministic `risk/` package (VaR, CVaR,
   factor exposures, historical stress tests). Optional Claude-powered
   scenario generation and prose risk briefings, gated behind an opt-in
   `ENABLE_LLM` env flag.

The two pieces share the repo but not state — you can use either independently.

---

## Repo layout

```
analysis/             R analysis scripts (regression, stepwise, plots)
data/
  raw/                scraped CSVs, untouched
  processed/          aligned, joined panels
  formatted/          model-ready inputs
  stock_data/         per-ticker price files
drivers/              chromedriver binaries used by the scrapers
plots/                generated figures
scripts/
  scrap_data/         scrapers for individual indicators
  format_data/        cleaning / alignment passes
  refine_data/        post-processing
  plot/               plot-generation helpers
  stock_data/         price downloaders
  dev.sh / dev.bat    risk-dashboard dev launcher (LLM off by default)
tickers.txt           tickers consumed by stock_data scripts
main.py               entry point for the indicator pipeline
requirements.txt      Python deps for the indicator pipeline

risk/                 numerical risk module (no LLM, no I/O)
llm/                  Claude wrapper — only writes scenarios + briefings
api/                  FastAPI app exposing risk/ + llm/ as JSON
web/                  Vite + React + TS + Tailwind dashboard
portfolios/           personal portfolio convention (main.json gitignored)
main_risk.py          synthetic-data smoke test for the risk module
requirements-risk.txt Python deps for the risk dashboard
```

---

## Workstream 1 — Indicator regression pipeline

### What it does
Pulls economic indicators and sector closing prices, lines them up by date,
and fits regression / time-series models to estimate how indicator changes
propagate into sector returns.

### Indicators currently or partially integrated
CPI, GDP, Leading Index, Unemployment Rate, Interest Rate.

### Indicators on the to-do list
신규 실업수당청구건수 (New Jobless Claims) · S&P 글로벌 합성 PMI · 근원 PCE
가격지수 (Core PCE) · EIA 원유재고 · 신규주택판매 · 컨퍼런스보드 소비자
신뢰지수 · 미국 국채경매 · 기존주택판매 · PPI 상승률.

### Models in play
- **Multiple linear regression** — baseline; dependent var = sector close,
  independent vars = indicator panel.
- **Ridge / Lasso** — handle multicollinearity, do feature selection.
- **ARIMA / VAR** — capture temporal structure and cross-series dynamics.
- **Random Forest / Gradient Boosting** — non-linear interactions.
- **Stepwise regression** — `olsrr::ols_step_both_p` for automated
  significance-based selection.

### Install + run
```bash
pip install -r requirements.txt
python main.py            # see main.py for the run_* steps
```

The R analysis scripts live under `analysis/R/`. They expect the panels
written by `scripts/format_data/`.

### Known caveats
- **Confounders**: macro releases never explain everything — geopolitics,
  earnings, sentiment all leak into prices. Treat R² with appropriate
  skepticism.
- **Data quality**: alignment of release dates vs. trading days, holiday
  gaps, revisions to historical indicator series.
- **Look-ahead leakage**: only validate with time-respecting splits.
- **Overfitting**: the more flexible the model, the harder this bites —
  always compare against a stupid baseline.

---

## Workstream 2 — Portfolio risk dashboard

A local-only single-user analytical tool. The deterministic risk pipeline
(overview metrics, factor exposures, historical stress tests) always works.
LLM features (scenario generator, prose briefing) are opt-in: they only
appear when the backend is started with `ENABLE_LLM=true` and
`ANTHROPIC_API_KEY` set.

**Architectural rule:** the LLM never does math and never recommends trades.
All numbers (VaR, betas, drawdown, stress-test impacts) are computed in
`risk/`. The LLM only enumerates adverse scenarios as JSON shocks (which
`risk.stress.apply_shock` then evaluates) and writes prose summaries of
already-computed numbers. The system prompts in `llm/reports.py` encode
that, and the API just routes through.

### Architecture

```
   browser (web/, :5173)
        │
        ▼  fetch JSON
   FastAPI (api/, :8000)
        │
        ▼  function calls
   risk/  (numerics)        llm/  (Claude — scenarios + briefings only)
```

Single local user — no auth, no DB, no global state library.

### Setup (one-time)

#### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-risk.txt
pip install 'fastapi>=0.110' 'uvicorn[standard]>=0.29' 'pydantic>=2.5'

cd web && npm install && cd ..
```

#### Windows (cmd / PowerShell)
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

### Run

Both processes together:
```bash
# macOS / Linux
./scripts/dev.sh
# Windows
scripts\dev.bat
```

Or separately:
```bash
# terminal 1 — backend
uvicorn api.main:app --reload --port 8000

# terminal 2 — frontend
cd web && npm run dev
```

Then open http://localhost:5173.

### LLM opt-in

The LLM endpoints are off by default. The deterministic risk pipeline
always works; the scenario generator and risk briefing only appear when
the backend is started with `ENABLE_LLM=true` *and* `ANTHROPIC_API_KEY`
set. While disabled, `/llm/scenarios` and `/llm/briefing` return HTTP 404
and the frontend hides the corresponding UI. `GET /capabilities` reports
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

### Smoke test

```bash
python main_risk.py
# enable LLM scenarios + briefing:
ENABLE_LLM=true ANTHROPIC_API_KEY=sk-... python main_risk.py
```

`main_risk.py` builds 18 years of synthetic factor and sector returns, fits
the factor model, runs the stress tests against canonical historical windows
(GFC 2008, COVID 2020, Rate Hikes 2022, SVB 2023), and — if the LLM is
enabled — calls Claude for adverse scenarios and a prose briefing.

### Python API

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

### HTTP API

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

Validation: weights must sum to ~1.00 (tolerance 0.01) — otherwise 422.
Unknown sector or factor names → 400.

> Note: `/stress/historical` is POST (not GET) because the body is JSON;
> GET-with-body is not well supported by `fetch()` or many HTTP clients.
> The frontend uses POST throughout for body-bearing endpoints.

### curl examples

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

# LLM scenarios (requires ENABLE_LLM=true + ANTHROPIC_API_KEY)
curl -s -X POST http://localhost:8000/llm/scenarios \
  -H 'Content-Type: application/json' \
  -d '{"macro_context":"persistent inflation, hawkish Fed","n_scenarios":3}'

# Streamed briefing (requires ENABLE_LLM=true + ANTHROPIC_API_KEY)
curl -N -X POST http://localhost:8000/llm/briefing \
  -H 'Content-Type: application/json' \
  -d '{"summary":{"var_95":0.02,"max_drawdown":0.18,"sharpe":-0.4},
       "exposures":{"Equity":0.9,"Rates":-0.4},
       "stress_results":{"GFC_2008":-0.55,"COVID_2020":-0.27}}'
```

### UI layout

- Left sidebar: per-sector weight inputs, live sum indicator (red if not
  ~1.00), Normalize / Equal-weight buttons, Analyze button.
- Main area, four stacked sections:
  1. **Overview** — metric cards (annualized return, vol, VaR, CVaR, max
     drawdown, Sharpe, Sortino, effective N) with amber/red highlights for
     elevated risk.
  2. **Factor Exposures** — horizontal bar chart, positive bars blue,
     negative red, with a one-line interpretation per factor.
  3. **Stress Tests** — historical table sorted worst-first; below it (LLM
     only), a macro-context textarea + "Generate adverse scenarios" button
     that calls `/llm/scenarios`, runs each shock through
     `/stress/hypothetical`, and renders a combined chart (blue =
     historical, purple = LLM-proposed).
  4. **Risk Briefing** *(LLM only)* — button that streams prose from
     `/llm/briefing` chunk by chunk with a pulsing cursor.
- Footer: "Analytical tool only. Not investment advice. Risk models can
  fail in regime changes." When LLM is off, an extra line points at the
  `ENABLE_LLM` flag.

### Conventions

- Returns are `pd.Series` (or `pd.DataFrame` per asset/factor) of **simple**
  periodic returns.
- VaR / CVaR use loss convention: a -3% return becomes +0.03.
- Max drawdown is a positive magnitude (0.30 = 30% drawdown).
- Annualization uses 252 trading days unless overridden.
- `estimate_factor_exposures` does OLS via `np.linalg.pinv` on raw arrays —
  pandas matmul on misaligned or near-collinear data silently propagates
  NaN coefficients, so the linear algebra deliberately drops to numpy.

### Plugging in real data

Replace `_build_synthetic_data()` in `main_risk.py` with a loader that
returns `(factor_returns, sector_returns)` as DataFrames indexed by date,
where columns are factor / sector names and values are simple daily returns.
For the API/dashboard, swap the loader passed to `init_context()` in
`api/main.py` (or call `init_context(my_loader)` before app startup).
Everything downstream is data-shape agnostic.

### Notes / known limits

- Default data is synthetic. Plug a real loader into `api/deps.py` →
  `init_context(my_loader)`.
- The synthetic series compounds five injected crisis windows over 18
  years, so headline metrics like Sharpe are deliberately negative — the
  smoke test verifies plumbing, not portfolio quality.
- Briefing streaming is plain `text/plain`. If you want SSE later you'd
  swap the `StreamingResponse` media type and add an `event:` framing.

---

## Portfolios

`portfolios/` holds a small personal-portfolio convention used by the risk
dashboard:

- `example.json` — committed schema reference (sanitized).
- `main.json` — your live holdings. **Gitignored.** Never commit.
- `history/` — append-only timestamped snapshots. Gitignored.
- `snapshot.sh` / `diff.sh` — copy current state to history, diff against
  the latest snapshot.

```bash
./portfolios/snapshot.sh    # record after each rebalance
./portfolios/diff.sh        # see what changed since last snapshot
```

---

## License / scope

Single-user analytical / research code. Not investment advice. Risk models
fail in regime changes; regression coefficients drift; LLM-generated text
is not financial guidance.
