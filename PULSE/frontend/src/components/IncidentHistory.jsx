import { useEffect, useState } from "react";
import FeedbackForm from "./FeedbackForm";
import axios from "axios";

export default function IncidentHistory() {

    const [incidents, setIncidents] = useState([]);
    const [selectedIncident, setSelectedIncident] = useState(null);
    const [feedbackStats, setFeedbackStats] = useState(null);

    const [submittedIds, setSubmittedIds] = useState(
        JSON.parse(localStorage.getItem("submittedFeedbacks") || "[]")
    );

    useEffect(() => {

        axios
            .get('${import.meta.env.VITE_API_BASE}/incident-history')
            .then(res => setIncidents(res.data));

        axios
            .get('${import.meta.env.VITE_API_BASE}/feedback-stats')
            .then(res => setFeedbackStats(res.data))
            .catch(console.error);

    }, []);
    const markFeedbackSubmitted = (id) => {

        const updated = [...new Set([...submittedIds, id])];

        setSubmittedIds(updated);

        localStorage.setItem(
            "submittedFeedbacks",
            JSON.stringify(updated)
        );
    };

    return (

    <>

        {feedbackStats && (

            <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-5">

                <h3 className="text-white font-bold mb-3">
                    Feedback Analytics
                </h3>

                <p className="text-gray-300">
                    Events Reviewed: {feedbackStats.events_reviewed}
                </p>

                <p className="text-gray-300">
                    Prediction Accuracy: {feedbackStats.prediction_accuracy}%
                </p>

                <p className="text-gray-300">
                    Resource Accuracy: {feedbackStats.resource_accuracy}%
                </p>

                <p className="text-gray-300">
                    Diversion Success: {feedbackStats.diversion_success_rate}%
                </p>

            </div>

        )}

        <div className="space-y-3">

            {incidents.slice().reverse().map((incident, index) => (

                <div
                    key={index}
                    className="bg-gray-900 border border-gray-700 rounded-xl p-4"
                >

                    <h3 className="text-white font-bold">
                        {incident.incident_type}
                    </h3>
                    <div className="mt-2 mb-3">

                        {incident.junction &&
                            incident.junction !== "Unknown" && (
                                <p className="text-blue-300 text-sm">
                                    📍 {incident.junction}
                                </p>
                            )}

                        {incident.corridor &&
                            incident.corridor !== "Unknown" &&
                            incident.corridor !== "Non-corridor" && (
                                <p className="text-orange-300 text-sm mt-1">
                                    🛣 {incident.corridor}
                                </p>
                            )}

                    </div>

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
                    {submittedIds.includes(incident.id) ? (

                        <div className="mt-3 text-green-400 text-sm">
                            ✓ Feedback Submitted
                        </div>

                    ) : (

                        <button
                            onClick={() =>
                                setSelectedIncident(
                                    selectedIncident?.id === incident.id
                                        ? null
                                        : incident
                                )
                            }
                            className={`mt-3 text-white px-3 py-2 rounded-lg text-sm ${selectedIncident?.id === incident.id
                                ? "bg-red-600 hover:bg-red-700"
                                : "bg-blue-600 hover:bg-blue-700"
                                }`}
                        >
                            {selectedIncident?.id === incident.id
                                ? "Close Feedback"
                                : "Give Feedback"}
                        </button>

                    )}
                    {selectedIncident?.id === incident.id && (
                        <div className="mt-5 border-t border-gray-700 pt-5">


                            <FeedbackForm
                                incidentId={incident.id}
                                onSubmitted={() =>
                                    markFeedbackSubmitted(incident.id)
                                }
                                result={{
                                    severity: incident.severity,
                                    officers_needed: incident.officers_needed,
                                    barricades_needed: incident.barricades_needed
                                }}
                            />

                        </div>
                    )}


                </div>

            ))}


        </div>
         </>
    );
}