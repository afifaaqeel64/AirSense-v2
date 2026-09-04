// AirSense React Hooks — drop into src/hooks/useAQI.js
import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';

/** Live AQI via WebSocket with exponential-backoff reconnect + HTTP fallback */
export function useLiveAQI(city = 'lahore') {
  const [data, setData]           = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef    = useRef(null);
  const retryRef = useRef(0);
  const timerRef = useRef(null);

  const connect = useCallback(() => {
    try {
      wsRef.current = new WebSocket(api.wsUrl(city));
      wsRef.current.onopen    = () => { setConnected(true); setError(null); retryRef.current = 0; };
      wsRef.current.onmessage = (e) => { setData(JSON.parse(e.data)); setLoading(false); };
      wsRef.current.onclose   = () => {
        setConnected(false);
        const delay = Math.min(30000, 1000 * Math.pow(2, retryRef.current++));
        timerRef.current = setTimeout(connect, delay);
      };
      wsRef.current.onerror = () => setError('Live connection unavailable — polling fallback active');
    } catch (e) {
      setError('WebSocket unavailable');
    }
  }, [city]);

  useEffect(() => {
    // Immediate HTTP fetch
    api.getCurrentAQI(city).then(d => { setData(d); setLoading(false); }).catch(() => {});
    // WebSocket
    connect();
    // Poll every 60s when WS is down
    const poll = setInterval(() => {
      if (!connected) api.getCurrentAQI(city).then(setData).catch(() => {});
    }, 60000);
    return () => {
      clearInterval(poll);
      clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [city, connect, connected]);

  return { data, loading, error, connected };
}

/** 24h / 48h / 72h forecast */
export function useForecast(city = 'lahore', hours = 24) {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading]   = useState(true);
  useEffect(() => {
    api.getForecast(city, hours)
      .then(d => { setForecast(d); setLoading(false); })
      .catch(() => setLoading(false));
    const iv = setInterval(
      () => api.getForecast(city, hours).then(setForecast).catch(() => {}),
      30 * 60 * 1000 // refresh every 30 min
    );
    return () => clearInterval(iv);
  }, [city, hours]);
  return { forecast, loading };
}

/** Historical time-series */
export function useHistorical(city, start, end, parameter = 'aqi', aggregation = 'hourly') {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!start || !end) return;
    setLoading(true);
    api.getHistorical(city, start, end, parameter, aggregation)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [city, start, end, parameter, aggregation]);
  return { data, loading };
}

/** Health risk assessment */
export function useHealthRisk(city = 'lahore', sensitive = false) {
  const [risk, setRisk]       = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.getHealthRisk(city, sensitive).then(r => { setRisk(r); setLoading(false); });
    const iv = setInterval(
      () => api.getHealthRisk(city, sensitive).then(setRisk).catch(() => {}),
      5 * 60 * 1000
    );
    return () => clearInterval(iv);
  }, [city, sensitive]);
  return { risk, loading };
}

/** Station list */
export function useStations(city = 'lahore') {
  const [stations, setStations] = useState([]);
  const [loading, setLoading]   = useState(true);
  useEffect(() => {
    api.getStations(city)
      .then(d => { setStations(d.stations || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [city]);
  return { stations, loading };
}
