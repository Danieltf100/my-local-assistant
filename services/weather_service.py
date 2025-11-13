"""
Weather API service.

This module provides weather information using the Meteoblue API
with geocoding support via OpenStreetMap Nominatim.
"""

import logging
import httpx
from typing import Dict, Any
from constants import CITY_COORDINATES

logger = logging.getLogger(__name__)


async def geocode_location(location: str) -> Dict[str, Any]:
    """
    Convert location name to coordinates using OpenStreetMap Nominatim API.
    Falls back to predefined coordinates for common cities.
    
    Args:
        location: City name or location
        
    Returns:
        Dictionary with lat, lon, and name
    """
    # Check predefined coordinates first
    location_lower = location.lower().strip()
    if location_lower in CITY_COORDINATES:
        return CITY_COORDINATES[location_lower]
    
    # Try OpenStreetMap Nominatim API for geocoding
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": location,
                    "format": "json",
                    "limit": 1
                },
                headers={"User-Agent": "GraniteChat/1.0"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    return {
                        "lat": float(result["lat"]),
                        "lon": float(result["lon"]),
                        "name": result.get("display_name", location)
                    }
    except Exception as e:
        logger.warning(f"Geocoding failed for {location}: {str(e)}")
    
    # Default fallback to São Paulo
    return {"lat": -23.5505, "lon": -46.6333, "name": location}


async def get_weather(location: str, units: str = "celsius", api_key: str = "demo") -> Dict[str, Any]:
    """
    Get current weather for a location using Meteoblue Forecast API.
    
    The API uses the basic-1h package which provides 7-day forecast with hourly values
    for temperature, wind speed, humidity, and precipitation.
    
    Args:
        location: City name or location (e.g., "São Paulo, Brazil" or "New York, USA")
        units: Temperature units (celsius or fahrenheit)
        api_key: Meteoblue API key
        
    Returns:
        Weather information including temperature, condition, humidity, wind speed, etc.
    """
    unit_symbol = "°C" if units == "celsius" else "°F"
    
    try:
        # For demo purposes, if no API key, return mock data
        if api_key == "demo":
            logger.info(f"Using mock weather data for {location}")
            temp_c = 25
            temp_f = 77
            return {
                "location": location,
                "temperature": temp_c if units == "celsius" else temp_f,
                "unit": unit_symbol,
                "condition": "Partly Cloudy",
                "humidity": 65,
                "wind_speed": 15,
                "precipitation": 10,
                "description": f"The weather in {location} is partly cloudy with a temperature of {temp_c if units == 'celsius' else temp_f}{unit_symbol}, humidity at 65%, and light winds at 15 km/h."
            }
        
        # Get coordinates for the location
        coords = await geocode_location(location)
        logger.info(f"Geocoded {location} to lat={coords['lat']}, lon={coords['lon']}")
        
        # Call Meteoblue Forecast API with coordinates
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://my.meteoblue.com/packages/basic-1h",
                params={
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "apikey": api_key,
                    "format": "json"
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.error(f"Meteoblue API error: {response.status_code} - {response.text}")
                return {
                    "error": f"Weather API returned status {response.status_code}",
                    "location": location
                }
            
            data = response.json()
            logger.info(f"Meteoblue API response keys: {data.keys()}")
            
            # Extract current weather data from the first hour of forecast
            if "data_1h" in data:
                hourly_data = data["data_1h"]
                metadata = data.get("metadata", {})
                
                # Get the first (current) hour data
                temp_c = hourly_data["temperature"][0] if "temperature" in hourly_data else 20
                windspeed = hourly_data["windspeed"][0] if "windspeed" in hourly_data else 10
                precipitation = hourly_data["precipitation"][0] if "precipitation" in hourly_data else 0
                humidity = hourly_data.get("relativehumidity", [50])[0]
                felt_temp_c = hourly_data.get("felttemperature", [temp_c])[0]
                wind_direction = hourly_data.get("winddirection", [0])[0]
                pictocode = hourly_data.get("pictocode", [1])[0]
                uv_index = hourly_data.get("uvindex", [0])[0]
                precipitation_prob = hourly_data.get("precipitation_probability", [0])[0]
                
                # Convert to Fahrenheit if needed
                temp_f = (temp_c * 9/5) + 32
                felt_temp_f = (felt_temp_c * 9/5) + 32
                
                # Determine condition based on pictocode
                condition_map = {
                    1: "Clear", 2: "Partly Cloudy", 3: "Cloudy", 4: "Overcast",
                    5: "Fog", 6: "Light Rain", 7: "Rain", 8: "Heavy Rain",
                    9: "Thunderstorm", 12: "Light Snow", 13: "Snow", 14: "Heavy Snow",
                    20: "Drizzle", 21: "Light Showers", 22: "Showers", 23: "Heavy Showers",
                    27: "Light Snow Showers", 28: "Snow Showers", 31: "Thunderstorm with Rain",
                    33: "Thunderstorm with Snow"
                }
                condition = condition_map.get(pictocode, "Clear")
                
                location_name = metadata.get("name") or coords.get("name", location)
                
                # Build hourly forecast array
                hourly_forecast = []
                num_hours = len(hourly_data.get("time", []))
                
                for i in range(num_hours):
                    hour_temp_c = hourly_data["temperature"][i]
                    hour_temp_f = (hour_temp_c * 9/5) + 32
                    
                    hourly_forecast.append({
                        "time": hourly_data["time"][i],
                        "temperature": round(hour_temp_c if units == "celsius" else hour_temp_f, 1),
                        "feels_like": round(hourly_data.get("felttemperature", [hour_temp_c]*num_hours)[i] if units == "celsius" else (hourly_data.get("felttemperature", [hour_temp_c]*num_hours)[i] * 9/5) + 32, 1),
                        "condition": condition_map.get(hourly_data.get("pictocode", [1]*num_hours)[i], "Clear"),
                        "humidity": round(hourly_data.get("relativehumidity", [50]*num_hours)[i]),
                        "wind_speed": round(hourly_data.get("windspeed", [0]*num_hours)[i], 1),
                        "wind_direction": round(hourly_data.get("winddirection", [0]*num_hours)[i]),
                        "precipitation": round(hourly_data.get("precipitation", [0]*num_hours)[i], 1),
                        "precipitation_probability": round(hourly_data.get("precipitation_probability", [0]*num_hours)[i]),
                        "uv_index": round(hourly_data.get("uvindex", [0]*num_hours)[i])
                    })
                
                weather_data = {
                    "location": location_name,
                    "coordinates": {
                        "latitude": metadata.get("latitude", coords.get("lat")),
                        "longitude": metadata.get("longitude", coords.get("lon")),
                        "elevation": metadata.get("height"),
                        "timezone": metadata.get("timezone_abbrevation", "UTC")
                    },
                    "current": {
                        "temperature": round(temp_c if units == "celsius" else temp_f, 1),
                        "feels_like": round(felt_temp_c if units == "celsius" else felt_temp_f, 1),
                        "unit": unit_symbol,
                        "condition": condition,
                        "humidity": round(humidity),
                        "wind_speed": round(windspeed, 1),
                        "wind_direction": round(wind_direction),
                        "precipitation": round(precipitation, 1),
                        "precipitation_probability": round(precipitation_prob),
                        "uv_index": round(uv_index)
                    },
                    "hourly_forecast": hourly_forecast,
                    "summary": f"Weather forecast for {location_name}: Currently {condition.lower()} with {round(temp_c if units == 'celsius' else temp_f, 1)}{unit_symbol} (feels like {round(felt_temp_c if units == 'celsius' else felt_temp_f, 1)}{unit_symbol}). {len(hourly_forecast)} hours of forecast data available."
                }
                
                return weather_data
            else:
                logger.error(f"No data_1h in response. Available keys: {data.keys()}")
                return {
                    "error": "Unable to parse weather data from API response",
                    "location": location
                }
            
    except httpx.TimeoutException:
        logger.error(f"Meteoblue API timeout for {location}")
        return {"error": "Weather API request timed out", "location": location}
    except Exception as e:
        logger.error(f"Error fetching weather from Meteoblue: {str(e)}", exc_info=True)
        return {"error": str(e), "location": location}

# Made with Bob
