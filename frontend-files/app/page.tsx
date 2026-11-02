"use client";
import { useEffect, useState } from "react";
import InsightCard from "@/components/InsightCard";
import SectorBars from "@/components/SectorBars";
import Link from "next/link";
import BenchmarkAnalysis from "@/components/BenchmarkAnalysis";
import { getPortfolios, runAnalysis, Job } from "@/lib/api";

export default function Home() {
  const [portfolios, setPortfolios] = useState<string[]>([]);
  const [selected, setSelected] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getPortfolios()
      .then((r) => {
        setPortfolios(r.portfolios);
        setSelected(r.portfolios[0] ?? "");
      })
      .catch(() => setError("Cannot reach the backend. Is it running on port 8000?"));
  }, []);

  async function analyse() {
    setLoading(true);
    setError("");
    setJob(null);
    try {
      setJob(await runAnalysis(selected));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold">Portfolio Intelligence</h1>
        <Link href="/operations" className="text-sm text-blue-700 underline">Operations dashboard</Link>
        <Link href="/compliance" className="ml-3 text-sm text-blue-700 underline">Compliance panel</Link>
        <p className="text-sm text-gray-600">
          Educational insights, not investment advice. LIVE shows your real Zerodha holdings; the other portfolios are samples.
        </p>
      </header>

      <div className="flex items-center gap-3">
        <select
          className="rounded border px-3 py-2"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {portfolios.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <button
          className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
          onClick={analyse}
          disabled={loading || !selected}
        >
          {loading ? "Analysing..." : "Analyse portfolio"}
        </button>
      </div>

      {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {job && (
        <>
          <section className="rounded-lg border p-4">
            <h2 className="mb-2 font-semibold">Sector exposure</h2>
            <SectorBars data={job.metrics.sector_pct} />
          </section>

          <section className="rounded-lg border p-4">
            <h2 className="mb-2 font-semibold">Holdings</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th>Symbol</th><th>Sector</th><th>Weight</th><th>P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {job.metrics.holdings.map((h) => (
                  <tr key={h.symbol} className="border-t">
                    <td>{h.symbol}</td><td>{h.sector}</td>
                    <td>{h.weight_pct}%</td>
                    <td className={h.pnl_pct >= 0 ? "text-green-700" : "text-red-700"}>{h.pnl_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="space-y-3">
            <h2 className="font-semibold">Insights</h2>
            <p className="text-xs text-gray-600">
              Prices in these insights come from the portfolio data itself: fixed sample prices for the sample portfolios, live Zerodha prices for LIVE. They can differ from the real market prices used in the benchmark analysis below.
            </p>
            {job.cards.map((c) => <InsightCard key={c.id} card={c} jobId={job.job_id} />)}
          </section>

          <section className="rounded-lg border p-4 text-xs text-gray-600">
            <b>Workflow:</b>{" "}
            {job.stages.map((s) => `${s.stage} (${s.ms}ms)`).join(" → ")}
          </section>
        </>
      )}

      <BenchmarkAnalysis portfolioId={selected} />
    </main>
  );
}
