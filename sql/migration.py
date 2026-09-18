from sqlalchemy import (
    Column,
    Integer, BigInteger, String, Numeric, Float,
    Date, DateTime, Text, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False, unique=True)
    latitude = Column(Numeric(8, 5), nullable=False)
    longitude = Column(Numeric(8, 5), nullable=False)

    forecasts = relationship("WeatherForecast", back_populates="city")


class WeatherForecast(Base):
    __tablename__ = "weather_forecast"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    city_id = Column(Integer, ForeignKey("cities.id", ondelete="CASCADE"), nullable=False)
    forecast_date = Column(DateTime(timezone=True), nullable=False)

    temperature_max = Column(Numeric(5, 2))
    temperature_min = Column(Numeric(5, 2))
    precipitation_sum = Column(Numeric(7, 2))
    precipitation_probability = Column(Integer)
    wind_speed_max = Column(Numeric(7, 2))
    wind_gust_max = Column(Numeric(7, 2))
    weather_code = Column(Integer)

    temperature_category = Column(String(30))
    precipitation_category = Column(String(30))
    wind_category = Column(String(30))

    risk_score = Column(Numeric(5, 2))
    risk_level = Column(String(20))

    forecast_run_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    city = relationship("City", back_populates="forecasts")

    __table_args__ = (
        UniqueConstraint("city_id", "forecast_date", name="uq_city_forecast_date"),
        CheckConstraint("precipitation_sum >= 0", name="ck_precipitation_positive"),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_risk_score_range"),
    )


def create_tables(engine):
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.database.connection import get_engine
    eng = get_engine()
    create_tables(eng)
    print("Tables created successfully.")
