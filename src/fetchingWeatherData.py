import openmeteo_requests

import pandas as pd
import numpy as np
import requests_cache
from retry_requests import retry
import requests

from pathlib import Path

import json
import logging

from openmeteo_requests.Client import OpenMeteoRequestsError



from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "weather_errors.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)



# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://api.open-meteo.com/v1/forecast"

dailyVars = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",

    "apparent_temperature_max",
    "apparent_temperature_min",

    "precipitation_sum",
    "rain_sum",
    "showers_sum",
    "precipitation_hours",
    "precipitation_probability_max",

    "weather_code",

    "wind_speed_10m_max",
    "wind_gusts_10m_max",

    "sunrise",
    "sunset",
    "sunshine_duration",

    "uv_index_max"
]

def getWeatherData(city, latitude, longitude):

	params = {
		"latitude": latitude,
		"longitude": longitude,
		"daily": ",".join(dailyVars)
	}
	try:
		responses = openmeteo.weather_api(url, params=params)
		if not responses:
			raise RuntimeError("API returned no responses")

	except OpenMeteoRequestsError as e:
		logger.error(f"Open-Meteo API error for {city}: {e}")
		print(f"❌ Open-Meteo API error for {city}: {e}")
		return False

	except requests.exceptions.RequestException as e:
		logger.error(f"Network error for {city}: {e}")
		print(f"❌ Network error for {city}: {e}")
		return False

	except Exception as e:
		logger.exception(f"Unexpected error for {city}: {e}")
		print(f"❌ Unexpected error for {city}: {e}")
		return False


	# Process first location. Add a for-loop for multiple locations or weather models
	response = responses[0]
	print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
	print(f"Elevation: {response.Elevation()} m asl")
	print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

	# Process hourly data. The order of variables needs to be the same as requested.
	daily = response.Daily()

	daily_data = {
		"date": pd.date_range(
			start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
			end =  pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
			freq = pd.Timedelta(seconds = daily.Interval()),
			inclusive = "left"
		).strftime('%Y-%m-%dT%H:%M:%SZ').tolist()
	}

	for i in range(len(dailyVars)):
		if isinstance(var := daily.Variables(i).ValuesAsNumpy() , np.ndarray):
			daily_data[dailyVars[i]] = var.tolist()
		else : daily_data[dailyVars[i]] = var


	cityFile = f"data/bronze/{city}.json"

	with open(cityFile, 'w', encoding='utf-8') as f:
		json.dump(daily_data, f, indent=4)


cities = Path('ma.csv')

if not cities.exists():
	print('cities file does not exists please provide it and retry')

cities_df =  pd.read_csv('ma.csv')

for _, city in cities_df.iterrows():
	if not getWeatherData(city['city'], city['lat'], city['lng']): break
