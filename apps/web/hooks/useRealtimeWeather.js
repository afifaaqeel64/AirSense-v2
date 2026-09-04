/**
 * AirSense Pakistan: Multi-Provider Real-Time Weather React Hook.
 * Supports auto-refresh, campus coordinate resolution, and provider failover.
 */

import { useState, useEffect } from 'react';

// WMO 4501 Weather Code Definitions for Frontend React Components
export const WMO_CODE_MAP = {
  0: { description: "Clear Sky", icon: "Sun", color: "#F59E0B" },
  1: { description: "Mainly Clear", icon: "CloudSun", color: "#64748B" },
  2: { description: "Partly Cloudy", icon: "CloudSun", color: "#64748B" },
  3: { description: "Overcast", icon: "Cloud", color: "#64748B" },
  45: { description: "Fog", icon: "CloudFog", color: "#94A3B8" },
  48: { description: "Depositing Rime Fog", icon: "CloudFog", color: "#94A3B8" },
  51: { description: "Light Drizzle", icon: "CloudDrizzle", color: "#38BDF8" },
  53: { description: "Moderate Drizzle", icon: "CloudDrizzle", color: "#38BDF8" },
  55: { description: "Dense Drizzle", icon: "CloudDrizzle", color: "#38BDF8" },
  61: { description: "Slight Rain", icon: "CloudRain", color: "#2563EB" },
  63: { description: "Moderate Rain", icon: "CloudRain", color: "#2563EB" },
  65: { description: "Heavy Rain", icon: "CloudRain", color: "#2563EB" },
  71: { description: "Slight Snow Fall", icon: "CloudSnow", color: "#E2E8F0" },
  73: { description: "Moderate Snow Fall", icon: "CloudSnow", color: "#E2E8F0" },
  75: { description: "Heavy Snow Fall", icon: "CloudSnow", color: "#E2E8F0" },
  80: { description: "Rain Showers", icon: "CloudRain", color: "#1D4ED8" },
  81: { description: "Moderate Showers", icon: "CloudRain", color: "#1D4ED8" },
  82: { description: "Violent Showers", icon: "CloudRain", color: "#1D4ED8" },
  95: { description: "Thunderstorm", icon: "CloudLightning", color: "#7C3AED" },
  96: { description: "Thunderstorm with Hail", icon: "CloudLightning", color: "#7C3AED" },
  99: { description: "Heavy Thunderstorm", icon: "CloudLightning", color: "#7C3AED" },
};

export function useRealtimeWeather(lat = 33.6844, lon = 73.0479, provider = null, refreshMs = 60000) {
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadWeather() {
      try {
        const queryParams = new URLSearchParams({
          latitude: lat,
          longitude: lon,
          ...(provider ? { provider } : {})
        });

        // Query AirSense backend unified multi-provider router
        const res = await fetch(`/api/v1/providers/weather/current?${queryParams.toString()}`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: Failed to fetch weather telemetry`);
        }
        const data = await res.json();
        
        if (isMounted) {
          setWeather(data);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadWeather();
    const interval = setInterval(loadWeather, refreshMs);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [lat, lon, provider, refreshMs]);

  return { weather, loading, error };
}
