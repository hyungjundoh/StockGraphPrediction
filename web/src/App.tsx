import { useEffect, useState } from 'react';

import { api } from './api';
import FactorExposuresView from './components/FactorExposures';
import Footer from './components/Footer';
import Overview from './components/Overview';
import RiskBriefing from './components/RiskBriefing';
import Sidebar from './components/Sidebar';
import StressTests from './components/StressTests';
import type {
  FactorExposures,
  PortfolioSummary,
  StressResults,
  Universe,
  Weights,
} from './types';

export default function App() {
  const [universe, setUniverse] = useState<Universe | null>(null);
  const [universeError, setUniverseError] = useState<string | null>(null);
  const [weights, setWeights] = useState<Weights>({});
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [exposures, setExposures] = useState<FactorExposures | null>(null);
  const [historical, setHistorical] = useState<StressResults | null>(null);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [llmEnabled, setLlmEnabled] = useState(false);

  useEffect(() => {
    api
      .universe()
      .then((u) => {
        setUniverse(u);
        const each = +(1 / u.sectors.length).toFixed(4);
        const w: Weights = {};
        u.sectors.forEach((s) => {
          w[s] = each;
        });
        setWeights(w);
      })
      .catch((e) => setUniverseError(e instanceof Error ? e.message : String(e)));
    api
      .capabilities()
      .then((c) => setLlmEnabled(c.llm_enabled))
      .catch(() => setLlmEnabled(false));
  }, []);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const [s, e, h] = await Promise.all([
        api.summary(weights),
        api.exposures(weights),
        api.historical(weights),
      ]);
      setSummary(s);
      setExposures(e);
      setHistorical(h);
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : String(err));
    } finally {
      setAnalyzing(false);
    }
  };

  if (universeError) {
    return (
      <div className="p-8 text-red-700">
        <p className="font-semibold">Backend unreachable.</p>
        <p className="text-sm mt-1">{universeError}</p>
        <p className="text-sm mt-3 text-slate-600">
          Start the API with <code>uvicorn api.main:app --port 8000</code>.
        </p>
      </div>
    );
  }

  if (!universe) {
    return <div className="p-8 text-slate-500">Loading universe…</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <div className="flex flex-1 min-h-0">
        <Sidebar
          sectors={universe.sectors}
          weights={weights}
          setWeights={setWeights}
          onSubmit={handleAnalyze}
          analyzing={analyzing}
        />
        <main className="flex-1 p-6 space-y-6 overflow-auto">
          <header>
            <h1 className="text-2xl font-semibold">Risk Dashboard</h1>
            <p className="text-sm text-slate-500">
              Synthetic data — local single-user analytical tool. All math runs in <code>risk/</code>;
              the LLM only writes scenarios and briefings.
            </p>
          </header>
          {analyzeError && (
            <div className="bg-red-50 border border-red-200 text-red-800 p-3 rounded">
              {analyzeError}
            </div>
          )}
          <Overview summary={summary} />
          <FactorExposuresView exposures={exposures} />
          <StressTests weights={weights} historical={historical} llmEnabled={llmEnabled} />
          {llmEnabled && (
            <RiskBriefing summary={summary} exposures={exposures} historical={historical} />
          )}
        </main>
      </div>
      <Footer llmEnabled={llmEnabled} />
    </div>
  );
}
