import type { Weights } from '../types';

interface Props {
  sectors: string[];
  weights: Weights;
  setWeights: (w: Weights) => void;
  onSubmit: () => void;
  analyzing: boolean;
}

export default function Sidebar({ sectors, weights, setWeights, onSubmit, analyzing }: Props) {
  const sum = Object.values(weights).reduce((a, b) => a + (b || 0), 0);
  const ok = Math.abs(sum - 1) < 0.01;

  const update = (s: string, v: number) => {
    setWeights({ ...weights, [s]: v });
  };

  const normalize = () => {
    if (sum === 0) return;
    const next: Weights = {};
    sectors.forEach((s) => {
      next[s] = +((weights[s] || 0) / sum).toFixed(4);
    });
    setWeights(next);
  };

  const equalize = () => {
    const each = +(1 / sectors.length).toFixed(4);
    const next: Weights = {};
    sectors.forEach((s) => {
      next[s] = each;
    });
    setWeights(next);
  };

  return (
    <aside className="w-72 border-r bg-white p-4 space-y-4 shrink-0">
      <div>
        <h2 className="font-semibold text-sm">Portfolio Weights</h2>
        <p className="text-xs text-slate-500">
          Decimal weights per sector. Must sum to ~1.00.
        </p>
      </div>

      <div className="space-y-2">
        {sectors.map((s) => (
          <div key={s} className="flex items-center justify-between gap-2">
            <label className="text-sm">{s}</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              className="w-24 border rounded px-2 py-1 text-right text-sm font-mono"
              value={weights[s] ?? 0}
              onChange={(e) => update(s, parseFloat(e.target.value) || 0)}
            />
          </div>
        ))}
      </div>

      <div
        className={`text-sm font-medium ${ok ? 'text-emerald-700' : 'text-red-600'}`}
      >
        Sum: {sum.toFixed(4)} {ok ? '✓' : '(must be ~1.00)'}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={normalize}
          className="bg-slate-100 hover:bg-slate-200 text-xs rounded py-2 border"
        >
          Normalize
        </button>
        <button
          onClick={equalize}
          className="bg-slate-100 hover:bg-slate-200 text-xs rounded py-2 border"
        >
          Equal weights
        </button>
      </div>

      <button
        onClick={onSubmit}
        disabled={!ok || analyzing}
        className="w-full bg-slate-900 text-white text-sm rounded py-2 disabled:opacity-50 hover:bg-slate-800"
      >
        {analyzing ? 'Analyzing…' : 'Analyze Portfolio'}
      </button>
    </aside>
  );
}
