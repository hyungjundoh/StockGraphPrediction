import type { PortfolioSummary } from '../types';
import MetricCard from './MetricCard';

const fmtPct = (x: number | undefined | null, digits = 2) =>
  x === undefined || x === null || Number.isNaN(x) ? '—' : `${(x * 100).toFixed(digits)}%`;
const fmtNum = (x: number | undefined | null, digits = 2) =>
  x === undefined || x === null || Number.isNaN(x) ? '—' : x.toFixed(digits);

type Tone = 'normal' | 'amber' | 'red';

export default function Overview({ summary }: { summary: PortfolioSummary | null }) {
  if (!summary) {
    return (
      <section>
        <h2 className="text-lg font-semibold mb-2">Overview</h2>
        <p className="text-sm text-slate-500">
          Enter weights and click <span className="font-medium">Analyze Portfolio</span> to compute metrics.
        </p>
      </section>
    );
  }

  const annRet = (summary.mean_return ?? 0) * 252;

  const varTone: Tone =
    summary.var_95 > 0.05 ? 'red' : summary.var_95 > 0.03 ? 'amber' : 'normal';
  const cvarTone: Tone =
    summary.cvar_95 > 0.07 ? 'red' : summary.cvar_95 > 0.04 ? 'amber' : 'normal';
  const ddTone: Tone =
    summary.max_drawdown > 0.3 ? 'red' : summary.max_drawdown > 0.2 ? 'amber' : 'normal';
  const sharpeTone: Tone =
    summary.sharpe < 0 ? 'red' : summary.sharpe < 0.5 ? 'amber' : 'normal';
  const annRetTone: Tone = annRet < 0 ? 'amber' : 'normal';

  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Annualized return" value={fmtPct(annRet)} tone={annRetTone} />
        <MetricCard label="Annualized vol" value={fmtPct(summary.vol_annualized)} />
        <MetricCard label="VaR 95%" value={fmtPct(summary.var_95)} tone={varTone} hint="1-day, historical" />
        <MetricCard label="CVaR 95%" value={fmtPct(summary.cvar_95)} tone={cvarTone} />
        <MetricCard label="Max drawdown" value={fmtPct(summary.max_drawdown)} tone={ddTone} />
        <MetricCard label="Sharpe" value={fmtNum(summary.sharpe)} tone={sharpeTone} />
        <MetricCard label="Sortino" value={fmtNum(summary.sortino)} />
        <MetricCard
          label="Effective N"
          value={fmtNum(summary.effective_n)}
          hint={summary.n_assets ? `of ${summary.n_assets} sectors` : undefined}
        />
      </div>
    </section>
  );
}
