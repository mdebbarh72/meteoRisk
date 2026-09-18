import pandas as pd
import requests
import json
from datetime import datetime
from pathlib import Path
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger("extract_weather")

def extract_weather():
    logger.info("Starting weather extraction...")
    config = load_config()
    forecast_days = config.get("weather", {}).get("forecast_days", 7)
    timezone = config.get("weather", {}).get("timezone", "Africa/Casablanca")
    
    cities_path = Path("data/bronze/cities/cities_raw.csv")
    if not cities_path.exists():
        logger.error(f"Cities file {cities_path} does not exist.")
        return
        
    df_cities = pd.read_csv(cities_path)
    output_dir = Path("data/bronze/weather")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    url = "https://api.open-meteo.com/v1/forecast"
    
    for _, row in df_cities.iterrows():
        city_name = row.get("city", "Unknown")
        lat = row.get("lat")
        lon = row.get("lng")
        
        if pd.isna(lat) or pd.isna(lon):
            logger.warning(f"Skipping {city_name} due to missing coordinates.")
            continue
            
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
                "weather_code"
            ],
            "forecast_days": forecast_days,
            "timezone": timezone
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            output_file = output_dir / f"weather_{city_name}_{today_str}.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=4)
                
            logger.info(f"Saved weather data for {city_name}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get weather for {city_name}: {e}")

if __name__ == "__main__": 
    extract_weather()
