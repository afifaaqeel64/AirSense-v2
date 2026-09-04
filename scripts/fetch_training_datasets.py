"""
AirSense Pakistan — Historical PM2.5 and Meteorological Data Retrieval Script.
Fetches multi-year hourly air quality and meteorological reanalysis datasets for
Islamabad, Karachi, and Lahore, merges pollutant & weather drivers, and saves
clean CSVs ready for ML model training and database ingestion.
"""

import os
import json
import urllib.request
import urllib.parse
import pandas as pd
import numpy as np
from pathlib import Path

AIRSENSE_ROOT = str(Path(__file__).resolve().parent.parent)
DATA_DIR = os.path.join(AIRSENSE_ROOT, "data", "datasets")
os.makedirs(DATA_DIR, exist_ok=True)

CITIES = {
    "islamabad": {
        "name": "Islamabad",
        "campus_code": "ISB_CAMPUS",
        "station_code": "ISB-CAMPUS-01",
        "lat": 33.6844,
        "lon": 73.0479,
        "timezone": "Asia/Karachi"
    },
    "karachi": {
        "name": "Karachi",
        "campus_code": "KHI_CAMPUS",
        "station_code": "KHI-CAMPUS-01",
        "lat": 24.8607,
        "lon": 67.0011,
        "timezone": "Asia/Karachi"
    },
    "lahore": {
        "name": "Lahore",
        "campus_code": "LHR_CAMPUS",
        "station_code": "LHR-SMOG-01",
        "lat": 31.5204,
        "lon": 74.3587,
        "timezone": "Asia/Karachi"
    }
}

START_DATE = "2023-01-01"
END_DATE = "2026-08-01"

def fetch_air_quality_hourly(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch hourly PM2.5, PM10, CO, NO2, SO2, O3, and dust from Open-Meteo Air Quality API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,dust",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "UTC"
    }
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{urllib.parse.urlencode(params)}"
    print(f"Fetching Air Quality from: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "AirSense-Dataset-Downloader/1.0"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
    
    hourly = data.get("hourly", {})
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df

def fetch_weather_hourly(lat: float, lon: float, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch hourly temperature, humidity, pressure, wind, rain, and boundary layer height from Open-Meteo Historical Archive."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,precipitation,wind_speed_10m,wind_direction_10m,boundary_layer_height",
        "timezone": "UTC"
    }
    url = f"https://archive-api.open-meteo.com/v1/archive?{urllib.parse.urlencode(params)}"
    print(f"Fetching Weather Drivers from: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "AirSense-Dataset-Downloader/1.0"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
        
    hourly = data.get("hourly", {})
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df

def compute_aqi_us_epa(pm25: float) -> int:
    """Calculate US EPA AQI from PM2.5 concentration in ug/m3."""
    if pd.isna(pm25) or pm25 < 0:
        return 0
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if bp_lo <= pm25 <= bp_hi:
            return int(((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo)
    return 500

def process_city_dataset(city_key: str, city_meta: dict) -> pd.DataFrame:
    print(f"\nProcessing {city_meta['name']} ({city_key})...")
    df_aq = fetch_air_quality_hourly(city_meta["lat"], city_meta["lon"], START_DATE, END_DATE)
    df_wx = fetch_weather_hourly(city_meta["lat"], city_meta["lon"], START_DATE, END_DATE)
    
    merged = pd.merge(df_aq, df_wx, on="time", how="inner")
    
    # Map to AirSense canonical schema
    merged["city"] = city_key
    merged["city_name"] = city_meta["name"]
    merged["campus_code"] = city_meta["campus_code"]
    merged["station_code"] = city_meta["station_code"]
    merged["latitude"] = city_meta["lat"]
    merged["longitude"] = city_meta["lon"]
    
    merged.rename(columns={
        "time": "hour_start",
        "pm2_5": "pm2_5_mean",
        "pm10": "pm10_mean",
        "temperature_2m": "temperature_mean",
        "relative_humidity_2m": "humidity_mean",
        "surface_pressure": "pressure_mean",
        "wind_speed_10m": "wind_speed_mean",
        "wind_direction_10m": "wind_direction_circular_mean",
        "precipitation": "precipitation_mm"
    }, inplace=True)
    
    # Derived variables
    merged["pm1_mean"] = merged["pm2_5_mean"] * 0.7  # standard PM1 approximation when unmeasured
    merged["pm2_5_median"] = merged["pm2_5_mean"]
    merged["pm10_median"] = merged["pm10_mean"]
    merged["rain_detected"] = (merged["precipitation_mm"] > 0.05).astype(int)
    merged["rain_fraction"] = np.where(merged["precipitation_mm"] > 0, 1.0, 0.0)
    
    # Directional trigonometry
    rad = np.radians(merged["wind_direction_circular_mean"].fillna(0.0))
    merged["wind_dir_sin"] = np.sin(rad)
    merged["wind_dir_cos"] = np.cos(rad)
    
    # Quality & Eligibility
    merged["average_quality_score"] = 1.0
    merged["high_humidity_fraction"] = (merged["humidity_mean"] > 85.0).astype(float)
    merged["has_interpolation"] = 0
    merged["completeness_pct"] = 100.0
    merged["is_model_eligible"] = (~merged["pm2_5_mean"].isna() & ~merged["temperature_mean"].isna()).astype(int)
    
    # US EPA AQI
    merged["aqi"] = merged["pm2_5_mean"].apply(compute_aqi_us_epa)
    
    # Save city CSV
    out_csv = os.path.join(DATA_DIR, f"{city_key}_pm25_meteorological_hourly_2023_2026.csv")
    merged.to_csv(out_csv, index=False)
    print(f"Saved {len(merged)} records to {out_csv}")
    
    return merged

def main():
    all_dfs = []
    for c_key, c_meta in CITIES.items():
        df_c = process_city_dataset(c_key, c_meta)
        all_dfs.append(df_c)
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_csv = os.path.join(DATA_DIR, "pakistan_multicity_pm25_meteorological_combined.csv")
    combined_df.to_csv(combined_csv, index=False)
    print(f"\nSaved combined multi-city dataset with {len(combined_df)} rows to {combined_csv}")
    
    # Print summary statistics
    print("\n=== Dataset Summary Statistics ===")
    for city, group in combined_df.groupby("city"):
        print(f"\n--- {city.upper()} ---")
        print(f"Total Hours: {len(group)}")
        print(f"Date Range: {group['hour_start'].min()} to {group['hour_start'].max()}")
        print(f"PM2.5 Mean: {group['pm2_5_mean'].mean():.2f} ug/m3 (Min: {group['pm2_5_mean'].min():.2f}, Max: {group['pm2_5_mean'].max():.2f})")
        print(f"Temp Mean: {group['temperature_mean'].mean():.2f} C")
        print(f"Humidity Mean: {group['humidity_mean'].mean():.2f} %")
        print(f"Pressure Mean: {group['pressure_mean'].mean():.2f} hPa")
        print(f"Wind Speed Mean: {group['wind_speed_mean'].mean():.2f} m/s")

if __name__ == "__main__":
    main()
