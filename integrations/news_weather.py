# -*- coding: utf-8 -*-
"""
News & Weather Integrations (Phase 6)
Env:
- OPENWEATHER_KEY: OpenWeatherMap API key
- NEWSAPI_KEY: NewsAPI.org API key
"""

import os
import requests
import logging
from typing import Tuple, Dict, List


def get_weather(city: str, units: str = 'metric') -> Tuple[bool, Dict]:
    key = os.environ.get('OPENWEATHER_KEY')
    if not key:
        return False, {"error": "OpenWeather API key missing"}

    url = 'https://api.openweathermap.org/data/2.5/weather'
    params = {"q": city, "appid": key, "units": units}
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 200:
            data = r.json()
            main = data.get('main', {})
            weather = (data.get('weather') or [{}])[0]
            return True, {
                "temp": main.get('temp'),
                "feels_like": main.get('feels_like'),
                "humidity": main.get('humidity'),
                "desc": weather.get('description'),
                "city": data.get('name')
            }
        logging.warning(f"[NewsWeather] OpenWeather error {r.status_code}: {r.text[:80]}")
        return False, {"error": f"OpenWeather error {r.status_code}"}
    except requests.RequestException as e:
        logging.exception("[NewsWeather] Network error fetching weather")
        return False, {"error": str(e)}
    except Exception:
        logging.exception("[NewsWeather] Weather fetch failed")
        return False, {"error": "Weather fetch failed"}


def get_news(topic: str = 'technology', country: str = 'us', page_size: int = 5) -> Tuple[bool, List[Dict]]:
    key = os.environ.get('NEWSAPI_KEY')
    if not key:
        return False, [{"error": "NewsAPI key missing"}]

    url = 'https://newsapi.org/v2/top-headlines'
    params = {"q": topic, "country": country, "pageSize": page_size, "apiKey": key}
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 200:
            data = r.json()
            articles = data.get('articles', [])
            items = [
                {"title": a.get('title'), "source": (a.get('source') or {}).get('name')}
                for a in articles if a.get('title')
            ]
            return True, items
        logging.warning(f"[NewsWeather] NewsAPI error {r.status_code}: {r.text[:80]}")
        return False, [{"error": f"NewsAPI error {r.status_code}"}]
    except requests.RequestException as e:
        logging.exception("[NewsWeather] Network error fetching news")
        return False, [{"error": str(e)}]
    except Exception:
        logging.exception("[NewsWeather] News fetch failed")
        return False, [{"error": "News fetch failed"}]
