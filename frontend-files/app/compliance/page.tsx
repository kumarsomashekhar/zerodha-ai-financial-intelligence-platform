"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { API_URL as API } from "@/lib/api";

type Review = { decision: string; note: string; reviewer: string; at: string } | null;

type Flag = {
  job_id: string;
  portfolio_id: string;
  created_at: string;
  reasons: string[];
  review: Review;
};

type AuditRow = {
  job_id: string;
  portfolio_id: string;
  status: string;
  created_at: string;
  provider: string | null;
  prompt_version: string | null;
  validation_status: string | null;
  has_snapshot: boolean;
  review: Review;
};

type Summary = {
  disclosures: string[];
  counts: { analyses_audited: number; flagged: number; awaiting_review: number; reviewed: number };
  flags: Flag[];
  data_flags: string[];
  audit_trail: AuditRow[];
};

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}

function reviewLabel(r: Review) {
  if (!r) return "awaiting review";
  return r.decision === "approved" ? "approved" : "needs follow-up";
}

function FlagCard({
  flag,
  reviewer,
  reviewKey,
  onSaved,
}: {
  flag: Flag;
  reviewer: string;
  reviewKey: string;
  onSaved: () => void;
}) {
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  async function submit(decision: "approved" | "needs_follow_up") {
    setSaving(true);
    setErr("");
    try {
      const r = await fetch(`${API}/api/compliance/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-review-key": reviewKey },
        body: JSON.stringify({ job_id: flag.job_id, decision, note, reviewer }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : "The review could not be saved");
      }
      setNote("");
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="space-y-2 rounded bg-amber-50 p-3 text-sm">
      <div className="flex flex-wrap justify-between gap-2">
        <b>{flag.portfolio_id}</b>
        <span className="text-xs text-gray-500">
          {new Date(flag.created_at).toLocaleString()} | ref {flag.job_id}
        </span>
      </div>
      <ul className="list-disc pl-5">
        {flag.reasons.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
      {flag.review && (
        <p className="rounded bg-white p-2">
          <b>{reviewLabel(flag.review)}</b> by {flag.review.reviewer} on{" "}
          {new Date(flag.review.at).toLocaleString()}
          {flag.review.note ? `: ${flag.review.note}` : ""}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <input
          className="min-w-48 flex-1 rounded border px-2 py-1"
          placeholder="Optional note"
          value={note}
          maxLength={500}
          onChange={(e) => setNote(e.target.value)}
        />
        <button
          className="rounded bg-green-700 px-3 py-1 text-white disabled:opacity-50"
          disabled={saving}
          onClick={() => submit("approved")}
        >
          Approve
        </button>
        <button
          className="rounded bg-amber-700 px-3 py-1 text-white disabled:opacity-50"
          disabled={saving}
          onClick={() => submit("needs_follow_up")}
        >
          Needs follow-up
        </button>
      </div>
      {err && <p className="text-red-700">{err}</p>}
    </li>
  );
}

export default function Compliance() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [reviewer, setReviewer] = useState("reviewer");
  const [reviewKey, setReviewKey] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/api/compliance/summary`);
      if (!r.ok) throw new Error("The backend could not produce the compliance summary");
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
          <h1 className="text-2xl font-bold">Compliance panel</h1>
          <p className="text-sm text-gray-600">
            Disclosures, audit trail, policy flags and reviewer decisions.
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
          <section className="rounded-lg border bg-blue-50 p-4">
            <h2 className="mb-2 font-semibold">Disclosures</h2>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {data.disclosures.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          </section>

          <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Analyses audited" value={data.counts.analyses_audited} />
            <Stat label="Flagged" value={data.counts.flagged} />
            <Stat label="Awaiting review" value={data.counts.awaiting_review} />
            <Stat label="Reviewed" value={data.counts.reviewed} />
          </section>

          <section className="rounded-lg border p-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">Policy flags ({data.flags.length})</h2>
              <label className="text-sm">
                Reviewer name:{" "}
                <input
                  className="rounded border px-2 py-1"
                  value={reviewer}
                  maxLength={60}
                  onChange={(e) => setReviewer(e.target.value)}
                />
              </label>
              <label className="text-sm">
                Reviewer key:{" "}
                <input
                  type="password"
                  className="rounded border px-2 py-1"
                  value={reviewKey}
                  maxLength={100}
                  onChange={(e) => setReviewKey(e.target.value)}
                />
              </label>
            </div>
            {data.flags.length === 0 ? (
              <p className="text-sm text-gray-500">No flagged analyses.</p>
            ) : (
              <ul className="space-y-3">
                {data.flags.map((f) => (
                  <FlagCard key={f.job_id} flag={f} reviewer={reviewer} reviewKey={reviewKey} onSaved={load} />
                ))}
              </ul>
            )}
            {data.data_flags.length > 0 && (
              <div className="mt-4 text-sm">
                <h3 className="mb-1 font-medium">Data-quality flags</h3>
                <ul className="list-disc pl-5">
                  {data.data_flags.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          <section className="rounded-lg border p-4">
            <h2 className="mb-2 font-semibold">Audit trail</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm [&_td]:py-1 [&_td]:pr-4 [&_th]:pr-4">
                <thead>
                  <tr className="text-left text-gray-500">
                    <th>When</th><th>Portfolio</th><th>Status</th><th>Answer by</th>
                    <th>Prompt</th><th>Check</th><th>Data</th><th>Review</th>
                  </tr>
                </thead>
                <tbody>
                  {data.audit_trail.map((r) => (
                    <tr key={r.job_id} className="border-t">
                      <td>{new Date(r.created_at).toLocaleString()}</td>
                      <td>{r.portfolio_id}</td>
                      <td className={r.status === "failed" ? "text-red-700" : ""}>{r.status}</td>
                      <td>{r.provider ?? "-"}</td>
                      <td>{r.prompt_version ?? "-"}</td>
                      <td>{r.validation_status ?? "-"}</td>
                      <td>
                        {r.has_snapshot ? (
                          <a
                            className="text-blue-700 underline"
                            href={`${API}/api/snapshot/${r.job_id}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            snapshot
                          </a>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td>{r.review ? reviewLabel(r.review) : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </main>
  );
}