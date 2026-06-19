import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:8000";

const ATTENDANCE_OPTIONS = [
  { value: "lt_500",     label: "Less than 500",    icon: "👥", officers_hint: "Small gathering" },
  { value: "500_2000",   label: "500 – 2,000",      icon: "👥", officers_hint: "Moderate crowd" },
  { value: "2000_5000",  label: "2,000 – 5,000",    icon: "👫", officers_hint: "Large crowd" },
  { value: "5000_10000", label: "5,000 – 10,000",   icon: "🎪", officers_hint: "Very large event" },
  { value: "gt_10000",   label: "10,000+",           icon: "🏟️", officers_hint: "Mass gathering" },
];

const EVENT_TYPES = [
  { value: "public_event", label: "Public Event / Festival", icon: "🎭" },
  { value: "procession",   label: "Procession / Rally",      icon: "🚶" },
  { value: "rare_event",   label: "VIP Movement / Protest",  icon: "⚠️" },
  { value: "construction", label: "Planned Construction",    icon: "🏗️" },
];

const SEVERITY_CONFIG = {
  CRITICAL: { color: "text-red-400",    bg: "bg-red-950 border-red-700",    label: "CRITICAL — Immediate pre-deployment required" },
  HIGH:     { color: "text-orange-400", bg: "bg-orange-950 border-orange-700", label: "HIGH — Deploy officers 30 min before event" },
  MEDIUM:   { color: "text-yellow-400", bg: "bg-yellow-950 border-yellow-700", label: "MEDIUM — Standard pre-positioning" },
  LOW:      { color: "text-green-400",  bg: "bg-green-950 border-green-700",  label: "LOW — Monitor only" },
};

function StatBox({ icon, value, label, sub }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4 text-center">
      <p className="text-2xl mb-1">{icon}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-gray-300 text-xs font-medium mt-0.5">{label}</p>
      {sub && <p className="text-gray-500 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}

export default function EventPlanner({ apiBase = API }) {
  const [corridors,  setCorridors]  = useState([]);
  const [zones,      setZones]      = useState([]);
  const [junctions,  setJunctions]  = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [advisory,   setAdvisory]   = useState(null);
  const [error,      setError]      = useState(null);

  // Form state
  const [form, setForm] = useState({
    event_type_cause:     "public_event",
    event_date:           "",
    event_hour:           18,
    expected_attendance:  "2000_5000",
    corridor:             "Non-corridor",
    zone:                 "Unknown",
    junction:             "Unknown",
    requires_road_closure: false,
  });

  // Load dropdowns once
  useEffect(() => {
    axios.get(`${apiBase}/corridors`).then(r => setCorridors(r.data.corridors)).catch(() => {});
    axios.get(`${apiBase}/zones`).then(r => setZones(r.data.zones)).catch(() => {});
    axios.get(`${apiBase}/junctions`).then(r => setJunctions(r.data.junctions)).catch(() => {});
  }, [apiBase]);

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }));

  const generateAdvisory = async () => {
    setLoading(true);
    setError(null);
    setAdvisory(null);

    // Parse event date to extract month (fall back to current month)
    let month = new Date().getMonth() + 1;
    if (form.event_date) {
      const d = new Date(form.event_date);
      if (!isNaN(d)) month = d.getMonth() + 1;
    }

    const payload = {
      event_cause:            form.event_type_cause,
      event_type:             "planned",
      hour:                   Number(form.event_hour),
      month:                  month,
      corridor:               form.corridor,
      zone:                   form.zone,
      junction:               form.junction,
      requires_road_closure:  form.requires_road_closure,
      expected_attendance:    form.expected_attendance,
      latitude:               12.97,
      longitude:              77.59,
    };

    try {
      const res = await axios.post(`${apiBase}/predict`, payload);
      setAdvisory({ ...res.data, event_date: form.event_date, event_hour: form.event_hour });
    } catch (e) {
      setError("Could not generate advisory. Please check the API connection.");
    } finally {
      setLoading(false);
    }
  };

  const selectedAttendance = ATTENDANCE_OPTIONS.find(o => o.value === form.expected_attendance);
  const selectedEventType  = EVENT_TYPES.find(e => e.value === form.event_type_cause);

  // Pre-deployment timing recommendation
  const preDeployMins = advisory
    ? advisory.severity === "CRITICAL" ? 60
    : advisory.severity === "HIGH"     ? 45
    : advisory.severity === "MEDIUM"   ? 30 : 15
    : null;

  const sevCfg = advisory ? SEVERITY_CONFIG[advisory.severity] : null;

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div>
        <h2 className="text-white text-2xl font-bold">Event Planner</h2>
        <p className="text-gray-400 text-sm mt-1">
          Schedule a future event → get a pre-deployment advisory before it starts
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* ── Left: Planning Form ── */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">

          <p className="text-white font-semibold text-sm flex items-center gap-2">
            📅 Plan a New Event
          </p>

          {/* Event type */}
          <div>
            <label className="text-gray-400 text-xs font-medium block mb-2">Event Type</label>
            <div className="grid grid-cols-2 gap-2">
              {EVENT_TYPES.map(et => (
                <button
                  key={et.value}
                  onClick={() => set("event_type_cause", et.value)}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-sm transition-all text-left ${
                    form.event_type_cause === et.value
                      ? "border-blue-500 bg-blue-950 text-blue-300"
                      : "border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-600"
                  }`}
                >
                  <span>{et.icon}</span>
                  <span className="text-xs leading-tight">{et.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Date + Time */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-gray-400 text-xs font-medium block mb-1">Event Date</label>
              <input
                type="date"
                value={form.event_date}
                min={new Date().toISOString().split("T")[0]}
                onChange={e => set("event_date", e.target.value)}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-gray-400 text-xs font-medium block mb-1">
                Start Hour — {form.event_hour}:00
              </label>
              <input
                type="range"
                min={0} max={23} step={1}
                value={form.event_hour}
                onChange={e => set("event_hour", Number(e.target.value))}
                className="w-full mt-2"
              />
              <div className="flex justify-between text-gray-600 text-xs mt-0.5">
                <span>12 AM</span><span>12 PM</span><span>11 PM</span>
              </div>
            </div>
          </div>

          {/* Attendance */}
          <div>
            <label className="text-gray-400 text-xs font-medium block mb-2">
              Expected Attendance — drives crowd-impact scoring
            </label>
            <div className="space-y-1.5">
              {ATTENDANCE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => set("expected_attendance", opt.value)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border text-sm transition-all ${
                    form.expected_attendance === opt.value
                      ? "border-blue-500 bg-blue-950 text-blue-300"
                      : "border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-600"
                  }`}
                >
                  <span>{opt.icon} {opt.label}</span>
                  <span className="text-xs text-gray-500">{opt.officers_hint}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Location */}
          <div>
            <label className="text-gray-400 text-xs font-medium block mb-2">Location</label>
            <div className="space-y-2">
              <select
                value={form.corridor}
                onChange={e => set("corridor", e.target.value)}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="Non-corridor">No specific corridor</option>
                {corridors.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <select
                value={form.zone}
                onChange={e => set("zone", e.target.value)}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="Unknown">No specific zone</option>
                {zones.map(z => <option key={z} value={z}>{z}</option>)}
              </select>
              <select
                value={form.junction}
                onChange={e => set("junction", e.target.value)}
                className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="Unknown">No specific junction</option>
                {junctions.map(j => <option key={j} value={j}>{j}</option>)}
              </select>
            </div>
          </div>

          {/* Road closure toggle */}
          <div className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3 border border-gray-700">
            <div>
              <p className="text-white text-sm font-medium">Road Closure Required</p>
              <p className="text-gray-500 text-xs">Significantly impacts traffic flow</p>
            </div>
            <button
              onClick={() => set("requires_road_closure", !form.requires_road_closure)}
              className={`relative w-11 h-6 rounded-full transition-colors ${
                form.requires_road_closure ? "bg-blue-600" : "bg-gray-600"
              }`}
            >
              <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                form.requires_road_closure ? "translate-x-5" : "translate-x-0.5"
              }`} />
            </button>
          </div>

          {/* Generate button */}
          <button
            onClick={generateAdvisory}
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 text-white font-semibold px-4 py-3 rounded-xl text-sm transition-all"
          >
            {loading ? "⏳ Generating advisory…" : "📋 Generate Pre-Deployment Advisory"}
          </button>

          {error && (
            <p className="text-red-400 text-sm bg-red-950 border border-red-800 rounded-lg px-4 py-2">
              {error}
            </p>
          )}
        </div>

        {/* ── Right: Advisory Output ── */}
        <div className="space-y-4">
          {!advisory && !loading && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 flex flex-col items-center justify-center text-center h-full min-h-64">
              <div className="text-5xl mb-4 opacity-40">📋</div>
              <p className="text-gray-400 font-medium">Fill in event details to generate</p>
              <p className="text-gray-600 text-sm mt-2">
                Pre-deployment plan · resource advisory · congestion forecast
              </p>
            </div>
          )}

          {loading && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 flex flex-col items-center justify-center text-center h-full min-h-64">
              <div className="text-4xl mb-4 animate-pulse">⏳</div>
              <p className="text-gray-400">Running prediction model…</p>
            </div>
          )}

          {advisory && sevCfg && (
            <>
              {/* Severity banner */}
              <div className={`rounded-xl border p-4 ${sevCfg.bg}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-xs font-medium uppercase tracking-wide">
                      Predicted Severity
                    </p>
                    <p className={`text-3xl font-bold mt-1 ${sevCfg.color}`}>
                      {advisory.severity}
                    </p>
                    <p className="text-gray-300 text-sm mt-1">{sevCfg.label}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-gray-400 text-xs">Impact Score</p>
                    <p className="text-4xl font-bold text-white">{advisory.impact_score}</p>
                  </div>
                </div>
              </div>

              {/* Pre-deployment timing */}
              <div className="bg-indigo-950 border border-indigo-800 rounded-xl p-4">
                <p className="text-indigo-300 font-semibold text-sm mb-2">⏰ Pre-Deployment Window</p>
                {advisory.event_date && (
                  <p className="text-white font-bold text-lg">
                    {advisory.event_date} at {String(advisory.event_hour).padStart(2, "0")}:00
                  </p>
                )}
                <p className="text-indigo-200 text-sm mt-1">
                  Deploy officers{" "}
                  <strong className="text-white">{preDeployMins} minutes before</strong> the event starts
                  {advisory.event_date && advisory.event_hour != null && (
                    <span className="text-indigo-400">
                      {" "}(by{" "}
                      {String(Math.max(0, advisory.event_hour - Math.floor(preDeployMins / 60))).padStart(2, "0")}
                      :{String(60 - (preDeployMins % 60 || 60)).padStart(2, "0").replace("60", "00")} hrs)
                    </span>
                  )}
                </p>
              </div>

              {/* Resource numbers */}
              <div className="grid grid-cols-3 gap-3">
                <StatBox icon="👮" value={advisory.officers_needed}   label="Officers" sub="Pre-position" />
                <StatBox icon="🚧" value={advisory.barricades_needed} label="Barricades" sub="Required" />
                <StatBox icon="🔀" value={advisory.diversion_needed ? "YES" : "NO"} label="Diversion" sub="Activate?" />
              </div>

              {/* Congestion + closure risk */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
                <p className="text-white font-semibold text-sm">Forecasted Risk Levels</p>
                {[
                  { label: "Congestion Risk",         value: advisory.congestion_risk,          max: 100, color: "#f97316" },
                  { label: "Road Closure Probability",value: advisory.road_closure_probability,  max: 100, color: "#ef4444" },
                  { label: "Prediction Confidence",   value: advisory.priority_confidence,       max: 100, color: "#3b82f6" },
                ].map(r => (
                  <div key={r.label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">{r.label}</span>
                      <span className="text-gray-200 font-medium">{r.value}%</span>
                    </div>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${Math.min(r.value, 100)}%`, background: r.color }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Action checklist */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-white font-semibold text-sm mb-3">📋 Pre-Event Action Checklist</p>
                <ul className="space-y-2">
                  {(advisory.actions || []).map((action, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                      <span className="text-blue-400 font-bold flex-shrink-0">{i + 1}.</span>
                      {action}
                    </li>
                  ))}
                  {/* Always add pre-positioning advice */}
                  <li className="flex items-start gap-2 text-sm text-gray-300">
                    <span className="text-blue-400 font-bold flex-shrink-0">
                      {(advisory.actions || []).length + 1}.
                    </span>
                    Pre-position {advisory.officers_needed} officers at entry/exit points{" "}
                    {preDeployMins} min before start
                  </li>
                </ul>
              </div>

              {/* Expected attendance label */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-white font-semibold text-sm mb-2">📊 Crowd Impact Analysis</p>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Expected Attendance</span>
                  <span className="text-white font-medium">{advisory.expected_attendance_label}</span>
                </div>
                <div className="flex justify-between text-sm mt-1">
                  <span className="text-gray-400">Attendance Impact Points</span>
                  <span className="text-orange-400 font-medium">+{advisory.attendance_impact_points}</span>
                </div>
                <div className="flex justify-between text-sm mt-1">
                  <span className="text-gray-400">Resource Multiplier</span>
                  <span className="text-blue-400 font-medium">×{advisory.attendance_resource_mult?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm mt-1">
                  <span className="text-gray-400">Estimated Vehicles Affected</span>
                  <span className="text-white font-medium">{(advisory.vehicles_affected_est || 0).toLocaleString()}</span>
                </div>
              </div>

              {/* Why this prediction */}
              {advisory.prediction_drivers?.length > 0 && (
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-white font-semibold text-sm mb-3">🔍 Why This Forecast</p>
                  <div className="space-y-2">
                    {advisory.prediction_drivers.map((d, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="text-gray-300">{d.name}</span>
                        <span className="text-orange-400 font-medium">+{d.score}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-gray-500 text-xs mt-3 italic">{advisory.prediction_explanation}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
