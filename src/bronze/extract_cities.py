import pandas as pd
import requests
import io
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("extract_cities")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def fetchFromSite() -> pd.DataFrame:
    url = "https://simplemaps.com/static/data/country-cities/ma/ma.csv"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    return df

def fetchFromFile() -> pd.DataFrame:
    file_path = PROJECT_ROOT / "fallbackData" / "ma.csv"
    return pd.read_csv(file_path)

def extract_cities():
    logger.info("Starting cities extraction...")
    cities_df = None
    last_error = None

    for method in [fetchFromSite, fetchFromFile]:
        try:
            cities_df = method()
            logger.info(f"Successfully loaded {len(cities_df)} cities via {method.__name__}.")
            break
        except Exception as e:
            last_error = e
            logger.warning(f"{method.__name__} failed to get cities data: {e}")

    if cities_df is None:
        raise RuntimeError("Failed to load cities data from all sources") from last_error

    output_dir = PROJECT_ROOT / "data" / "bronze" / "cities"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "cities_raw.csv"
    cities_df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(cities_df)} cities to {output_path}")

if __name__ == "__main__":
    extract_cities()
