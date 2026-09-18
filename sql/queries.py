

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, cast, func, Numeric
from sqlalchemy.orm import Session


import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sql.migration import City, WeatherForecast


def _rows_to_dicts(rows) -> list[dict[str, Any]]:
    """Convert SQLAlchemy Row objects to plain dicts (keys are column labels)."""
    return [row._asdict() for row in rows]



def cities_with_highest_avg_temperature(session: Session, limit: int = 10) -> list[dict]:
    """
    Business question: Quelles villes auront les températures les plus élevées ?

    Returns cities ranked by their average maximum temperature (descending).
    """
    rows = (
        session.query(
            City.name.label("city"),
            func.avg(WeatherForecast.temperature_max).label("avg_temperature_max"),
            func.max(WeatherForecast.temperature_max).label("peak_temperature_max"),
        )
        .join(WeatherForecast, WeatherForecast.city_id == City.id)
        .filter(WeatherForecast.temperature_max.isnot(None))
        .group_by(City.id, City.name)
        .order_by(func.avg(WeatherForecast.temperature_max).desc())
        .limit(limit)
        .all()
    )
    return _rows_to_dicts(rows)



def cities_with_highest_precipitation(session: Session, limit: int = 10) -> list[dict]:

    rows = (
        session.query(
            City.name.label("city"),
            func.sum(WeatherForecast.precipitation_sum).label("total_precipitation_mm"),
            func.avg(WeatherForecast.precipitation_sum).label("avg_daily_precipitation_mm"),
            func.max(WeatherForecast.precipitation_sum).label("max_single_day_precipitation_mm"),
        )
        .join(WeatherForecast, WeatherForecast.city_id == City.id)
        .filter(WeatherForecast.precipitation_sum.isnot(None))
        .group_by(City.id, City.name)
        .order_by(func.sum(WeatherForecast.precipitation_sum).desc())
        .limit(limit)
        .all()
    )
    return _rows_to_dicts(rows)



def cities_with_highest_avg_risk(session: Session, limit: int = 10) -> list[dict]:
    """
    Business question: Quelles villes présentent le risque moyen le plus élevé ?

    Returns cities ranked by their average composite risk score (descending).
    """
    rows = (
        session.query(
            City.name.label("city"),
            func.avg(cast(WeatherForecast.risk_score, Float)).label("avg_risk_score"),
            func.max(cast(WeatherForecast.risk_score, Float)).label("max_risk_score"),
            func.min(cast(WeatherForecast.risk_score, Float)).label("min_risk_score"),
        )
        .join(WeatherForecast, WeatherForecast.city_id == City.id)
        .filter(WeatherForecast.risk_score.isnot(None))
        .group_by(City.id, City.name)
        .order_by(func.avg(cast(WeatherForecast.risk_score, Float)).desc())
        .limit(limit)
        .all()
    )
    return _rows_to_dicts(rows)


def periods_with_max_risk(session: Session, limit: int = 10) -> list[dict]:
    """
    Business question: Quelles périodes présentent le risque maximal ?

    Returns the (city, date) combinations that carry the highest risk score,
    ordered from the most dangerous to the least.
    """
    rows = (
        session.query(
            WeatherForecast.forecast_date.label("forecast_date"),
            City.name.label("city"),
            WeatherForecast.risk_score.label("risk_score"),
            WeatherForecast.risk_level.label("risk_level"),
            WeatherForecast.temperature_max.label("temperature_max"),
            WeatherForecast.precipitation_sum.label("precipitation_sum"),
        )
        .join(City, WeatherForecast.city_id == City.id)
        .filter(WeatherForecast.risk_score.isnot(None))
        .order_by(cast(WeatherForecast.risk_score, Float).desc())
        .limit(limit)
        .all()
    )
    return _rows_to_dicts(rows)


def riskiest_period_per_city(session: Session) -> list[dict]:
    """
    Business question: Pour chaque ville, quelle période présente le plus grand risque ?

    Uses a correlated subquery to find, for each city, the single row with
    the maximum risk_score.
    """
    # Subquery: max risk_score per city
    subq = (
        session.query(
            WeatherForecast.city_id,
            func.max(cast(WeatherForecast.risk_score, Float)).label("max_risk"),
        )
        .filter(WeatherForecast.risk_score.isnot(None))
        .group_by(WeatherForecast.city_id)
        .subquery()
    )

    rows = (
        session.query(
            City.name.label("city"),
            WeatherForecast.forecast_date.label("riskiest_date"),
            WeatherForecast.risk_score.label("risk_score"),
            WeatherForecast.risk_level.label("risk_level"),
            WeatherForecast.temperature_max.label("temperature_max"),
            WeatherForecast.precipitation_sum.label("precipitation_sum"),
            WeatherForecast.wind_speed_max.label("wind_speed_max"),
        )
        .join(City, WeatherForecast.city_id == City.id)
        .join(
            subq,
            (WeatherForecast.city_id == subq.c.city_id)
            & (cast(WeatherForecast.risk_score, Float) == subq.c.max_risk),
        )
        .order_by(cast(WeatherForecast.risk_score, Float).desc())
        .all()
    )
    return _rows_to_dicts(rows)



def city_count(session: Session) -> int:
    """
    Business question: Combien de villes sont enregistrées ?

    Returns the total count of cities in the database.
    """
    return session.query(func.count(City.id)).scalar()


def global_max_temperature(session: Session) -> dict:
    """
    Business question: Quelle est la température maximale enregistrée (toutes villes confondues) ?

    Returns city name, date, and the peak temperature.
    """
    row = (
        session.query(
            City.name.label("city"),
            WeatherForecast.forecast_date.label("forecast_date"),
            WeatherForecast.temperature_max.label("temperature_max"),
        )
        .join(City, WeatherForecast.city_id == City.id)
        .filter(WeatherForecast.temperature_max.isnot(None))
        .order_by(WeatherForecast.temperature_max.desc())
        .first()
    )
    return row._asdict() if row else {}



def global_max_precipitation(session: Session) -> dict:
    """
    Business question: Quelle est la précipitation maximale enregistrée (toutes villes confondues) ?

    Returns city name, date, and the peak single-day precipitation sum.
    """
    row = (
        session.query(
            City.name.label("city"),
            WeatherForecast.forecast_date.label("forecast_date"),
            WeatherForecast.precipitation_sum.label("precipitation_sum"),
        )
        .join(City, WeatherForecast.city_id == City.id)
        .filter(WeatherForecast.precipitation_sum.isnot(None))
        .order_by(WeatherForecast.precipitation_sum.desc())
        .first()
    )
    return row._asdict() if row else {}


def cities_with_critical_risk(session: Session) -> list[dict]:
    """
    Business question: Quelles villes ont au moins une période de risque critique ?

    Returns the list of cities with one or more Critical forecast days,
    along with how many such days they have.
    """
    rows = (
        session.query(
            City.name.label("city"),
            func.count(WeatherForecast.id).label("critical_days_count"),
        )
        .join(WeatherForecast, WeatherForecast.city_id == City.id)
        .filter(WeatherForecast.risk_level == "Critical")
        .group_by(City.id, City.name)
        .order_by(func.count(WeatherForecast.id).desc())
        .all()
    )
    return _rows_to_dicts(rows)


def risk_distribution_by_level(session: Session) -> list[dict]:
    """
    Business question: Quelle est la distribution des prévisions par niveau de risque ?

    Returns the count and percentage of forecast rows for each risk level.
    """
    risk_levels = ['Low', 'Moderate', 'High', 'Critical']

    total_subq = (
        session.query(func.count(WeatherForecast.id).label("total"))
        .filter(WeatherForecast.risk_level.isnot(None))
        .scalar_subquery()
    )

    rows = (
        session.query(
            WeatherForecast.risk_level.label("risk_level"),
            func.count(WeatherForecast.id).label("count"),
            (
                func.round(
                    cast(func.count(WeatherForecast.id), Numeric) / total_subq * 100,
                    2,
                    
                )
            ).label("percentage"),
        )
        .filter(WeatherForecast.risk_level.isnot(None))
        .group_by(WeatherForecast.risk_level)
        .order_by(func.count(WeatherForecast.id).desc())
        .all()
    )
    data = _rows_to_dicts(rows)

    present_levels  = [item['risk_level'] for item in data]

    for level in risk_levels:
        if level not in present_levels:
            data.append({'risk_level': level, 'count': 0, 'percentage':0.0})

    
    return data




def run_all(session: Session) -> None:
    """Execute all queries and pretty-print the results."""
    import json
    from datetime import date, datetime

    def _serialise(obj):
        """JSON encoder for dates and decimals."""
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return str(obj)

    sections = [
        ("1. Cities with highest average max temperature", cities_with_highest_avg_temperature(session)),
        ("2. Cities with highest total precipitation",     cities_with_highest_precipitation(session)),
        ("3. Cities with highest average risk score",      cities_with_highest_avg_risk(session)),
        ("4. Periods with maximum risk (top 10)",          periods_with_max_risk(session)),
        ("5. Riskiest period per city",                    riskiest_period_per_city(session)),
        ("6. Total number of cities",                      city_count(session)),
        ("7. Global maximum temperature",                  global_max_temperature(session)),
        ("8. Global maximum precipitation",                global_max_precipitation(session)),
        ("9. Cities with Critical risk days",              cities_with_critical_risk(session)),
        ("10. Risk distribution by level",                 risk_distribution_by_level(session)),
    ]

    for title, result in sections:
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}")
        print(json.dumps(result, indent=2, default=_serialise))



if __name__ == "__main__":
    from sqlalchemy.orm import sessionmaker

    from src.database.connection import get_engine

    engine = get_engine()
    Session = sessionmaker(bind=engine)

    with Session() as session:
        run_all(session)
