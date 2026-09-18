import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger("create_features")

def categorize_temperature(temp, thresholds):
    if pd.isna(temp):
        return "Unknown"
    if temp < thresholds.get("cold", 10):
        return "Very Cold"
    elif temp < thresholds.get("normal", 20): # Adjusted default
        return "Cold"
    elif temp < thresholds.get("hot", 30):
        return "Normal"
    elif temp < 35:
        return "Hot"
    else:
        return "Extreme Heat"

def categorize_precipitation(precip, thresholds):
    if pd.isna(precip):
        return "Unknown"
    if precip == 0:
        return "None"
    elif precip < thresholds.get("light", 2.5):
        return "Light"
    elif precip < thresholds.get("moderate", 10):
        return "Moderate"
    elif precip < thresholds.get("heavy", 25):
        return "Heavy"
    else:
        return "Very Heavy"

def categorize_wind(wind, thresholds):
    if pd.isna(wind):
        return "Unknown"
    if wind < thresholds.get("moderate", 20):
        return "Calm"
    elif wind < thresholds.get("strong", 40):
        return "Moderate"
    elif wind < thresholds.get("dangerous", 60):
        return "Strong"
    else:
        return "Dangerous"

def normalize(val, max_val):
    if pd.isna(val):
        return 0
    return min(100, max(0, (val / max_val) * 100))

def create_features():
    logger.info("Starting Gold layer feature creation...")
    config = load_config()
    
    cities_path = Path("data/silver/cities/cities_clean.csv")
    weather_path = Path("data/silver/weather/weather_clean.parquet")
    
    if not cities_path.exists() or not weather_path.exists():
        logger.error("Silver datasets not found.")
        return
        
    df_cities = pd.read_csv(cities_path)
    df_weather = pd.read_parquet(weather_path)
    
    # Join
    df = pd.merge(df_weather, df_cities, on="city_name", how="left")
    
    thresh_temp = config.get("thresholds", {}).get("temperature", {})
    thresh_precip = config.get("thresholds", {}).get("precipitation", {})
    thresh_wind = config.get("thresholds", {}).get("wind", {})
    
    # Categories
    df["temperature_category"] = df["temperature_max"].apply(lambda x: categorize_temperature(x, thresh_temp))
    df["precipitation_category"] = df["precipitation_sum"].apply(lambda x: categorize_precipitation(x, thresh_precip))
    df["wind_category"] = df["wind_speed_max"].apply(lambda x: categorize_wind(x, thresh_wind))
    
    def calc_temp_risk(temp):
        if pd.isna(temp): return 0
        if temp >= 35: return 100
        elif temp >= 30: return 50
        elif temp <= 10: return 50
        elif temp <= 5: return 100
        else: return 0
        
    df["temp_risk"] = df["temperature_max"].apply(calc_temp_risk)
    df["precip_risk"] = df["precipitation_sum"].apply(lambda x: normalize(x, 25))
    df["prob_risk"] = df["precipitation_probability"].fillna(0)
    df["wind_risk"] = df["wind_speed_max"].apply(lambda x: normalize(x, 60))
    df["code_risk"] = 0 
    
    weights = config.get("risk", {})
    w_temp = weights.get("temperature_weight", 0.20)
    w_precip = weights.get("precipitation_weight", 0.35)
    w_prob = weights.get("rain_probability_weight", 0.15)
    w_wind = weights.get("wind_weight", 0.20)
    w_code = weights.get("weather_code_weight", 0.10)
    
    df["risk_score"] = (
        df["temp_risk"] * w_temp +
        df["precip_risk"] * w_precip +
        df["prob_risk"] * w_prob +
        df["wind_risk"] * w_wind +
        df["code_risk"] * w_code
    )
    df["risk_score"] = df["risk_score"].round(2)
    
    def get_risk_level(score):
        if pd.isna(score): return "Unknown"
        if score < 25: return "Low"
        elif score < 50: return "Moderate"
        elif score < 75: return "High"
        else: return "Critical"
        
    df["risk_level"] = df["risk_score"].apply(get_risk_level)
    
    df = df.drop(columns=["temp_risk", "precip_risk", "prob_risk", "wind_risk", "code_risk"])
    
    # 1. Save Weather Risk Forecast to Parquet
    output_dir_risk = Path("data/gold/weather_risk")
    output_dir_risk.mkdir(parents=True, exist_ok=True)
    output_path_risk = output_dir_risk / "weather_risk.parquet"
    df.to_parquet(output_path_risk, index=False)
    logger.info(f"Saved {len(df)} gold forecast records to {output_path_risk}")
    
    # 2. Save Cities to Parquet
    df_gold_cities = df[['city_name', 'latitude', 'longitude']].drop_duplicates()
    output_dir_cities = Path("data/gold/cities")
    output_dir_cities.mkdir(parents=True, exist_ok=True)
    output_path_cities = output_dir_cities / "cities.parquet"
    df_gold_cities.to_parquet(output_path_cities, index=False)
    logger.info(f"Saved {len(df_gold_cities)} gold city records to {output_path_cities}")

if __name__ == "__main__":
    create_features()
