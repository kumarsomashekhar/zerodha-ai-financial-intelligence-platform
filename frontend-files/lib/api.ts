export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Card = {
  id: string;
  category: "educational_insight" | "risk_alert" | "review_prompt";
  title: string;
  rationale: string;
  details: string[];
  metrics: Record<string, number | string>;
  freshness: { age_days: number; stale: boolean };
  confidence: "low" | "medium" | "high";
  disclaimer: string;
};

export type Job = {
  job_id: string;
  status: string;
  stages: { stage: string; ms: number }[];
  metrics: {
    holdings_count: number;
    total_pnl_pct: number;
    sector_pct: Record<string, number>;
    top_holding: { symbol: string; weight_pct: number };
    data_age_days: number;
    holdings: { symbol: string; sector: string; weight_pct: number; pnl_pct: number }[];
  };
  cards: Card[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export const getPortfolios = () => request<{ portfolios: string[] }>("/api/portfolios");

export const runAnalysis = (portfolio_id: string) =>
  request<Job>("/api/portfolio-analysis", {
    method: "POST",
    body: JSON.stringify({ portfolio_id }),
  });

export const sendFeedback = (job_id: string, card_id: string, helpful: boolean) =>
  request<{ saved: boolean }>("/api/feedback", {
    method: "POST",
    body: JSON.stringify({ job_id, card_id, helpful }),
  });
