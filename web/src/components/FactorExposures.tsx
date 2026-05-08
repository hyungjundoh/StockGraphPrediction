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

import type { FactorExposures } from '../types';

const interp = (factor: string, beta: number): string => {
  if (Math.abs(beta) < 0.05) {
    return `Roughly neutral on ${factor} (beta ${beta.toFixed(2)}).`;
  }
  if (beta >= 0) {
    return `Positive on ${factor}: portfolio gains when ${factor} rises (beta ${beta.toFixed(2)}).`;
  }
  return `Negative on ${factor}: portfolio loses when ${factor} rises (beta ${beta.toFixed(2)}).`;
};

export default function FactorExposuresView({
  exposures,
}: {
  exposures: FactorExposures | null;
}) {
  if (!exposures) {
    return (
      <section>
        <h2 className="text-lg font-semibold mb-2">Factor Exposures</h2>
        <p className="text-sm text-slate-500">Submit weights to compute factor exposures.</p>
      </section>
    );
  }

  const data = Object.entries(exposures).map(([factor, beta]) => ({ factor, beta }));

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Factor Exposures</h2>
      <div className="bg-white border rounded-md p-3">
        <div style={{ height: 220 }}>
          <ResponsiveContainer>
            <BarChart data={data} layout="vertical" margin={{ left: 30, right: 30, top: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={(v) => v.toFixed(2)} />
              <YAxis dataKey="factor" type="category" width={80} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Bar dataKey="beta">
                {data.map((d, i) => (
                  <Cell key={i} fill={d.beta >= 0 ? '#0ea5e9' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <ul className="text-sm space-y-1 mt-3">
          {data.map((d) => (
            <li key={d.factor} className="text-slate-700">
              {interp(d.factor, d.beta)}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
