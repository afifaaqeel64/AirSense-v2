// AirSense API Service Layer — drop into src/services/api.js
const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WS   = process.env.REACT_APP_WS_URL  || 'ws://localhost:8000';

const req = async (path, opts = {}) => {
  const token = localStorage.getItem('airsense_token');
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opts.headers,
    },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
};

export const api = {
  // AQI endpoints
  getCurrentAQI: (city = 'lahore', station = null) =>
    req(`/api/v1/aqi/current/${city}${station ? `?station=${station}` : ''}`),
  getHeatmap: (city, param = 'aqi', res = 0.01) =>
    req(`/api/v1/aqi/heatmap/${city}?parameter=${param}&resolution=${res}`),
  getForecast: (city, hours = 24) =>
    req(`/api/v1/aqi/forecast/${city}?hours=${hours}`),
  getHistorical: (city, start, end, param = 'aqi', agg = 'hourly') =>
    req(`/api/v1/aqi/historical/${city}?start_date=${start}&end_date=${end}&parameter=${param}&aggregation=${agg}`),
  getHealthRisk: (city, sensitive = false) =>
    req(`/api/v1/aqi/health/${city}?sensitive=${sensitive}`),
  getCompare: (cities, param = 'aqi', days = 7) =>
    req(`/api/v1/aqi/compare?cities=${cities.join(',')}&parameter=${param}&days=${days}`),
  getStations: (city) => req(`/api/v1/stations/${city}`),

  // Auth
  login: (email, password) =>
    req('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (data) =>
    req('/api/v1/auth/register', { method: 'POST', body: JSON.stringify(data) }),

  // WebSocket URL
  wsUrl: (city) => `${WS}/api/v1/aqi/live/${city}`,
};

export default api;
