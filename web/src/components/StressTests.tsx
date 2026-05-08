import { useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { api } from '../api';
import type { Scenario, StressResults, Weights } from '../types';

interface Props {
  weights: Weights;
  historical: StressResults | null;
  llmEnabled: boolean;
}

interface ScenarioImpact {
  name: string;
  impact: number;
  narrative: string;
}

export default function StressTests({ weights, historical, llmEnabled }: Props) {
  const [macroContext, setMacroContext] = useState(
    'US large-cap, late-cycle, persistent inflation, hawkish Fed, geopolitical tail risks.',
  );
  const [scenarios, setScenarios] = useState<ScenarioImpact[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runScenarios = async () => {
    setLoading(true);
    setError(null);
    try {
      const sc = await api.scenarios(macroContext, 3);
      const list: Scenario[] = sc.scenarios || [];
      const results = await Promise.all(
        list.map(async (s) => {
          const r = await api.hypothetical(weights, s.shocks);
          return { name: s.name, impact: r.impact, narrative: s.narrative };
        }),
      );
      setScenarios(results);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const histRows = historical
    ? Object.entries(historical).sort((a, b) => (a[1] || 0) - (b[1] || 0))
    : [];

  const combined = [
    ...(historical
      ? Object.entries(historical).map(([name, impact]) => ({
          name,
          impact,
          kind: 'historical' as const,
        }))
      : []),
    ...scenarios.map((s) => ({ name: s.name, impact: s.impact, kind: 'hypothetical' as const })),
  ];

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Stress Tests</h2>

      {!historical ? (
        <p className="text-sm text-slate-500">Submit weights to compute historical stress tests.</p>
      ) : (
        <div className="bg-white border rounded-md p-3">
          <h3 className="font-medium text-sm mb-2">Historical scenarios (worst first)</h3>
          <table className="text-sm w-full">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-1 font-medium">Scenario</th>
                <th className="py-1 font-medium text-right">Estimated impact</th>
              </tr>
            </thead>
            <tbody>
              {histRows.map(([name, impact]) => (
                <tr key={name} className="border-b last:border-b-0">
                  <td className="py-1.5">{name}</td>
                  <td
                    className={`py-1.5 text-right font-mono ${
                      impact < 0 ? 'text-red-700' : 'text-emerald-700'
                    }`}
                  >
                    {(impact * 100).toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {llmEnabled && (
        <div className="bg-white border rounded-md p-3 space-y-2">
          <h3 className="font-medium text-sm">Generate adverse scenarios (LLM)</h3>
          <p className="text-xs text-slate-500">
            Claude proposes adverse but plausible factor shocks as JSON; the backend then evaluates
            each one against your portfolio. The LLM never recommends trades.
          </p>
          <textarea
            className="w-full border rounded px-2 py-1 text-sm"
            rows={3}
            value={macroContext}
            onChange={(e) => setMacroContext(e.target.value)}
          />
          <button
            onClick={runScenarios}
            disabled={loading}
            className="bg-slate-900 text-white text-sm rounded px-3 py-2 disabled:opacity-50 hover:bg-slate-800"
          >
            {loading ? 'Generating…' : 'Generate adverse scenarios'}
          </button>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 text-sm rounded p-2">
              {error}
            </div>
          )}
          {scenarios.length > 0 && (
            <ul className="text-sm space-y-1 mt-2">
              {scenarios.map((s) => (
                <li key={s.name} className="border rounded p-2 bg-slate-50">
                  <div className="flex justify-between gap-2">
                    <span className="font-medium">{s.name}</span>
                    <span
                      className={`font-mono ${
                        s.impact < 0 ? 'text-red-700' : 'text-emerald-700'
                      }`}
                    >
                      {(s.impact * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 mt-1">{s.narrative}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {llmEnabled && combined.length > 0 && (
        <div className="bg-white border rounded-md p-3">
          <h3 className="font-medium text-sm mb-2">Combined stress impacts</h3>
          <div style={{ height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={combined} margin={{ bottom: 60, left: 10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  angle={-30}
                  textAnchor="end"
                  interval={0}
                  height={70}
                  tick={{ fontSize: 12 }}
                />
                <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                <Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} />
                <Bar dataKey="impact">
                  {combined.map((d, i) => (
                    <Cell key={i} fill={d.kind === 'historical' ? '#0ea5e9' : '#a855f7'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Blue = historical · Purple = LLM-proposed
          </p>
        </div>
      )}
    </section>
  );
}
