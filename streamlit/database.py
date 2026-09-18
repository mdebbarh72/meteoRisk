import os
from sqlalchemy import create_engine
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_engine():
    """Create and return a SQLAlchemy engine for PostgreSQL."""
    url = f"postgresql+psycopg2://{os.getenv('DB_USER', 'weather_user')}:{os.getenv('DB_PWD', 'weather_password')}@{os.getenv('DB_HOST', 'postgres')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'weather_db')}"

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
        return create_engine(db_url)
        
    return create_engine(url)

def fetch_data(query: str) -> pd.DataFrame:
    """Fetch data from the database using a SQL query."""
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df
