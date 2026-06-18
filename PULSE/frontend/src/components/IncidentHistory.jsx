import { useEffect, useState } from "react";
import FeedbackForm from "./FeedbackForm";
import axios from "axios";

export default function IncidentHistory() {

    const [incidents, setIncidents] = useState([]);
    const [selectedIncident, setSelectedIncident] = useState(null);

    useEffect(() => {

        axios
            .get("http://127.0.0.1:8000/incident-history")
            .then(res => setIncidents(res.data));

    }, []);

    return (

        <div className="space-y-3">

            {incidents.slice().reverse().map((incident, index) => (

                <div
                    key={index}
                    className="bg-gray-900 border border-gray-700 rounded-xl p-4"
                >

                    <h3 className="text-white font-bold">
                        {incident.incident_type}
                    </h3>

                    <p className="text-gray-400">
                        Severity: {incident.severity}
                    </p>

                    <p className="text-gray-400">
                        Impact Score: {incident.impact_score}
                    </p>

                    <p className="text-gray-400">
                        Officers: {incident.officers_needed}
                    </p>

                    <p className="text-gray-500 text-sm">
                        {incident.timestamp}
                    </p>
                    <button
                        onClick={() => setSelectedIncident(incident)}
                        className="mt-3 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-sm"
                    >
                        Give Feedback
                    </button>


                </div>

            ))}
            {selectedIncident && (
                <div className="mt-6">
                    <FeedbackForm
                        incidentId={selectedIncident.id}
                        result={{
                            severity: selectedIncident.severity,
                            officers_needed: selectedIncident.officers_needed,
                            barricades_needed: selectedIncident.barricades_needed
                        }}
                    />
                </div>
            )}

        </div>
    );
}