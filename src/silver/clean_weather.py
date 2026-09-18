import pandas as pd
import json
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("clean_weather")

def clean_weather():
    logger.info("Starting weather cleaning...")
    input_dir = Path("data/bronze/weather")
    
    if not input_dir.exists():
        logger.error(f"Directory not found: {input_dir}")
        return
        
    all_weather_data = []
    
    for json_file in input_dir.glob("weather_*.json"):
        # File name format: weather_{city}_{date}.json
        parts = json_file.stem.split("_")
        if len(parts) >= 3:
            city_name = parts[1]
        else:
            continue
            
        with open(json_file, "r") as f:
            data = json.load(f)
            
        daily = data.get("daily", {})
        if not daily:
            continue
            
        dates = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        precip_prob = daily.get("precipitation_probability_max", [])
        wind_speed = daily.get("wind_speed_10m_max", [])
        wind_gusts = daily.get("wind_gusts_10m_max", [])
        weather_code = daily.get("weather_code", [])
        
        for i in range(len(dates)):
            all_weather_data.append({
                "city_name": city_name,
                "forecast_date": dates[i],
                "temperature_max": temp_max[i] if i < len(temp_max) else None,
                "temperature_min": temp_min[i] if i < len(temp_min) else None,
                "precipitation_sum": precip[i] if i < len(precip) else None,
                "precipitation_probability": precip_prob[i] if i < len(precip_prob) else None,
                "wind_speed_max": wind_speed[i] if i < len(wind_speed) else None,
                "wind_gust_max": wind_gusts[i] if i < len(wind_gusts) else None,
                "weather_code": weather_code[i] if i < len(weather_code) else None
            })
            
    if not all_weather_data:
        logger.warning("No weather data found to clean.")
        return
        
    df = pd.DataFrame(all_weather_data)
    
    # Drop duplicates if any
    df = df.drop_duplicates(subset=["city_name", "forecast_date"])
    
    output_dir = Path("data/silver/weather")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path  =  output_dir / "weather_clean.parquet"

    df.to_parquet(output_path, engine='pyarrow')
    logger.info(f"saved {len(df)} cleaned weather records to {output_path}")


if __name__ == "__main__":
    clean_weather()
