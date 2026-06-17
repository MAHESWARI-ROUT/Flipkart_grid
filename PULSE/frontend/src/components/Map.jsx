import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import axios from 'axios'
import 'leaflet/dist/leaflet.css'

const color = (impact) =>
  impact >= 75 ? '#ef4444' : impact >= 50 ? '#f97316' : impact >= 25 ? '#eab308' : '#22c55e'

const LEGEND = [
  { c:'#ef4444', l:'Critical (75–100)' },
  { c:'#f97316', l:'High (50–74)' },
  { c:'#eab308', l:'Medium (25–49)' },
  { c:'#22c55e', l:'Low (0–24)' },
]

export default function Map({ apiBase }) {
  const [hotspots, setHotspots] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get(`${apiBase}/hotspots`)
      .then(r => { setHotspots(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const filtered = filter === 'all' ? hotspots
    : hotspots.filter(h => {
        const i = h.avg_impact || 0
        if (filter==='critical') return i >= 75
        if (filter==='high')     return i >= 50 && i < 75
        if (filter==='medium')   return i >= 25 && i < 50
        return i < 25
      })

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-white text-2xl font-bold">Congestion Hotspot Map</h2>
          <p className="text-gray-400 text-sm mt-1">
            {hotspots.length} spatial clusters identified · Bengaluru
          </p>
        </div>
        <div className="flex gap-2">
          {['all','critical','high','medium','low'].map(f=>(
            <button key={f} onClick={()=>setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors
                ${filter===f?'bg-blue-600 text-white':'bg-gray-800 text-gray-400 hover:text-white'}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="relative rounded-xl overflow-hidden border border-gray-800" style={{height:'70vh'}}>
        {loading && (
          <div className="absolute inset-0 bg-gray-900 flex items-center justify-center z-50">
            <p className="text-gray-400">Loading hotspot data…</p>
          </div>
        )}
        <MapContainer center={[12.97, 77.59]} zoom={12} style={{height:'100%',width:'100%'}}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="© OpenStreetMap contributors"/>
          {filtered.map((h, i) => (
            <CircleMarker key={i}
              center={[h.lat, h.lon]}
              radius={Math.max(Math.min((h.count||1)/3, 28), 7)}
              pathOptions={{
                color: color(h.avg_impact||0),
                fillColor: color(h.avg_impact||0),
                fillOpacity: 0.72, weight: 2
              }}>
              <Popup>
                <div style={{color:'#111',fontSize:'13px',minWidth:'190px',lineHeight:'1.6'}}>
                  <p style={{fontWeight:'bold',marginBottom:'6px',fontSize:'14px'}}>
                    Cluster #{h.hotspot_cluster ?? i}
                  </p>
                  <table style={{width:'100%'}}>
                    {[
                      ['Incidents',      h.count],
                      ['Avg Impact',     `${(h.avg_impact||0).toFixed(1)}/100`],
                      ['Top Cause',      h.top_cause],
                      ['Road Closures',  `${((h.road_closure_rate||0)*100).toFixed(0)}%`],
                    ].map(([k,v])=>(
                      <tr key={k}>
                        <td style={{color:'#555',paddingRight:'8px',paddingBottom:'2px'}}>{k}</td>
                        <td style={{fontWeight:'600'}}>{v}</td>
                      </tr>
                    ))}
                  </table>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>

        {/* Legend */}
        <div className="absolute bottom-4 right-4 bg-gray-900 bg-opacity-95 rounded-xl p-3 z-50 border border-gray-700 shadow-xl">
          <p className="text-gray-400 text-xs font-semibold mb-2 uppercase tracking-wide">Impact</p>
          {LEGEND.map(l=>(
            <div key={l.l} className="flex items-center gap-2 mb-1.5">
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{background:l.c}}/>
              <span className="text-gray-300 text-xs">{l.l}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
