import { useState, useEffect } from 'react'
import IncidentForm from './components/IncidentForm'
import ResultCard from './components/ResultCard'
import ResourcePanel from './components/ResourcePanel'
import Map from './components/Map'
import Analytics from './components/Analytics'
import axios from 'axios'
import IncidentHistory from "./components/IncidentHistory";
import EventPlanner from "./components/EventPlanner";

const API = import.meta.env.VITE_API_BASE

export default function App() {
  const [tab, setTab] = useState('predict')
  const [result, setResult] = useState(null)
  const [apiOk, setApiOk] = useState(null)

  useEffect(() => {
    axios.get(`${API}/health`).then(() => setApiOk(true)).catch(() => setApiOk(false))
  }, [])

  const tabs = [
    { id: 'predict',  icon: '⚡',  label: 'Predict' },
    { id: 'planner',  icon: '📅',  label: 'Event Planner' },
    { id: 'map',      icon: '🗺️', label: 'Hotspot Map' },
    { id: 'analytics',icon: '📊',  label: 'Analytics' },
    { id: 'history',  icon: '📜',  label: 'Incident History' },
  ]

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">

      {/* ── Header ── */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center text-lg shadow-lg">
            🚦
          </div>
          <div>
            <h1 className="font-bold text-white text-lg leading-none">PULSE</h1>
            <p className="text-gray-400 text-xs">Predictive Urban Live Situation Engine · Bengaluru</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${
            apiOk === true  ? 'text-green-400 bg-green-950 border-green-800'  :
            apiOk === false ? 'text-red-400 bg-red-950 border-red-800'        :
                              'text-gray-400 bg-gray-800 border-gray-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              apiOk === true  ? 'bg-green-400 animate-pulse' :
              apiOk === false ? 'bg-red-400'                 : 'bg-gray-500'
            }`} />
            {apiOk === true ? 'API Connected' : apiOk === false ? 'API Offline' : 'Connecting…'}
          </div>
        </div>
      </header>

      {/* ── Tabs ── */}
      <div className="bg-gray-900 border-b border-gray-800 px-6">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-5 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-all ${
                tab === t.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ── */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">

        {/* Predict tab */}
        {tab === 'predict' && (
          <div>
            <div className="mb-6">
              <h2 className="text-white text-2xl font-bold">Incident Impact Predictor</h2>
              <p className="text-gray-400 text-sm mt-1">
                Report an incident → get instant AI impact assessment + resource plan
              </p>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <IncidentForm onResult={setResult} apiBase={API} />
              <div className="space-y-4">
                {result ? (
                  <>
                    <ResultCard result={result} />
                    <ResourcePanel result={result} />
                  </>
                ) : (
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 flex flex-col items-center justify-center text-center h-full min-h-64">
                    <div className="text-5xl mb-4 opacity-50">🎯</div>
                    <p className="text-gray-400 font-medium">Submit an incident to see predictions</p>
                    <p className="text-gray-600 text-sm mt-2">Impact score, severity, officers, actions</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Event Planner tab — NEW */}
        {tab === 'planner' && <EventPlanner apiBase={API} />}

        {/* Hotspot Map tab */}
        {tab === 'map' && <Map apiBase={API} />}

        {/* Analytics tab */}
        {tab === 'analytics' && <Analytics apiBase={API} />}

        {/* Incident History tab */}
        {tab === 'history' && <IncidentHistory />}

      </main>
    </div>
  )
}
