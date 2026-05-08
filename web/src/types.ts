export interface Universe {
  sectors: string[];
  factors: string[];
}

export type Weights = Record<string, number>;

export interface PortfolioSummary {
  n_obs: number;
  mean_return: number;
  vol_annualized: number;
  ewma_vol_annualized: number;
  var_95: number;
  cvar_95: number;
  max_drawdown: number;
  sharpe: number;
  sortino: number;
  calmar: number;
  effective_n?: number;
  n_assets?: number;
  max_weight?: number;
  [key: string]: number | undefined;
}

export type FactorExposures = Record<string, number>;
export type StressResults = Record<string, number>;

export interface Scenario {
  name: string;
  narrative: string;
  horizon_days: number;
  shocks: Record<string, number>;
}

export interface ScenariosResponse {
  scenarios: Scenario[];
}
