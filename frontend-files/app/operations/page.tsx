"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { API_URL as API } from "@/lib/api";

type Summary = {
  job_health: {
    total_jobs: number;
    by_status: Record<string, number>;
    avg_stage_ms: Record<string, number>;
  };
  adoption: { jobs_by_portfolio: Record<string, number>; feedback_count: number };
  output_quality: {
    ai_provider_mix: Record<string, number>;
    validation: Record<string, number>;
    validation_pass_rate_pct: number | null;
    helpful_rate_pct: number | null;
  };
  exceptions: { type: string; ref: string; detail: string }[];
  recent_jobs: {
    job_id: string;
    portfolio_id: string;
    status: string;
    created_at: string;
    provider: string | null;
    validation_status: string | null;
    total_ms: number;
  }[];
  latest_quality_run: {
    run_at: string;
    runs_saved: number;
    metrics: Record<string, number>;
  } | null;
};

const EXCEPTION_LABELS: Record<string, string> = {
  failed_job: "Failed job",
  ai_output_rejected: "AI answer rejected (safe fallback used)",
  data_quality_flag: "Data quality flag",
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}

function Pairs({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return <p className="text-sm text-gray-500">Nothing yet</p>;
  return (
    <ul className="space-y-1 text-sm">
      {entries.map(([k, v]) => (
        <li key={k} className="flex justify-between border-b py-1">
          <span>{k.replace(/_/g, " ")}</span>
          <b>{v}</b>
        </li>
      ))}
    </ul>
  );
}

export default function Operations() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/api/ops/summary`);
      if (!r.ok) throw new Error("The backend could not produce the summary");
      setData(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach the backend. Is it running on port 8000?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Operations dashboard</h1>
          <p className="text-sm text-gray-600">
            Job health, adoption, output quality and open exceptions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/" className="text-sm text-blue-700 underline">Back to portfolios</Link>
          <button
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
            onClick={load}
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {!data && !error && <p className="text-sm text-gray-600">Loading...</p>}

      {data && (
        <>
          <section className="rounded-lg border p-4">
            <h2 className="mb-3 font-semibold">Job health</h2>
            <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label="Total jobs" value={data.job_health.total_jobs} />
              <Stat label="Completed" value={data.job_health.by_status.completed ?? 0} />
              <Stat label="Failed" value={data.job_health.by_status.failed ?? 0} />
              <Stat label="Feedback clicks" value={data.adoption.feedback_count} />
            </div>
            <h3 className="mb-1 text-sm font-medium">Average time per stage (ms)</h3>
            <Pairs data={data.job_health.avg_stage_ms} />
          </section>

          <section className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border p-4">
              <h2 className="mb-2 font-semibold">Adoption: jobs by portfolio</h2>
              <Pairs data={data.adoption.jobs_by_portfolio} />
            </div>
            <div className="rounded-lg border p-4">
              <h2 className="mb-2 font-semibold">Output quality</h2>
              <div className="mb-2 grid grid-cols-2 gap-3">
                <Stat
                  label="Passed validation"
                  value={data.output_quality.validation_pass_rate_pct === null ? "n/a" : `${data.output_quality.validation_pass_rate_pct}%`}
                />
                <Stat
                  label="Marked helpful"
                  value={data.output_quality.helpful_rate_pct === null ? "n/a" : `${data.output_quality.helpful_rate_pct}%`}
                />
              </div>
              <h3 className="mb-1 text-sm font-medium">Who wrote the answers</h3>
              <Pairs data={data.output_quality.ai_provider_mix} />
            </div>
          </section>

          <section className="rounded-lg border p-4">
            <h2 className="mb-2 font-semibold">Unresolved exceptions ({data.exceptions.length})</h2>
            {data.exceptions.length === 0 ? (
              <p className="text-sm text-gray-500">No open exceptions.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {data.exceptions.map((x, i) => (
                  <li key={i} className="rounded bg-amber-50 p-2">
                    <b>{EXCEPTION_LABELS[x.type] ?? x.type}</b>
                    <div>{x.detail}</div>
                    <div className="text-xs text-gray-500">ref: {x.ref}</div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border p-4">
            <h2 className="mb-2 font-semibold">Recent jobs</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm [&_td]:py-1 [&_td]:pr-4 [&_th]:pr-4">
                <thead>
                  <tr className="text-left text-gray-500">
                    <th>When</th><th>Portfolio</th><th>Status</th><th>Answer by</th><th>Check</th><th>Total ms</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_jobs.map((j) => (
                    <tr key={j.job_id} className="border-t">
                      <td>{new Date(j.created_at).toLocaleString()}</td>
                      <td>{j.portfolio_id}</td>
                      <td className={j.status === "failed" ? "text-red-700" : ""}>{j.status}</td>
                      <td>{j.provider ?? "-"}</td>
                      <td>{j.validation_status ?? "-"}</td>
                      <td>{j.total_ms}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {data.latest_quality_run && (
            <section className="rounded-lg border p-4 text-sm">
              <h2 className="mb-2 font-semibold">Latest data-quality run</h2>
              <p className="mb-2 text-gray-600">
                {new Date(data.latest_quality_run.run_at).toLocaleString()} ({data.latest_quality_run.runs_saved} runs saved)
              </p>
              <Pairs data={data.latest_quality_run.metrics} />
            </section>
          )}
        </>
      )}
    </main>
  );
}