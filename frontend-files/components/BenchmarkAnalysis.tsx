"use client";
import { useEffect, useState } from "react";
import { API_URL as API } from "@/lib/api";

type Analysis = {
  kpis: Record<string, number | string>;
  graphs: Record<string, string>;
};

type Explain = {
  explanation: { summary: string; key_drivers: string[]; risk_note: string };
  provider: string;
};

const ROWS: [string, string, string][] = [
  ["One-year return (%)", "Portfolio return (%)", "Nifty 50 return (%)"],
  ["Volatility (% a year)", "Portfolio volatility (% a year)", "Nifty 50 volatility (% a year)"],
  ["Max drawdown (%)", "Portfolio max drawdown (%)", "Nifty 50 max drawdown (%)"],
];

async function readError(r: Response, fallback: string) {
  try {
    const body = await r.json();
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

export default function BenchmarkAnalysis({ portfolioId }: { portfolioId: string }) {
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [explain, setExplain] = useState<Explain | null>(null);
  const [explainFailed, setExplainFailed] = useState(false);

  useEffect(() => {
    if (!portfolioId) return;
    let cancelled = false;
    setData(null);
    setError("");
    setExplain(null);
    setExplainFailed(false);
    const id = encodeURIComponent(portfolioId);

    async function load() {
      try {
        const r = await fetch(`${API}/api/benchmark/${id}`);
        if (!r.ok) throw new Error(await readError(r, "Could not load benchmark analysis"));
        const d = await r.json();
        if (cancelled) return;
        setData(d);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Could not load benchmark analysis");
        }
        return;
      }
      try {
        const r = await fetch(`${API}/api/benchmark/${id}/explanation`);
        if (!r.ok) throw new Error("no explanation");
        const x = await r.json();
        if (!cancelled) setExplain(x);
      } catch {
        if (!cancelled) setExplainFailed(true);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [portfolioId]);

  if (!portfolioId) return null;

  if (error) {
    return (
      <section className="rounded-lg border p-4 text-sm text-gray-700">
        <h2 className="mb-1 font-semibold">Benchmark analysis: portfolio versus Nifty 50</h2>
        <p>{error}. Try one of the other portfolios in the list.</p>
      </section>
    );
  }
  if (!data) {
    return <p className="text-sm text-gray-600">Loading benchmark analysis...</p>;
  }

  const diff = Number(data.kpis["Return versus Nifty 50 (percentage points)"]);
  const gap = Math.abs(diff).toFixed(1);
  const side = diff < 0 ? "behind" : "ahead of";

  return (
    <section className="space-y-4 rounded-lg border p-4">
      <div>
        <h2 className="font-semibold">Benchmark analysis: portfolio versus Nifty 50</h2>
        <p className="text-xs text-gray-600">
          A one-year “what if I had held these quantities” view of the sample
          portfolio ({portfolioId}), using real market prices downloaded from Yahoo Finance.
          These can differ from the insights above, which use the prices stored with each
          portfolio. Educational only, not investment advice.
        </p>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500">
            <th>Measure</th>
            <th>Portfolio</th>
            <th>Nifty 50</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(([label, portfolioKey, niftyKey]) => (
            <tr key={label} className="border-t">
              <td>{label}</td>
              <td>{String(data.kpis[portfolioKey])}</td>
              <td>{String(data.kpis[niftyKey])}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="text-sm">
        Over the year, the portfolio finished <b>{gap}</b> percentage points {side} the Nifty 50.
      </p>

      {explain ? (
        <div className="space-y-2 rounded-lg bg-blue-50 p-4 text-sm">
          <p className="text-xs font-semibold uppercase text-gray-600">
            Educational insight (
            {explain.provider === "template" ? "standard summary" : "AI-written, numbers checked"})
          </p>
          <p>{explain.explanation.summary}</p>
          <ul className="list-disc space-y-1 pl-5">
            {explain.explanation.key_drivers.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
          <p className="text-gray-700">{explain.explanation.risk_note}</p>
        </div>
      ) : (
        <p className="text-xs text-gray-500">
          {explainFailed ? "The explanation could not be loaded." : "Loading explanation..."}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {Object.entries(data.graphs).map(([name, path]) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={name}
            src={`${API}${path}`}
            alt={name.replace(/_/g, " ")}
            className="w-full rounded border"
          />
        ))}
      </div>
    </section>
  );
}