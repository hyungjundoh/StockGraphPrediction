import type {
  FactorExposures,
  PortfolioSummary,
  ScenariosResponse,
  StressResults,
  Universe,
  Weights,
} from './types';

const BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
  }
  return (await resp.json()) as T;
}

export const api = {
  capabilities: () => call<{ llm_enabled: boolean }>('/capabilities'),

  universe: () => call<Universe>('/universe'),

  summary: (weights: Weights) =>
    call<PortfolioSummary>('/portfolio/summary', {
      method: 'POST',
      body: JSON.stringify({ weights }),
    }),

  exposures: (weights: Weights) =>
    call<FactorExposures>('/portfolio/exposures', {
      method: 'POST',
      body: JSON.stringify({ weights }),
    }),

  historical: (weights: Weights) =>
    call<StressResults>('/stress/historical', {
      method: 'POST',
      body: JSON.stringify({ weights }),
    }),

  hypothetical: (weights: Weights, shocks: Record<string, number>) =>
    call<{ impact: number }>('/stress/hypothetical', {
      method: 'POST',
      body: JSON.stringify({ weights, shocks }),
    }),

  scenarios: (macro_context: string, n_scenarios: number) =>
    call<ScenariosResponse>('/llm/scenarios', {
      method: 'POST',
      body: JSON.stringify({ macro_context, n_scenarios }),
    }),

  briefingStream: async (
    body: {
      summary: PortfolioSummary;
      exposures: FactorExposures;
      stress_results: StressResults;
      macro_context?: string;
    },
    onChunk: (chunk: string) => void,
  ): Promise<void> => {
    const resp = await fetch(`${BASE}/llm/briefing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok || !resp.body) {
      const text = await resp.text();
      throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      onChunk(decoder.decode(value, { stream: true }));
    }
  },
};
