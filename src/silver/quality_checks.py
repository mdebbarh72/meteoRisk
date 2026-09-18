import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("quality_checks")

def run_quality_checks():
    logger.info("Starting data quality checks...")
    
    cities_path = Path("data/silver/cities/cities_clean.csv")
    weather_path = Path("data/silver/weather/weather_clean.parquet")
    
    if not cities_path.exists() or not weather_path.exists():
        logger.error("Silver datasets not found. Cannot run quality checks.")
        return
        
    df_cities = pd.read_csv(cities_path)
    df_weather = pd.read_parquet(weather_path)
    
    # Checks on cities
    assert df_cities["city_name"].notna().all(), "Cities contain null city_name"
    assert df_cities["latitude"].between(-90, 90).all(), "Invalid latitudes found"
    assert df_cities["longitude"].between(-180, 180).all(), "Invalid longitudes found"
    
    # Checks on weather
    assert df_weather["city_name"].notna().all(), "Weather contains null city_name"
    assert df_weather["forecast_date"].notna().all(), "Weather contains null dates"
    
    if "temperature_max" in df_weather.columns:
        assert df_weather["temperature_max"].between(-50, 60).all(), "Unrealistic temperatures found"
        
    if "precipitation_sum" in df_weather.columns:
        assert (df_weather["precipitation_sum"].dropna() >= 0).all(), "Negative precipitation found"
        
    if "precipitation_probability" in df_weather.columns:
        assert df_weather["precipitation_probability"].dropna().between(0, 100).all(), "Invalid probability"
        
    duplicates = df_weather.duplicated(subset=["city_name", "forecast_date"]).sum()
    assert duplicates == 0, f"Found {duplicates} duplicate forecasts"
    
    logger.info("All quality checks passed successfully!")

if __name__ == "__main__":
    run_quality_checks()