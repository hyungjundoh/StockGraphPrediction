import { useState } from 'react';

import { api } from '../api';
import type { FactorExposures, PortfolioSummary, StressResults } from '../types';

interface Props {
  summary: PortfolioSummary | null;
  exposures: FactorExposures | null;
  historical: StressResults | null;
}

export default function RiskBriefing({ summary, exposures, historical }: Props) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ready = !!summary && !!exposures && !!historical;

  const generate = async () => {
    if (!summary || !exposures || !historical) return;
    setText('');
    setLoading(true);
    setError(null);
    try {
      await api.briefingStream(
        { summary, exposures, stress_results: historical },
        (chunk) => setText((t) => t + chunk),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Risk Briefing</h2>
      <div className="bg-white border rounded-md p-3 space-y-3">
        <div className="flex items-center gap-3">
          <button
            onClick={generate}
            disabled={!ready || loading}
            className="bg-slate-900 text-white text-sm rounded px-3 py-2 disabled:opacity-50 hover:bg-slate-800"
          >
            {loading ? 'Streaming briefing…' : 'Generate risk briefing'}
          </button>
          {!ready && (
            <span className="text-sm text-slate-500">
              Submit weights first to enable.
            </span>
          )}
          {loading && (
            <span className="text-sm text-slate-500 inline-flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              streaming from Claude…
            </span>
          )}
        </div>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 text-sm rounded p-2">
            {error}
          </div>
        )}
        {(text || loading) && (
          <div className="border-t pt-3 text-sm leading-relaxed whitespace-pre-wrap">
            {text}
            {loading && <span className="text-slate-400 animate-pulse">▍</span>}
          </div>
        )}
      </div>
    </section>
  );
}
