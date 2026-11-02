export default function SectorBars({ data }: { data: Record<string, number> }) {
  return (
    <div className="space-y-1">
      {Object.entries(data).map(([sector, pct]) => (
        <div key={sector} className="flex items-center gap-2 text-sm">
          <span className="w-28 shrink-0">{sector}</span>
          <div className="h-3 flex-1 rounded bg-gray-200">
            <div className="h-3 rounded bg-blue-600" style={{ width: `${Math.min(pct, 100)}%` }} />
          </div>
          <span className="w-12 text-right">{pct}%</span>
        </div>
      ))}
    </div>
  );
}
