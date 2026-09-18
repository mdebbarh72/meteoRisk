import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# Add project root to path so we can import src modules
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.database.connection import get_engine
from sql.migration import City, WeatherForecast, create_tables
from src.utils.logger import get_logger

logger = get_logger("database_loader")

def load_to_postgres():
    """Load Gold layer data into PostgreSQL database."""
    logger.info("Starting database load process...")

    engine = get_engine()
    create_tables(engine)   # ensure schema exists before any insert
    
    gold_path = Path("data/gold/weather_risk/weather_risk.parquet")
    if not gold_path.exists():
        logger.error(f"Gold forecast data not found at {gold_path}")
        return
        
    df = pd.read_parquet(gold_path)
    # Convert dates to datetime
    df['forecast_date'] = pd.to_datetime(df['forecast_date']).dt.tz_localize('UTC')
    
    # Handle NaNs: SQLAlchemy doesn't like pandas/numpy NaNs, it prefers None
    df = df.replace({np.nan: None})
    
    with Session(engine) as session:
        try:
            # 1. Upsert Cities
            unique_cities = df[['city_name', 'latitude', 'longitude']].drop_duplicates()
            city_name_to_id = {}
            
            for _, row in unique_cities.iterrows():
                # Try to find city by name
                city = session.query(City).filter_by(name=row['city_name']).first()
                if not city:
                    city = City(
                        name=row['city_name'],
                        latitude=row['latitude'],
                        longitude=row['longitude']
                    )
                    session.add(city)
                    session.flush() # flush to get the ID
                city_name_to_id[row['city_name']] = city.id
                
            # 2. Insert Weather Forecasts
            forecasts_to_insert = []
            for _, row in df.iterrows():
                city_id = city_name_to_id[row['city_name']]
                
                # Check for existing forecast for this city and date to avoid constraint violation
                # The unique constraint is on (city_id, forecast_date, forecast_run_date)
                # For simplicity, we just add the new run
                
                forecast = WeatherForecast(
                    city_id=city_id,
                    forecast_date=row['forecast_date'],
                    temperature_max=row['temperature_max'],
                    temperature_min=row.get('temperature_min'),
                    precipitation_sum=row['precipitation_sum'],
                    precipitation_probability=row.get('precipitation_probability'),
                    wind_speed_max=row['wind_speed_max'],
                    wind_gust_max=row.get('wind_gust_max'),
                    weather_code=row.get('weather_code'),
                    temperature_category=row.get('temperature_category'),
                    precipitation_category=row.get('precipitation_category'),
                    wind_category=row.get('wind_category'),
                    risk_score=row['risk_score'],
                    risk_level=row['risk_level']
                )
                forecasts_to_insert.append(forecast)
                
            session.add_all(forecasts_to_insert)
            session.commit()
            logger.info(f"Successfully loaded {len(unique_cities)} cities and {len(forecasts_to_insert)} forecasts.")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error loading to database: {e}")
            raise

if __name__ == "__main__":
    load_to_postgres()
