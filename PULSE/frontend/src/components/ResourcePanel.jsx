export default function ResourcePanel({ result }) {
  if (!result) return null
  const { severity, officers_needed, barricades_needed, diversion_needed, actions } = result

  const SEV_BORDER = {
    CRITICAL:'border-red-700', HIGH:'border-orange-700',
    MEDIUM:'border-yellow-700', LOW:'border-green-700'
  }

  return (
    <div className={`bg-gray-900 rounded-xl border ${SEV_BORDER[severity]||'border-gray-700'} p-6`}>
      <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
        <span>📋</span> Resource & Action Plan
      </h3>

      {/* Resource counts */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        {[
          { icon:'👮', label:'Officers', value: officers_needed,   color:'text-blue-400' },
          { icon:'🚧', label:'Barricades', value: barricades_needed, color:'text-orange-400' },
          { icon:'↩️', label:'Diversion', value: diversion_needed?'YES':'NO',
            color: diversion_needed?'text-red-400':'text-green-400' },
        ].map(r=>(
          <div key={r.label} className="bg-gray-800 rounded-xl p-4 text-center border border-gray-700">
            <p className="text-2xl mb-1">{r.icon}</p>
            <p className={`text-2xl font-bold ${r.color}`}>{r.value}</p>
            <p className="text-gray-400 text-xs mt-1">{r.label}</p>
          </div>
        ))}
      </div>

      {/* Action checklist */}
      <div>
        <p className="text-gray-300 text-xs font-semibold uppercase tracking-wide mb-3">
          Action Checklist
        </p>
        {actions && actions.length > 0
          ? <ul className="space-y-2">
              {actions.map((a, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center
                    text-xs font-bold flex-shrink-0 text-white
                    ${i===0?'bg-red-600':i===1?'bg-orange-600':'bg-gray-600'}`}>
                    {i+1}
                  </span>
                  <span className="text-gray-300 text-sm">{a}</span>
                </li>
              ))}
            </ul>
          : <p className="text-gray-500 text-sm italic">Standard monitoring — no immediate action required</p>
        }
      </div>

      {/* Business impact */}
      <div className="mt-4 pt-4 border-t border-gray-700">
        <p className="text-gray-500 text-xs">
          📊 Estimated impact: <span className="text-gray-300 font-medium">
            ~{result.vehicles_affected_est?.toLocaleString()} vehicles affected
          </span> · <span className="text-gray-300 font-medium">
            +{result.estimated_delay_mins} min delay
          </span>
        </p>
      </div>
    </div>
  )
}
