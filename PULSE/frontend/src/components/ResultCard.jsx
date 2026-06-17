const SEV = {
  CRITICAL: { ring: 'ring-red-500', bg: 'bg-red-950', txt: 'text-red-400', badge: 'bg-red-900 text-red-300' },
  HIGH: { ring: 'ring-orange-500', bg: 'bg-orange-950', txt: 'text-orange-400', badge: 'bg-orange-900 text-orange-300' },
  MEDIUM: { ring: 'ring-yellow-500', bg: 'bg-yellow-950', txt: 'text-yellow-400', badge: 'bg-yellow-900 text-yellow-300' },
  LOW: { ring: 'ring-green-500', bg: 'bg-green-950', txt: 'text-green-400', badge: 'bg-green-900 text-green-300' },
}

const ScoreRing = ({ value, color }) => {
  const r = 36, circ = 2 * Math.PI * r
  const offset = circ - (value / 100) * circ
  return (
    <svg width="100" height="100" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={r} fill="none" stroke="#374151" strokeWidth="8" />
      <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round" transform="rotate(-90 50 50)"
        style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
      <text x="50" y="50" textAnchor="middle" dominantBaseline="central"
        fontSize="20" fontWeight="bold" fill="white">{value}</text>
    </svg>
  )
}

const RING_COLORS = { CRITICAL: '#ef4444', HIGH: '#f97316', MEDIUM: '#eab308', LOW: '#22c55e' }

export default function ResultCard({ result }) {
  const s = SEV[result.severity] || SEV.LOW
  const ringColor = RING_COLORS[result.severity] || '#22c55e'

  return (
    <div className={`rounded-xl border-2 ring-2 ${s.ring} ${s.bg} p-6`}>
      {/* Header row */}
      <div className="flex justify-between items-start mb-5">
        <div>
          <p className="text-gray-400 text-xs font-semibold uppercase tracking-wide">Severity</p>
          <p className={`text-3xl font-bold ${s.txt} mt-1`}>{result.severity}</p>
          <span className={`inline-block text-xs px-2.5 py-0.5 rounded-full mt-2 font-medium ${s.badge}`}>
            Respond within {result.response_sla_mins} min
          </span>
        </div>
        <div className="flex flex-col items-center">
          <ScoreRing value={result.impact_score} color={ringColor} />
          <p className="text-gray-400 text-xs mt-1">Impact Score</p>
        </div>
      </div>

      {/* 4 metric grid */}
      <div className="bg-black bg-opacity-30 rounded-lg p-3">
        <p className="text-gray-500 text-xs">Closure Risk</p>

        <p className="text-white font-bold text-base mt-1">
          {result.road_closure_probability}%
        </p>

        <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
          <div
            className={`h-2 rounded-full ${result.road_closure_probability > 70
                ? "bg-red-500"
                : result.road_closure_probability > 40
                  ? "bg-yellow-500"
                  : "bg-green-500"
              }`}
            style={{
              width: `${result.road_closure_probability}%`
            }}
          />
        </div>

        <p className={`text-xs mt-2 ${result.road_closure_probability > 70
            ? "text-red-400"
            : result.road_closure_probability > 40
              ? "text-yellow-400"
              : "text-green-400"
          }`}>
          {result.road_closure_probability > 70
            ? "High closure likelihood"
            : result.road_closure_probability > 40
              ? "Moderate closure likelihood"
              : "Low closure likelihood"}
        </p>
      </div>

      {/* Congestion risk bar */}
      {result.congestion_risk !== undefined && (
        <div className="mb-4 bg-black bg-opacity-20 rounded-lg p-3">
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-gray-400">Congestion Risk</span>
            <span className={`font-bold ${s.txt}`}>{result.congestion_risk}/100</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700"
              style={{ width: `${result.congestion_risk}%`, backgroundColor: ringColor }} />
          </div>
        </div>
      )}

      {/* How impact was calculated — explainability section */}
      <div className="bg-black bg-opacity-20 rounded-lg p-3 text-xs text-gray-400">
        <p className="font-semibold text-gray-300 mb-1">📐 Impact Formula (Explainable AI)</p>
        <p>Cause severity × 5 + Road closure × 20 + Major corridor × 10 + Peak hour × 5</p>
        <p className="text-gray-500 mt-0.5">Rule-based scoring — no black box</p>
      </div>
    </div>
  )
}
