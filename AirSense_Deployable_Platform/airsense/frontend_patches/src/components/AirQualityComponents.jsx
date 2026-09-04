// src/components/AirQualityMap.jsx
// Drop-in Mapbox GL heatmap — reads live interpolated data from AirSense API
import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import { api } from '../services/api';
import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = process.env.REACT_APP_MAPBOX_TOKEN || '';

const LAHORE_CENTER = [74.3436, 31.5497];
const LAHORE_ZOOM   = 11;

export function AirQualityMap({ parameter = 'aqi', onStationClick }) {
  const mapRef  = useRef(null);
  const mapInst = useRef(null);
  const [activeParam, setActiveParam] = useState(parameter);

  useEffect(() => {
    mapInst.current = new mapboxgl.Map({
      container: mapRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: LAHORE_CENTER,
      zoom: LAHORE_ZOOM,
      attributionControl: false,
    });

    mapInst.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
    mapInst.current.addControl(new mapboxgl.ScaleControl());

    mapInst.current.on('load', () => loadHeatmap(activeParam));

    return () => mapInst.current?.remove();
  }, []);

  const loadHeatmap = async (param) => {
    const map = mapInst.current;
    if (!map || !map.loaded()) return;
    try {
      const geojson = await api.getHeatmap('lahore', param, 0.01);
      if (map.getSource('aqi-grid')) {
        map.getSource('aqi-grid').setData(geojson);
      } else {
        map.addSource('aqi-grid', { type: 'geojson', data: geojson });

        map.addLayer({
          id: 'aqi-heat',
          type: 'heatmap',
          source: 'aqi-grid',
          paint: {
            'heatmap-weight': ['interpolate', ['linear'], ['get', param], 0, 0, 500, 1],
            'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 10, 1, 14, 3],
            'heatmap-color': [
              'interpolate', ['linear'], ['heatmap-density'],
              0,   'rgba(0,228,0,0)',
              0.2, '#00E400',
              0.4, '#FFFF00',
              0.6, '#FF7E00',
              0.8, '#FF0000',
              1.0, '#7E0023',
            ],
            'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 10, 20, 14, 60],
            'heatmap-opacity': 0.75,
          },
        });

        // Station marker layer
        map.addSource('stations', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
        map.addLayer({
          id: 'station-markers',
          type: 'circle',
          source: 'stations',
          paint: {
            'circle-radius': 8,
            'circle-color': ['get', 'color'],
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 2,
          },
        });
        map.on('click', 'station-markers', (e) => {
          const props = e.features[0].properties;
          new mapboxgl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(`<div style="color:#111;font-family:sans-serif;padding:4px">
              <strong>${props.name}</strong><br/>
              AQI: <strong>${props.aqi || '—'}</strong><br/>
              PM2.5: ${props.pm25 ? props.pm25 + ' µg/m³' : '—'}<br/>
              <small>${props.source}</small>
            </div>`)
            .addTo(map);
          onStationClick?.(props);
        });
      }
    } catch (e) {
      console.error('Heatmap load failed:', e);
    }
  };

  // Refresh every 10 minutes
  useEffect(() => {
    const iv = setInterval(() => loadHeatmap(activeParam), 10 * 60 * 1000);
    return () => clearInterval(iv);
  }, [activeParam]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={mapRef} style={{ width: '100%', height: '100%', borderRadius: 12 }} />
      {/* Parameter switcher */}
      <div style={{
        position: 'absolute', top: 12, left: 12, background: 'rgba(0,0,0,0.75)',
        borderRadius: 8, padding: '6px 10px', display: 'flex', gap: 8,
      }}>
        {['aqi','pm25','pm10','no2'].map(p => (
          <button key={p} onClick={() => { setActiveParam(p); loadHeatmap(p); }}
            style={{
              background: activeParam === p ? '#FF6B35' : 'transparent',
              color: '#fff', border: '1px solid rgba(255,255,255,0.3)',
              borderRadius: 6, padding: '3px 10px', cursor: 'pointer',
              fontSize: 12, fontWeight: 600,
            }}>
            {p.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── AQI GAUGE COMPONENT ─────────────────────────────────────────────────────
// src/components/AQIGauge.jsx — animated SVG arc gauge

export function AQIGauge({ aqi = 0, pm25, location, lastUpdated, size = 220 }) {
  const AQI_LEVELS = [
    { max:  50, color: '#00E400', label: 'Good' },
    { max: 100, color: '#FFFF00', label: 'Moderate' },
    { max: 150, color: '#FF7E00', label: 'Unhealthy*' },
    { max: 200, color: '#FF0000', label: 'Unhealthy' },
    { max: 300, color: '#8F3F97', label: 'Very Unhealthy' },
    { max: 500, color: '#7E0023', label: 'Hazardous' },
  ];
  const level   = AQI_LEVELS.find(l => aqi <= l.max) || AQI_LEVELS[5];
  const pct     = Math.min(1, aqi / 500);
  const angle   = pct * 180 - 90; // -90 to 90 degrees

  // SVG arc helper
  const polarToCartesian = (cx, cy, r, deg) => {
    const rad = (deg - 90) * Math.PI / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };
  const describeArc = (cx, cy, r, startDeg, endDeg) => {
    const s = polarToCartesian(cx, cy, r, startDeg);
    const e = polarToCartesian(cx, cy, r, endDeg);
    const largeArc = endDeg - startDeg <= 180 ? '0' : '1';
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${largeArc} 1 ${e.x} ${e.y}`;
  };

  const cx = size / 2, cy = size * 0.55, r = size * 0.38;
  const filled = describeArc(cx, cy, r, -90, -90 + pct * 180);

  return (
    <div style={{ textAlign: 'center', fontFamily: 'sans-serif' }}>
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.65}`}>
        {/* Background arc */}
        <path d={describeArc(cx, cy, r, -90, 90)}
          fill="none" stroke="#2a2a2a" strokeWidth={size * 0.06} strokeLinecap="round"/>
        {/* Filled arc */}
        <path d={filled}
          fill="none" stroke={level.color} strokeWidth={size * 0.06} strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 8px ${level.color}80)`, transition: 'all 1.5s ease' }}/>
        {/* Needle */}
        <g style={{ transform: `rotate(${angle}deg)`, transformOrigin: `${cx}px ${cy}px`, transition: 'transform 1.5s ease' }}>
          <line x1={cx} y1={cy} x2={cx} y2={cy - r * 0.85}
            stroke="#fff" strokeWidth={2.5} strokeLinecap="round"/>
        </g>
        <circle cx={cx} cy={cy} r={size * 0.04} fill="#fff"/>
        {/* AQI value */}
        <text x={cx} y={cy - size * 0.08} textAnchor="middle"
          fill="#fff" fontSize={size * 0.16} fontWeight="700">
          {Math.round(aqi)}
        </text>
        <text x={cx} y={cy + size * 0.06} textAnchor="middle"
          fill={level.color} fontSize={size * 0.065} fontWeight="600" letterSpacing="1">
          {level.label.toUpperCase()}
        </text>
      </svg>
      <div style={{ color: '#aaa', fontSize: 13, marginTop: 4 }}>
        {location && <div style={{ color: '#fff', fontWeight: 600 }}>{location}</div>}
        {pm25 != null && <div>PM2.5: <span style={{ color: level.color }}>{parseFloat(pm25).toFixed(1)} µg/m³</span></div>}
        {lastUpdated && <div style={{ fontSize: 11, marginTop: 4 }}>Updated: {new Date(lastUpdated).toLocaleTimeString()}</div>}
      </div>
    </div>
  );
}

// ─── FORECAST CHART COMPONENT ────────────────────────────────────────────────
export function ForecastChart({ forecast, city }) {
  if (!forecast?.forecast?.length) {
    return <div style={{ color: '#666', textAlign: 'center', padding: 40 }}>Forecast loading…</div>;
  }

  const AQI_LEVELS = [
    { max:  50, color: '#00E400' },
    { max: 100, color: '#FFFF00' },
    { max: 150, color: '#FF7E00' },
    { max: 200, color: '#FF0000' },
    { max: 300, color: '#8F3F97' },
    { max: 500, color: '#7E0023' },
  ];
  const getColor = (aqi) => (AQI_LEVELS.find(l => aqi <= l.max) || AQI_LEVELS[5]).color;

  const points = forecast.forecast.filter(f => f.predicted_aqi != null);
  const maxAQI = Math.max(...points.map(p => p.predicted_aqi), 200);
  const W = 600, H = 180, PAD = 40;
  const xScale = (i) => PAD + (i / (points.length - 1)) * (W - PAD * 2);
  const yScale = (v) => H - PAD - (v / maxAQI) * (H - PAD * 2);

  const pathD = points.map((p, i) =>
    `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.predicted_aqi)}`
  ).join(' ');

  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ color: '#fff', fontWeight: 700, marginBottom: 12 }}>
        {city ? city.charAt(0).toUpperCase() + city.slice(1) : 'Lahore'} — {points.length}h Forecast
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', minWidth: 300 }}>
        {/* Grid lines */}
        {[50, 100, 150, 200].map(v => (
          <g key={v}>
            <line x1={PAD} y1={yScale(v)} x2={W - PAD} y2={yScale(v)}
              stroke="#333" strokeWidth={0.5} strokeDasharray="4"/>
            <text x={PAD - 4} y={yScale(v) + 4} fill="#555" fontSize={9} textAnchor="end">{v}</text>
          </g>
        ))}
        {/* Area fill */}
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FF6B35" stopOpacity="0.3"/>
            <stop offset="100%" stopColor="#FF6B35" stopOpacity="0"/>
          </linearGradient>
        </defs>
        <path d={`${pathD} L ${xScale(points.length-1)} ${H-PAD} L ${xScale(0)} ${H-PAD} Z`}
          fill="url(#areaGrad)"/>
        {/* Line */}
        <path d={pathD} fill="none" stroke="#FF6B35" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round"/>
        {/* Dots */}
        {points.filter((_, i) => i % 4 === 0).map((p, i) => {
          const realIdx = i * 4;
          return (
            <g key={i}>
              <circle cx={xScale(realIdx)} cy={yScale(p.predicted_aqi)} r={4}
                fill={getColor(p.predicted_aqi)} stroke="#fff" strokeWidth={1.5}/>
              <text x={xScale(realIdx)} y={H - PAD + 14}
                fill="#666" fontSize={8} textAnchor="middle">
                {new Date(p.prediction_for).getHours()}h
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ─── STATION TABLE COMPONENT ─────────────────────────────────────────────────
export function StationTable({ stations = [] }) {
  const AQI_LEVELS = [
    { max:50,color:'#00E400'},{max:100,color:'#FFFF00'},{max:150,color:'#FF7E00'},
    {max:200,color:'#FF0000'},{max:300,color:'#8F3F97'},{max:500,color:'#7E0023'},
  ];
  const getColor = (aqi) => (AQI_LEVELS.find(l => aqi <= l.max) || AQI_LEVELS[5]).color;

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width:'100%', borderCollapse:'collapse', color:'#fff', fontSize:13 }}>
        <thead>
          <tr style={{ borderBottom:'1px solid #333' }}>
            {['Station','AQI','PM2.5','PM10','Temp','Humidity','Source'].map(h => (
              <th key={h} style={{ padding:'8px 12px', textAlign:'left', color:'#888', fontWeight:500 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stations.map((s, i) => (
            <tr key={i} style={{ borderBottom:'1px solid #1a1a1a',
              background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
              <td style={{ padding:'8px 12px', fontWeight:600 }}>{s.station_id?.replace('lahore_','').replace(/_/g,' ')}</td>
              <td style={{ padding:'8px 12px' }}>
                {s.aqi != null
                  ? <span style={{ color: getColor(s.aqi), fontWeight:700, fontSize:15 }}>{Math.round(s.aqi)}</span>
                  : '—'}
              </td>
              <td style={{ padding:'8px 12px' }}>{s.pm25 != null ? `${parseFloat(s.pm25).toFixed(1)}` : '—'}</td>
              <td style={{ padding:'8px 12px' }}>{s.pm10 != null ? `${parseFloat(s.pm10).toFixed(1)}` : '—'}</td>
              <td style={{ padding:'8px 12px' }}>{s.temperature != null ? `${Math.round(s.temperature)}°C` : '—'}</td>
              <td style={{ padding:'8px 12px' }}>{s.humidity != null ? `${Math.round(s.humidity)}%` : '—'}</td>
              <td style={{ padding:'8px 12px', color:'#555', fontSize:11 }}>{s.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
