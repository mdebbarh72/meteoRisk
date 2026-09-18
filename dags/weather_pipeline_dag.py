from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

import sys
import os

sys.path.insert(0, '/opt/airflow')

from src.bronze.extract_cities import extract_cities
from src.bronze.extract_weather import extract_weather
from src.silver.clean_cities import clean_cities
from src.silver.clean_weather import clean_weather
from src.silver.quality_checks import run_quality_checks
from src.gold.create_features import create_features
from src.database.loader import load_to_postgres


default_args = {
    "owner": "weather-risk",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="weather_risk_pipeline",
    default_args=default_args,
    start_date=datetime(2026, 9, 14),
    schedule="@daily",
    catchup=False,
) as dag:

    extract_cities_task = PythonOperator(
        task_id="extract_cities",
        python_callable=extract_cities,
    )

    extract_weather_task = PythonOperator(
        task_id="extract_weather",
        python_callable=extract_weather,
    )

    clean_cities_task = PythonOperator(
        task_id="clean_cities",
        python_callable=clean_cities,
    )

    clean_weather_task = PythonOperator(
        task_id="clean_weather",
        python_callable=clean_weather,
    )

    quality_task = PythonOperator(
        task_id="quality_checks",
        python_callable=run_quality_checks,
    )

    features_task = PythonOperator(
        task_id="create_features",
        python_callable=create_features,
    )

    load_task = PythonOperator(
        task_id="load_postgres",
        python_callable=load_to_postgres,
    )

    # Define the execution pipeline order
    extract_cities_task >> extract_weather_task
    extract_weather_task >> [clean_cities_task, clean_weather_task]
    [clean_cities_task, clean_weather_task] >> quality_task
    quality_task >> features_task >> load_task
