import { useState } from "react";
import axios from "axios";

export default function FeedbackForm({ result, incidentId }) {

  const [form, setForm] = useState({
    incident_id: incidentId,
    predicted_severity: result.severity,
    actual_severity: "MEDIUM",
    officers_recommended: result.officers_needed,
    officers_deployed: result.officers_needed,
    barricades_used: result.barricades_needed,

    diversion_effective: true,
    comments: ""
  });

  const submit = async () => {
    await axios.post(
      "http://localhost:8000/feedback",
      form
    );

    alert("Feedback Saved");
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">

      <h3 className="text-white font-bold mb-4">
        Post Event Feedback
      </h3>

      <label className="block text-gray-400 text-sm mb-2">
        Actual Severity
      </label>

      <select
        value={form.actual_severity}
        onChange={e => setForm({ ...form, actual_severity: e.target.value })}
        className="w-full bg-gray-800 text-white border border-gray-700 rounded-lg p-2"
      >
        <option>LOW</option>
        <option>MEDIUM</option>
        <option>HIGH</option>
        <option>CRITICAL</option>
      </select>

      <button
        onClick={submit}
        className="mt-4 bg-blue-600 px-4 py-2 rounded"
      >
        Submit Feedback
      </button>

    </div>
  );
}