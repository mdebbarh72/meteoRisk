import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../extract_villes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def extract_villes(csv_path):
    df = pd.read_csv(csv_path)

    duplicates = df['city'].duplicated().sum()
    if duplicates > 0:
        logger.warning(f"{duplicates} duplicate cities found")
    else:
        logger.info("No duplicate cities found")

    lat_ok = df['lat'].between(21, 36).all()
    if not lat_ok:
        logger.error("Latitude values out of expected range")
    else:
        logger.info("Latitude values OK")

    lng_ok = df['lng'].between(-17, -1).all()
    if not lng_ok:
        logger.error("Longitude values out of expected range")
    else:
        logger.info("Longitude values OK")
        
    return df


if __name__ == "__main__":
    df = extract_villes('ma.csv')
    print(df)