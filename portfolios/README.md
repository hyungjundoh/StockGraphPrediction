# Portfolios

Personal portfolio data. Files matching `*.json` are gitignored except `example.json`.

## Files
- `example.json` — committed schema reference.
- `main.json` — your live portfolio. Gitignored.
- `history/` — append-only snapshots. Gitignored.
- `snapshot.sh` — copy main.json to a timestamped history file.
- `diff.sh` — compare current main.json against the latest snapshot.

## Workflow
1. Edit `main.json` when you trade or rebalance.
2. Run `./portfolios/snapshot.sh` to record the new state.
3. Run `./portfolios/diff.sh` later to see what changed since last snapshot.

## Privacy
Never share `main.json`, screenshots of holdings, or absolute KRW/USD totals in
public channels. Use `example.json` or normalized weights when demoing.
