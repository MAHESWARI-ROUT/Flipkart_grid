import { useState } from "react";
import axios from "axios";

export default function FeedbackForm({ result, incidentId, onSubmitted }) {

  const [form, setForm] = useState({
    incident_id: incidentId,
    predicted_severity: result.severity,
    actual_severity: result.severity,   // default to predicted — officer changes if wrong
    officers_recommended: result.officers_needed,
    officers_deployed: result.officers_needed,
    barricades_used: result.barricades_needed,
    diversion_effective: true,
    comments: "",
  });

  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    try {
      await axios.post(
        `${import.meta.env.VITE_API_BASE}/feedback`,
        form
      );
      setSubmitted(true);
      if (onSubmitted) onSubmitted();
    } catch {
      alert("Failed to save feedback. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-green-950 border border-green-800 rounded-xl p-5 text-center">
        <p className="text-3xl mb-2">✅</p>
        <p className="text-green-300 font-semibold">Post-event review saved!</p>
        <p className="text-green-600 text-xs mt-1">
          Your feedback helps PULSE improve future predictions.
        </p>
      </div>
    );
  }

  const field = (label, child) => (
    <div>
      <label className="block text-gray-400 text-xs font-medium mb-1">{label}</label>
      {child}
    </div>
  );

  const select = (key, options, label) =>
    field(label, (
      <select
        value={form[key]}
        onChange={e => setForm({ ...form, [key]: e.target.value })}
        className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 text-sm"
      >
        {options.map(o => (
          <option key={o.value ?? o} value={o.value ?? o}>
            {o.label ?? o}
          </option>
        ))}
      </select>
    ));

  const numInput = (key, label, min = 0, max = 50) =>
    field(label, (
      <input
        type="number"
        min={min}
        max={max}
        value={form[key]}
        onChange={e => setForm({ ...form, [key]: parseInt(e.target.value) || 0 })}
        className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 text-sm"
      />
    ));

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 p-5 space-y-4">

      <div>
        <h3 className="text-white font-bold text-sm">Post-Event Review</h3>
        <p className="text-gray-500 text-xs mt-0.5">
          Predicted severity: <span className="text-gray-300">{result.severity}</span>
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {select("actual_severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"], "Actual severity observed")}
        {select(
          "diversion_effective",
          [
            { value: true, label: "Yes — diversion worked" },
            { value: false, label: "No — diversion failed" },
          ],
          "Was diversion effective?"
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        {numInput("officers_deployed", "Officers actually deployed", 0, 50)}
        {numInput("barricades_used", "Barricades actually used", 0, 50)}
      </div>

      {field("Comments (optional)", (
        <textarea
          rows={2}
          placeholder="E.g. crowd larger than expected, diversion route blocked…"
          value={form.comments}
          onChange={e => setForm({ ...form, comments: e.target.value })}
          className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg px-3 py-2 text-sm resize-none"
        />
      ))}

      <button
        onClick={submit}
        disabled={loading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium px-4 py-2.5 rounded-lg text-sm transition-colors"
      >
        {loading ? "Saving…" : "Submit Post-Event Review"}
      </button>
    </div>
  );
}
