import { useState, useEffect, useRef } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const C = {
  flame: "#FF6B35", teal: "#00D4A8", bg: "#07090F", card: "#0C0F1A",
  border: "#161D2E", text: "#DDE4F0", muted: "#4A5568", mutedLt: "#6B7A9A",
  good: "#00C48C", moderate: "#F5C842", warning: "#FF9500",
};

const STATIONS = [
  { id: 1, name: "US Consulate", area: "Gulberg", lat: 31.522, lon: 74.396, base: 187 },
  { id: 2, name: "Jail Road", area: "City Centre", lat: 31.507, lon: 74.344, base: 218 },
  { id: 3, name: "PCRWR", area: "Thokar Niaz Baig", lat: 31.452, lon: 74.388, base: 196 },
  { id: 4, name: "DHA Phase 5", area: "DHA", lat: 31.478, lon: 74.394, base: 171 },
  { id: 5, name: "Gulberg III", area: "Gulberg", lat: 31.513, lon: 74.335, base: 204 },
];

function aqiMeta(v) {
  if (v <= 50) return { label: "Good", color: C.good };
  if (v <= 100) return { label: "Moderate", color: C.moderate };
  if (v <= 150) return { label: "Unhealthy (SG)", color: C.warning };
  if (v <= 200) return { label: "Unhealthy", color: C.flame };
  if (v <= 300) return { label: "Very Unhealthy", color: "#FF4081" };
  return { label: "Hazardous", color: "#C62828" };
}

function genForecast() {
  const now = new Date(); const rows = [];
  for (let i = 0; i < 72; i++) {
    const t = new Date(now.getTime() + i * 3600000);
    const h = t.getHours();
    const peak = (h >= 7 && h <= 10) ? 28 : (h >= 17 && h <= 20) ? 22 : 0;
    const night = h < 5 ? 18 : 0;
    const v = Math.round(190 + Math.sin(i * 0.13) * 18 + peak + night + (Math.random() - 0.5) * 14);
    const label = i === 0 ? "Now" : i % 12 === 0 ? `${String(t.getHours()).padStart(2,"0")}:00\n${t.getDate()}/${t.getMonth()+1}` : "";
    rows.push({ i, aqi: Math.max(60, Math.min(340, v)), label, h: t.getHours() });
  }
  return rows;
}

const FORECAST = genForecast();
const BEST_WINDOW = FORECAST.slice(0, 24).reduce((m, f) => f.aqi < m.aqi ? f : m, FORECAST[0]);

const MAP_W = 260, MAP_H = 170;
const toX = (lon) => ((lon - 73.9) / 0.8) * MAP_W;
const toY = (lat) => ((31.8 - lat) / 0.6) * MAP_H;

const MONTH = new Date().getMonth();
const IS_SMOG = MONTH >= 9 && MONTH <= 10;

const QUICK = [
  "Should I dispatch trucks now?",
  "Safest route: Gulberg to DHA?",
  "Driver safety advisory today",
  "When is the best dispatch window?",
];

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const m = aqiMeta(payload[0].value);
  return (
    <div style={{ background: C.card, border: `1px solid ${m.color}44`, borderRadius: 8, padding: "8px 12px", fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}>
      <div style={{ color: C.mutedLt, marginBottom: 2 }}>Hour +{payload[0].payload.i}</div>
      <div style={{ color: m.color, fontSize: 18, fontWeight: 700 }}>{payload[0].value}</div>
      <div style={{ color: m.color }}>{m.label}</div>
    </div>
  );
}

export default function AirSense() {
  const [stations, setStations] = useState(STATIONS.map(s => ({ ...s, aqi: s.base + Math.floor((Math.random() - 0.5) * 14) })));
  const [msgs, setMsgs] = useState([{ role: "assistant", content: "Hello. I'm your AirSense Decision Advisor — I have real-time access to all 5 Lahore station readings and the 72-hour forecast.\n\nAsk me anything about route safety, driver health, dispatch windows, or fleet operations." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [ts, setTs] = useState(new Date());
  const chatEl = useRef(null);

  useEffect(() => {
    const iv = setInterval(() => {
      setStations(p => p.map(s => ({ ...s, aqi: Math.max(90, Math.min(340, s.aqi + Math.floor((Math.random() - 0.5) * 7))) })));
      setTs(new Date());
    }, 8000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => { if (chatEl.current) chatEl.current.scrollTop = chatEl.current.scrollHeight; }, [msgs]);

  const avg = Math.round(stations.reduce((s, x) => s + x.aqi, 0) / stations.length);
  const avgMeta = aqiMeta(avg);

  async function send(text) {
    const q = (text || input).trim();
    if (!q || busy) return;
    setInput("");
    setMsgs(p => [...p, { role: "user", content: q }]);
    setBusy(true);
    const stSummary = stations.map(s => `${s.name} (${s.area}): AQI ${s.aqi} — ${aqiMeta(s.aqi).label}`).join("\n");
    const fcSummary = FORECAST.slice(0, 12).map(f => `+${f.i}h: ${f.aqi}`).join("  |  ");
    const sys = `You are the AirSense Pakistan Decision Advisor — AI embedded in a real-time air quality platform built for logistics SMEs in Lahore, Pakistan.

LIVE DATA (${ts.toLocaleTimeString("en-PK")}):
City average AQI: ${avg} (${avgMeta.label})
Station readings:
${stSummary}

12-hour forecast: ${fcSummary}
Optimal dispatch window (next 24h): Hour +${BEST_WINDOW.i} at AQI ${BEST_WINDOW.aqi} (${aqiMeta(BEST_WINDOW.aqi).label})
${IS_SMOG ? "ACTIVE: Crop burning season (Oct–Nov) — elevated PM2.5 from Punjab agricultural fires." : "Season: Normal."}

Your role: Give specific, actionable logistics decisions. Recommend exact routes, timing windows, driver protection measures. Be direct and precise — logistics managers need clear decisions, not information dumps. Reference exact AQI values.`;
    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514", max_tokens: 1000,
          system: sys,
          messages: [...msgs.filter(m => m.role !== "system"), { role: "user", content: q }],
        }),
      });
      const d = await res.json();
      const reply = d.content?.[0]?.text || "Connection issue — please retry.";
      setMsgs(p => [...p, { role: "assistant", content: reply }]);
    } catch {
      setMsgs(p => [...p, { role: "assistant", content: "Network error. Please try again." }]);
    }
    setBusy(false);
  }

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "'Outfit', sans-serif", fontSize: 13 }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:${C.card}}::-webkit-scrollbar-thumb{background:${C.border};border-radius:2px}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes blink{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.8);opacity:0}}
        .sc{transition:transform 0.25s,border-color 0.25s}.sc:hover{transform:translateY(-2px)}
        .qb{background:transparent;border:1px solid ${C.border};border-radius:20px;color:${C.mutedLt};cursor:pointer;padding:4px 11px;font-size:11px;font-family:'Outfit',sans-serif;transition:all 0.2s}
        .qb:hover{border-color:${C.teal}55;color:${C.teal}}
        .send{background:${C.teal};border:none;border-radius:8px;color:${C.bg};font-weight:600;font-size:13px;font-family:'Outfit',sans-serif;padding:0 20px;cursor:pointer;transition:opacity 0.2s}
        .send:hover{opacity:0.85}.send:disabled{opacity:0.4;cursor:not-allowed}
        .inp{background:rgba(255,255,255,0.04);border:1px solid ${C.border};border-radius:8px;padding:10px 14px;font-size:13px;color:${C.text};outline:none;font-family:'Outfit',sans-serif;flex:1;transition:border-color 0.2s}
        .inp:focus{border-color:${C.teal}44}
        .inp::placeholder{color:${C.muted}}
      `}</style>

      {/* Header */}
      <header style={{ borderBottom: `1px solid ${C.border}`, padding: "14px 22px", display: "flex", alignItems: "center", justifyContent: "space-between", background: C.card }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          <div style={{ width: 34, height: 34, borderRadius: 8, background: `${C.flame}22`, border: `1px solid ${C.flame}44`, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="7" stroke={C.flame} strokeWidth="1.5"/>
              <circle cx="9" cy="9" r="3" fill={C.flame}/>
              <line x1="9" y1="2" x2="9" y2="5" stroke={C.teal} strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="9" y1="13" x2="9" y2="16" stroke={C.teal} strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="2" y1="9" x2="5" y2="9" stroke={C.teal} strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="13" y1="9" x2="16" y2="9" stroke={C.teal} strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: "-0.3px" }}>AirSense <span style={{ color: C.teal }}>Pakistan</span></div>
            <div style={{ fontSize: 10, color: C.muted, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.3px" }}>Deliver on time—despite smog.</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 10, color: C.muted, fontFamily: "JetBrains Mono, monospace" }}>LAHORE · PHASE 1</div>
            <div style={{ fontSize: 10, color: C.mutedLt, fontFamily: "JetBrains Mono, monospace" }}>{ts.toLocaleTimeString("en-PK")}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", background: `${C.teal}11`, border: `1px solid ${C.teal}33`, borderRadius: 20 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.teal, animation: "blink 2s infinite" }}/>
            <span style={{ fontSize: 10, color: C.teal, fontFamily: "JetBrains Mono, monospace", fontWeight: 600 }}>LIVE</span>
          </div>
        </div>
      </header>

      {IS_SMOG && (
        <div style={{ background: `${C.flame}12`, borderBottom: `1px solid ${C.flame}30`, padding: "7px 22px", display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ color: C.flame, fontSize: 12 }}>▲</span>
          <span style={{ fontSize: 11, color: "#FFAA80" }}>CROP BURNING SEASON ACTIVE (Oct–Nov) — Elevated PM2.5 from Punjab agricultural fires. Logistics impact: HIGH. Recommend pilot operations by 5–8 AM window.</span>
        </div>
      )}

      <div style={{ padding: "16px 22px 0" }}>
        {/* City Banner */}
        <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, padding: "16px 22px", display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 60, fontWeight: 700, color: avgMeta.color, lineHeight: 1 }}>{avg}</div>
            <div>
              <div style={{ fontSize: 11, color: C.muted, marginBottom: 3 }}>City Average · Lahore · {STATIONS.length} stations</div>
              <div style={{ fontSize: 22, fontWeight: 600, color: avgMeta.color }}>{avgMeta.label}</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 22 }}>
            {[["PM2.5", `${Math.round(avg * 0.38)} µg/m³`],["PM10", `${Math.round(avg * 0.52)} µg/m³`],["NO₂", `${Math.round(avg * 0.12)} ppb`],["Visibility", avg > 200 ? "< 2 km" : avg > 150 ? "2–4 km" : "> 4 km"]].map(([l, v]) => (
              <div key={l} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 10, color: C.muted, marginBottom: 4, fontFamily: "JetBrains Mono, monospace" }}>{l}</div>
                <div style={{ fontSize: 13, fontWeight: 600, fontFamily: "JetBrains Mono, monospace", color: C.text }}>{v}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Station Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 12 }}>
          {stations.map(s => {
            const m = aqiMeta(s.aqi);
            return (
              <div key={s.id} className="sc" style={{ background: C.card, border: `1px solid ${C.border}`, borderTop: `3px solid ${m.color}`, borderRadius: 10, padding: "13px 15px" }}>
                <div style={{ fontSize: 10, color: C.muted, marginBottom: 6 }}>{s.area}</div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 30, fontWeight: 700, color: m.color, lineHeight: 1 }}>{s.aqi}</div>
                <div style={{ fontSize: 10, fontWeight: 600, color: m.color, marginTop: 4 }}>{m.label}</div>
                <div style={{ fontSize: 10, color: C.muted, marginTop: 5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.name}</div>
              </div>
            );
          })}
        </div>

        {/* Main row */}
        <div style={{ display: "grid", gridTemplateColumns: "260px 1fr 210px", gap: 10, marginBottom: 12 }}>
          {/* Map */}
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 10, color: C.muted, marginBottom: 10, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.5px" }}>STATION MAP · LAHORE</div>
            <svg width={MAP_W} height={MAP_H} style={{ borderRadius: 6, display: "block" }}>
              <rect width={MAP_W} height={MAP_H} fill="#060A12" rx="4"/>
              {[1,2,3,4].map(i => <line key={`h${i}`} x1={0} y1={i*MAP_H/5} x2={MAP_W} y2={i*MAP_H/5} stroke={C.border} strokeWidth={0.5}/>)}
              {[1,2,3,4,5].map(i => <line key={`v${i}`} x1={i*MAP_W/6} y1={0} x2={i*MAP_W/6} y2={MAP_H} stroke={C.border} strokeWidth={0.5}/>)}
              {stations.map(s => {
                const x = toX(s.lon), y = toY(s.lat), m = aqiMeta(s.aqi);
                return (
                  <g key={s.id}>
                    <circle cx={x} cy={y} r={14} fill={m.color} opacity={0.07}/>
                    <circle cx={x} cy={y} r={5} fill={m.color} opacity={0.9}/>
                    <circle cx={x} cy={y} r={2} fill="white" opacity={0.8}/>
                    <text x={x} y={y+15} textAnchor="middle" fill={C.mutedLt} fontSize={8} fontFamily="JetBrains Mono, monospace">{s.aqi}</text>
                  </g>
                );
              })}
              <text x={3} y={MAP_H-3} fill={C.border} fontSize={7} fontFamily="JetBrains Mono, monospace">73.9°E</text>
              <text x={MAP_W-28} y={MAP_H-3} fill={C.border} fontSize={7} fontFamily="JetBrains Mono, monospace">74.7°E</text>
            </svg>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
              {[["Good", C.good],["Moderate", C.moderate],["Unhealthy", C.flame],["Hazardous","#C62828"]].map(([l, c]) => (
                <div key={l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: c }}/>
                  <span style={{ fontSize: 9, color: C.muted }}>{l}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Forecast */}
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div style={{ fontSize: 10, color: C.muted, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.5px" }}>72-HOUR AQI FORECAST</div>
              <div style={{ fontSize: 9, color: C.teal, fontFamily: "JetBrains Mono, monospace" }}>XGBoost + GBM · MLflow</div>
            </div>
            <ResponsiveContainer width="100%" height={130}>
              <AreaChart data={FORECAST} margin={{ top: 5, right: 4, left: -22, bottom: 0 }}>
                <defs>
                  <linearGradient id="fg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={C.flame} stopOpacity={0.25}/>
                    <stop offset="95%" stopColor={C.flame} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false}/>
                <XAxis dataKey="i" tick={false} axisLine={false} tickLine={false}/>
                <YAxis tick={{ fill: C.muted, fontSize: 9, fontFamily: "JetBrains Mono, monospace" }} tickLine={false} axisLine={false} domain={[80, 340]}/>
                <Tooltip content={<CustomTooltip/>}/>
                <Area type="monotone" dataKey="aqi" stroke={C.flame} strokeWidth={1.5} fill="url(#fg)" dot={false} activeDot={{ r: 4, fill: C.flame }}/>
              </AreaChart>
            </ResponsiveContainer>
            {/* Timeline labels */}
            <div style={{ display: "flex", justifyContent: "space-between", padding: "0 4px", marginTop: 2 }}>
              {["Now", "+12h", "+24h", "+36h", "+48h", "+60h", "+72h"].map(l => (
                <span key={l} style={{ fontSize: 9, color: C.muted, fontFamily: "JetBrains Mono, monospace" }}>{l}</span>
              ))}
            </div>
            <div style={{ marginTop: 10, padding: "8px 12px", background: `${C.teal}0A`, borderRadius: 6, border: `1px solid ${C.teal}20`, display: "flex", gap: 10, alignItems: "center" }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.teal, flexShrink: 0 }}/>
              <div>
                <div style={{ fontSize: 9, color: C.teal, fontFamily: "JetBrains Mono, monospace", marginBottom: 2 }}>OPTIMAL DISPATCH WINDOW (NEXT 24H)</div>
                <div style={{ fontSize: 12, color: C.text }}>Hour +{BEST_WINDOW.i} · AQI <span style={{ color: aqiMeta(BEST_WINDOW.aqi).color, fontFamily: "JetBrains Mono, monospace", fontWeight: 600 }}>{BEST_WINDOW.aqi}</span> · {aqiMeta(BEST_WINDOW.aqi).label}</div>
              </div>
            </div>
          </div>

          {/* Health Risk */}
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 14 }}>
            <div style={{ fontSize: 10, color: C.muted, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.5px", marginBottom: 12 }}>DRIVER HEALTH RISK</div>
            {[
              { g: "Healthy adults", r: avg > 200 ? "HIGH" : avg > 150 ? "MODERATE" : "LOW", c: avg > 200 ? C.flame : avg > 150 ? C.moderate : C.good },
              { g: "Pre-existing conditions", r: avg > 150 ? "HIGH" : avg > 100 ? "MODERATE" : "LOW", c: avg > 150 ? C.flame : avg > 100 ? C.moderate : C.good },
              { g: "Elderly drivers", r: avg > 100 ? "HIGH" : "MODERATE", c: avg > 100 ? C.flame : C.moderate },
            ].map(r => (
              <div key={r.g} style={{ marginBottom: 10, paddingBottom: 10, borderBottom: `1px solid ${C.border}` }}>
                <div style={{ fontSize: 10, color: C.muted, marginBottom: 3 }}>{r.g}</div>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, fontWeight: 600, color: r.c }}>{r.r}</div>
              </div>
            ))}
            <div style={{ fontSize: 10, color: C.muted, marginBottom: 8, fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.4px" }}>ACTIVE MEASURES</div>
            {["N95 mask — mandatory", "Cabin recirculation ON", "Max 4h continuous exposure", "Pre/post shift lung check"].map(m => (
              <div key={m} style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: 5 }}>
                <span style={{ color: C.teal, fontSize: 10, marginTop: 1 }}>▸</span>
                <span style={{ fontSize: 10, color: C.mutedLt, lineHeight: 1.4 }}>{m}</span>
              </div>
            ))}
          </div>
        </div>

        {/* AI Decision Advisor */}
        <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 12, marginBottom: 22, overflow: "hidden" }}>
          <div style={{ padding: "12px 18px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, background: `${C.teal}15`, border: `1px solid ${C.teal}30`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>🧠</div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>Decision Advisor</div>
              <div style={{ fontSize: 10, color: C.muted }}>AI-powered logistics decision support · Live AQI context</div>
            </div>
            <div style={{ marginLeft: "auto", fontSize: 9, color: C.teal, fontFamily: "JetBrains Mono, monospace", padding: "3px 8px", background: `${C.teal}0F`, borderRadius: 4, border: `1px solid ${C.teal}25` }}>
              DECISION LAYER ACTIVE
            </div>
          </div>

          <div style={{ padding: "8px 18px 8px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 7, flexWrap: "wrap" }}>
            {QUICK.map(q => <button key={q} className="qb" onClick={() => send(q)}>{q}</button>)}
          </div>

          <div ref={chatEl} style={{ height: 210, overflowY: "auto", padding: "14px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
            {msgs.map((m, i) => (
              <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", animation: "fadeUp 0.3s ease" }}>
                <div style={{
                  maxWidth: "78%", padding: "10px 13px", borderRadius: m.role === "user" ? "12px 12px 4px 12px" : "4px 12px 12px 12px",
                  background: m.role === "user" ? `${C.teal}14` : `rgba(255,255,255,0.035)`,
                  border: `1px solid ${m.role === "user" ? C.teal + "28" : C.border}`,
                  fontSize: 13, lineHeight: 1.65, color: C.text, whiteSpace: "pre-wrap",
                }}>{m.content}</div>
              </div>
            ))}
            {busy && (
              <div style={{ display: "flex", gap: 5, padding: "8px 12px" }}>
                {[0,1,2].map(i => <div key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: C.teal, animation: `pulse 1.2s ease ${i*0.2}s infinite` }}/>)}
              </div>
            )}
          </div>

          <div style={{ padding: "10px 18px", borderTop: `1px solid ${C.border}`, display: "flex", gap: 9, height: 54, alignItems: "center" }}>
            <input className="inp" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} placeholder="Ask about routes, timing, driver safety, fleet decisions…"/>
            <button className="send" onClick={() => send()} disabled={busy} style={{ height: 36, minWidth: 72 }}>{busy ? "…" : "Ask →"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
