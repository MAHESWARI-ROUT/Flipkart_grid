import { useState } from 'react'
import axios from 'axios'

const CAUSES = [
  { v: 'accident', l: '🚗 Accident' },
  { v: 'vehicle_breakdown', l: '🔧 Vehicle Breakdown' },
  { v: 'construction', l: '🏗️ Construction' },
  { v: 'water_logging', l: '💧 Water Logging' },
  { v: 'tree_fall', l: '🌳 Tree Fall' },
  { v: 'pot_holes', l: '🕳️ Pot Holes' },
  { v: 'congestion', l: '🚦 Congestion' },
  { v: 'public_event', l: '🎪 Public Event' },
  { v: 'procession', l: '🚶 Procession' },
  { v: 'rare_event', l: '⭐ VIP / Protest / Debris' },
  { v: 'road_conditions', l: '🛣️ Road Conditions' },
  { v: 'others', l: '❓ Others' },
]

const CORRIDORS = [
  'Non-corridor', 'Mysore Road', 'Bellary Road 1', 'Bellary Road 2',
  'Tumkur Road', 'Hosur Road', 'ORR North 1', 'ORR North 2',
  'Old Madras Road', 'Magadi Road', 'ORR East 1', 'ORR East 2',
  'ORR West 1', 'Bannerghata Road', 'West of Chord Road',
  'Airport New South Road', 'Varthur Road', 'Hennur Main Road',
]

const ZONES = [
  'Unknown', 'Central Zone 1', 'Central Zone 2', 'North Zone 1', 'North Zone 2',
  'South Zone 1', 'South Zone 2', 'East Zone 1', 'East Zone 2',
  'West Zone 1', 'West Zone 2',
]

// Top junctions from your analytics data (top 8 shown first, then rest)
const JUNCTIONS = [
  'Unknown',
  // ── High-risk (from your analytics) ──
  'MekhriCircle',
  'AyyappaTempleJunc',
  'SatteliteBusStandJunc',
  'YeshwanthpuraCircle',
  'YelhankaCircle',
  'SilkBoardJunc',
  'toll gate mysore road',
  'Nagavara-ORR Junction',
  // ── Other major junctions ──
  'HebbalFlyoverJunc',
  'KempegowdaCircle',
  'TrinityCircle',
  'DomlurJunc',
  'KoramangalaJunc',
  'MarathahalliJunc',
  'KRPuramJunc',
  'WhitefieldJunc',
  'ElectronicCityJunc',
  'BannerghataRoadJunc',
  'JPNagarJunc',
  'KengeriJunc',
  'RajajinagarCircle',
  'MalleshwaramCircle',
  'HebbalCircle',
  'TinFactoryJunc',
  'BaiyyappanahalliBridge',
  'HopefarmsJunc',
  'VarthurJunc',
  'SarjapurJunc',
  'BellandurJunc',
  'HSRLayoutJunc',
]

const inp = "w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none transition-colors"

export default function IncidentForm({ onResult, apiBase }) {
  const [form, setForm] = useState({
    event_cause: 'accident',
    event_type: 'unplanned',
    requires_road_closure: false,
    hour: new Date().getHours(),
    latitude: 12.97,
    longitude: 77.59,
    corridor: 'Tumkur Road',
    zone: 'Unknown',
    junction: 'Unknown',
  })
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async () => {
    setLoading(true)
    setErr(null)
    try {
      const res = await axios.post(`${apiBase}/predict`, form)
      onResult(res.data)
    } catch (e) {
      setErr(e.response?.data?.detail || 'Cannot reach backend. Is uvicorn running on port 8000?')
    } finally {
      setLoading(false)
    }
  }

  const downloadPDF = async () => {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/export-report",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(form),
        }
      );

      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");

      a.href = url;
      a.download = "incident_report.pdf";

      document.body.appendChild(a);
      a.click();
      a.remove();

    } catch (err) {
      console.error(err);
    }
  };

  const Label = ({ children }) => (
    <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wide mb-1.5">
      {children}
    </label>
  )

  const isHighRiskJunction = ['MekhriCircle', 'AyyappaTempleJunc', 'SatteliteBusStandJunc',
    'YeshwanthpuraCircle', 'YelhankaCircle', 'SilkBoardJunc'].includes(form.junction)

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
      <div className="flex items-center gap-2 mb-5">
        <span className="w-6 h-6 bg-red-600 rounded flex items-center justify-center text-xs font-bold text-white">!</span>
        <h3 className="text-white font-semibold">Report New Incident</h3>
      </div>

      {/* Cause */}
      <div className="mb-4">
        <Label>Incident Type</Label>
        <select value={form.event_cause} onChange={e => set('event_cause', e.target.value)} className={inp}>
          {CAUSES.map(c => <option key={c.v} value={c.v}>{c.l}</option>)}
        </select>
      </div>

      {/* Planned / Unplanned */}
      <div className="mb-4">
        <Label>Event Type</Label>
        <div className="flex gap-2">
          {['unplanned', 'planned'].map(t => (
            <button key={t} onClick={() => set('event_type', t)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors
                ${form.event_type === t
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'}`}>
              {t === 'unplanned' ? '⚡ Unplanned' : '📅 Planned'}
            </button>
          ))}
        </div>
      </div>

      {/* Corridor + Zone */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <Label>Corridor</Label>
          <select value={form.corridor} onChange={e => set('corridor', e.target.value)} className={inp}>
            {CORRIDORS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <Label>Zone</Label>
          <select value={form.zone} onChange={e => set('zone', e.target.value)} className={inp}>
            {ZONES.map(z => <option key={z} value={z}>{z}</option>)}
          </select>
        </div>
      </div>

      {/* ✅ NEW: Junction dropdown */}
      <div className="mb-4">
        <Label>
          Junction
          <span className="ml-2 text-blue-400 normal-case font-normal text-xs">
            — activates junction_freq &amp; hotspot features
          </span>
        </Label>
        <select
          value={form.junction}
          onChange={e => set('junction', e.target.value)}
          className={inp}>
          {JUNCTIONS.map(j => <option key={j} value={j}>{j}</option>)}
        </select>

        {/* Feedback hints */}
        {form.junction === 'Unknown' && (
          <p className="text-gray-600 text-xs mt-1.5 flex items-center gap-1">
            <span>⚠️</span> Select a junction for more accurate predictions
          </p>
        )}
        {isHighRiskJunction && (
          <p className="text-red-400 text-xs mt-1.5 flex items-center gap-1">
            <span>🔴</span> High-risk junction — historically elevated incident frequency
          </p>
        )}
        {form.junction !== 'Unknown' && !isHighRiskJunction && (
          <p className="text-green-400 text-xs mt-1.5 flex items-center gap-1">
            <span>✓</span> Junction frequency feature active
          </p>
        )}
      </div>

      {/* Hour */}
      <div className="mb-4">
        <Label>
          Time of Incident —&nbsp;
          <span className="text-white normal-case font-bold">{form.hour}:00</span>
          {[7, 8, 9, 17, 18, 19, 20, 21].includes(form.hour) &&
            <span className="ml-2 text-yellow-400 normal-case">⚠️ Peak Hour</span>}
        </Label>
        <input type="range" min="0" max="23" value={form.hour}
          onChange={e => set('hour', parseInt(e.target.value))}
          className="w-full accent-blue-500 cursor-pointer" />
        <div className="flex justify-between text-gray-600 text-xs mt-1">
          <span>12 AM</span><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>11 PM</span>
        </div>
      </div>

      {/* Road closure toggle */}
      <div className="mb-5 flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3 border border-gray-700">
        <div>
          <p className="text-white text-sm font-medium">Requires Road Closure</p>
          <p className="text-gray-500 text-xs">Significantly impacts traffic flow</p>
        </div>
        <button
          onClick={() => set('requires_road_closure', !form.requires_road_closure)}
          className={`relative w-12 h-6 rounded-full transition-colors flex-shrink-0
            ${form.requires_road_closure ? 'bg-red-600' : 'bg-gray-600'}`}>
          <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform
            ${form.requires_road_closure ? 'translate-x-6' : 'translate-x-0.5'}`} />
        </button>
      </div>

      {err && (
        <div className="mb-4 p-3 bg-red-950 border border-red-800 rounded-lg text-red-300 text-xs">
          ⚠️ {err}
        </div>
      )}

      <button
        onClick={submit}
        disabled={loading}
        className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400
                   disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3
                   rounded-lg transition-all text-sm shadow-lg">
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Analyzing…
          </span>
        ) : (
          '⚡ Predict Impact & Get Resource Plan'
        )}
      </button>
      <button
        onClick={downloadPDF}
        className="w-full mt-3 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-semibold"
      >
        📄 Export Incident Report
      </button>
    </div>
  )
}