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
   `ENABLE_LLM` env flag. See **[README-RISK.md](./README-RISK.md)** for
   full details.

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
README-RISK.md        full docs for the risk dashboard
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

## Workstream 2 — Risk dashboard

A local-only single-user analytical tool. The deterministic risk pipeline
(overview metrics, factor exposures, historical stress tests) always works.
LLM features (scenario generator, prose briefing) are **opt-in**: they only
appear when the backend is started with `ENABLE_LLM=true` and
`ANTHROPIC_API_KEY` set.

```bash
pip install -r requirements-risk.txt
cd web && npm install && cd ..

# numeric-only mode (default)
./scripts/dev.sh

# with LLM features on
ENABLE_LLM=true ANTHROPIC_API_KEY=sk-... ./scripts/dev.sh
```

`/capabilities` reports `{llm_enabled: bool}` so the frontend can hide LLM
UI when disabled. `/llm/*` endpoints return 404 (not 503) when off.

Full docs, API surface, curl examples, and architecture notes:
**[README-RISK.md](./README-RISK.md)**.

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
