const SEV = {
  CRITICAL: { ring: 'ring-red-500', bg: 'bg-red-950', txt: 'text-red-400', badge: 'bg-red-900 text-red-300' },
  HIGH: { ring: 'ring-orange-500', bg: 'bg-orange-950', txt: 'text-orange-400', badge: 'bg-orange-900 text-orange-300' },
  MEDIUM: { ring: 'ring-yellow-500', bg: 'bg-yellow-950', txt: 'text-yellow-400', badge: 'bg-yellow-900 text-yellow-300' },
  LOW: { ring: 'ring-green-500', bg: 'bg-green-950', txt: 'text-green-400', badge: 'bg-green-900 text-green-300' },
}

const RING_COLORS = {
  CRITICAL: '#ef4444', HIGH: '#f97316', MEDIUM: '#eab308', LOW: '#22c55e'
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

// ✅ NEW: Hotspot feature bar component
const FeatureBar = ({ label, value, color, tooltip }) => {
  // Normalize to 0–100 for display (values are raw frequencies/densities)
  const MAX_DISPLAY = 100
  const displayPct = Math.min((value / MAX_DISPLAY) * 100, 100)
  const intensity = value > 50 ? 'High' : value > 20 ? 'Medium' : 'Low'
  const intensityColor = value > 50 ? 'text-red-400' : value > 20 ? 'text-yellow-400' : 'text-green-400'

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-xs">
        <span className="text-gray-400">{label}</span>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${intensityColor}`}>{intensity}</span>
          <span className="text-gray-300 font-mono">{value.toFixed(2)}</span>
        </div>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${Math.max(displayPct, 4)}%`, backgroundColor: color }}
        />
      </div>
      {tooltip && <p className="text-gray-600 text-xs">{tooltip}</p>}
    </div>
  )
}

export default function ResultCard({ result }) {
  const s = SEV[result.severity] || SEV.LOW
  const ringColor = RING_COLORS[result.severity] || '#22c55e'

  // ✅ Spatial features from backend
  const jf = result.junction_freq ?? null
  const cf = result.corridor_freq ?? null
  const hd = result.hotspot_density ?? null
  const hasFeatures = jf !== null || cf !== null || hd !== null

  return (
    <div className={`rounded-xl border-2 ring-2 ${s.ring} ${s.bg} p-6 space-y-4`}>

      {/* ── Header ── */}
      <div className="flex justify-between items-start">
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

      {/* ── Road Closure Risk ── */}
      <div className="bg-black bg-opacity-30 rounded-lg p-3">
        <p className="text-gray-500 text-xs mb-1">Closure Risk</p>
        <p className="text-white font-bold text-base">{result.road_closure_probability}%</p>
        <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
          <div
            className={`h-2 rounded-full transition-all duration-700 ${result.road_closure_probability > 70 ? 'bg-red-500'
              : result.road_closure_probability > 40 ? 'bg-yellow-500'
                : 'bg-green-500'
              }`}
            style={{ width: `${result.road_closure_probability}%` }}
          />
        </div>
        <p className={`text-xs mt-1.5 ${result.road_closure_probability > 70 ? 'text-red-400'
          : result.road_closure_probability > 40 ? 'text-yellow-400'
            : 'text-green-400'
          }`}>
          {result.road_closure_probability > 70 ? '🔴 High closure likelihood'
            : result.road_closure_probability > 40 ? '🟡 Moderate closure likelihood'
              : '🟢 Low closure likelihood'}
        </p>
      </div>

      {/* ── Congestion Risk ── */}
      {result.congestion_risk !== undefined && (
        <div className="bg-black bg-opacity-20 rounded-lg p-3">
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

      {/* ── ✅ NEW: Spatial Intelligence / Hotspot Explanation ── */}
      {hasFeatures && (
        <div className="bg-black bg-opacity-25 rounded-lg p-4 space-y-3 border border-gray-700">
          <div className="flex items-center justify-between mb-1">
            <p className="text-gray-200 text-xs font-semibold uppercase tracking-wide">
              📍 Spatial Intelligence
            </p>
            <span className="text-gray-600 text-xs">ML features used</span>
          </div>

          {jf !== null && (
            <FeatureBar
              label="Junction Frequency"
              value={jf}
              color="#3b82f6"
              tooltip="How often incidents occur at this junction historically"
            />
          )}
          {cf !== null && (
            <FeatureBar
              label="Corridor Frequency"
              value={cf}
              color="#8b5cf6"
              tooltip="Historical incident rate on this road corridor"
            />
          )}
          {hd !== null && (
            <FeatureBar
              label="Hotspot Cluster Density"
              value={hd}
              color="#f97316"
              tooltip="Density of incidents in the nearest spatial cluster"
            />
          )}

          {/* Summary badge */}
          <div className={`mt-2 text-xs rounded-md px-3 py-2 flex items-center gap-2 ${(jf ?? 0) > 50 || (hd ?? 0) > 50
            ? 'bg-red-950 border border-red-800 text-red-300'
            : (jf ?? 0) > 20 || (hd ?? 0) > 20
              ? 'bg-yellow-950 border border-yellow-800 text-yellow-300'
              : 'bg-green-950 border border-green-800 text-green-300'
            }`}>
            {(jf ?? 0) > 50 || (hd ?? 0) > 50
              ? '⚠️ High-density hotspot — elevated risk zone'
              : (jf ?? 0) > 20 || (hd ?? 0) > 20
                ? '⚡ Moderate hotspot activity in this area'
                : '✓ Low historical incident density at this location'}
          </div>
        </div>
      )}
            

      {/* Smart Diversion Generator */}
      {result.diversion_plan?.length > 0 && (
        <div className="bg-black bg-opacity-25 rounded-lg p-4 border border-blue-700">
          <h3 className="text-blue-400 font-semibold mb-3">
            🚧 Smart Diversion Generator
          </h3>

          <div className="space-y-2">
            {result.diversion_plan.map((item, idx) => (
              <div
                key={idx}
                className="text-sm text-gray-300 flex items-start gap-2"
              >
                <span>➡️</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      

      {/* ── Explainability ── */}
      <div className="bg-black bg-opacity-20 rounded-lg p-3 text-xs text-gray-400">
        <p className="font-semibold text-gray-300 mb-1">📐 Why This Prediction Happened</p>
        <div className="mt-4">
          <h4 className="font-semibold text-white mb-2">
            Key Impact Factors
          </h4>

          {result.prediction_drivers?.map((d, i) => (
            <div
              key={i}
              className="flex justify-between text-sm py-1"
            >
              <span>{d.name}</span>
              <span className="font-bold text-yellow-400">
                +{d.score}
              </span>
            </div>
          ))}
        </div>
        <p className="text-sm text-orange-300 mt-3 mb-2">
          {result.prediction_explanation}
        </p>
        <p className="text-xs text-gray-400 mt-2">
          Cause severity × 5 + Road closure × 20 +
          Major corridor × 10 + Peak hour × 5
        </p>

      </div>

    </div>
  )
}