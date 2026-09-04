// src/utils/aqi.js
export const AQI_LEVELS = [
  { max:  50, label: 'Good',                  color: '#00E400', bg: '#0a2e0a', emoji: '🟢' },
  { max: 100, label: 'Moderate',              color: '#FFFF00', bg: '#2e2e0a', emoji: '🟡' },
  { max: 150, label: 'Unhealthy (Sensitive)', color: '#FF7E00', bg: '#2e1a0a', emoji: '🟠' },
  { max: 200, label: 'Unhealthy',             color: '#FF0000', bg: '#2e0a0a', emoji: '🔴' },
  { max: 300, label: 'Very Unhealthy',        color: '#8F3F97', bg: '#1e0a2e', emoji: '🟣' },
  { max: 500, label: 'Hazardous',             color: '#7E0023', bg: '#2e0010', emoji: '⚫' },
];
export const getAQILevel  = (aqi) => AQI_LEVELS.find(l => aqi <= l.max) || AQI_LEVELS[5];
export const aqiToPercent = (aqi) => Math.min(100, (aqi / 500) * 100);
export const formatPM25   = (v)   => v == null ? '—' : `${parseFloat(v).toFixed(1)} µg/m³`;
export const formatAQI    = (v)   => v == null ? '—' : Math.round(v).toString();
export const pm25VsWHO    = (v)   => v != null && v > 15;
