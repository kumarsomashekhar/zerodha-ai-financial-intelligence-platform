"use client";
import { useState } from "react";
import { Card, sendFeedback } from "@/lib/api";

const STYLES: Record<Card["category"], string> = {
  educational_insight: "border-blue-300 bg-blue-50",
  risk_alert: "border-amber-400 bg-amber-50",
  review_prompt: "border-gray-300 bg-gray-50",
};

const LABELS: Record<Card["category"], string> = {
  educational_insight: "Educational insight",
  risk_alert: "Risk alert",
  review_prompt: "Review prompt",
};

export default function InsightCard({ card, jobId }: { card: Card; jobId: string }) {
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);

  async function rate(helpful: boolean) {
    await sendFeedback(jobId, card.id, helpful);
    setSent(true);
  }

  return (
    <div className={`rounded-lg border p-4 ${STYLES[card.category]}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide">{LABELS[card.category]}</span>
        <span className="text-xs">
          Confidence: {card.confidence}
          {card.freshness.stale && <b className="ml-2 text-red-600">Stale data ({card.freshness.age_days}d)</b>}
        </span>
      </div>
      <h3 className="mt-1 text-lg font-semibold">{card.title}</h3>
      <p className="mt-1 text-sm">{card.rationale}</p>

      <button className="mt-2 text-sm underline" onClick={() => setOpen(!open)}>
        {open ? "Hide details" : "Show details"}
      </button>
      {open && (
        <div className="mt-2 space-y-2 text-sm">
          <ul className="list-disc pl-5">
            {card.details.map((d, i) => <li key={i}>{d}</li>)}
          </ul>
          <pre className="rounded bg-white/70 p-2 text-xs">{JSON.stringify(card.metrics, null, 2)}</pre>
          <p className="text-xs italic">{card.disclaimer}</p>
        </div>
      )}

      <div className="mt-3 text-xs">
        {sent ? "Thanks for the feedback." : (
          <>
            Was this useful?{" "}
            <button className="underline" onClick={() => rate(true)}>Yes</button>{" / "}
            <button className="underline" onClick={() => rate(false)}>No</button>
          </>
        )}
      </div>
    </div>
  );
}
