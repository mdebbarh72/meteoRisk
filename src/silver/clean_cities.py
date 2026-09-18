import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("clean_cities")

def clean_cities():
    logger.info("Starting cities cleaning...")
    input_path = Path("data/bronze/cities/cities_raw.csv")
    
    if not input_path.exists():
        logger.error(f"File not found: {input_path}")
        return
        
    df = pd.read_csv(input_path)
    
    df = df.drop(columns=['country',  'iso2', 'admin_name', 'capital', 'population', 'population_proper'])

    # Standardize column names (if using our fallback or simplemaps)
    df = df.rename(columns={
        "city": "city_name",
        "lat": "latitude",
        "lng": "longitude"
    })

    # Ensure types
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    
    # Remove duplicates
    df = df.drop_duplicates(subset=["city_name"])
    df = df.dropna(subset=["city_name", "latitude", "longitude"])
    
    output_dir = Path("data/silver/cities")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "cities_clean.csv"
    df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(df)} cleaned cities to {output_path}")

if __name__ == "__main__":
    clean_cities()
