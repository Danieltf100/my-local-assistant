"""
City coordinates mapping for geocoding.

This module contains predefined coordinates for common cities worldwide,
used as a fallback when the geocoding API is unavailable.
"""

from typing import Dict, Any

CITY_COORDINATES: Dict[str, Dict[str, Any]] = {
    "são paulo": {"lat": -23.5505, "lon": -46.6333, "name": "São Paulo, Brazil"},
    "sao paulo": {"lat": -23.5505, "lon": -46.6333, "name": "São Paulo, Brazil"},
    "new york": {"lat": 40.7128, "lon": -74.0060, "name": "New York, USA"},
    "london": {"lat": 51.5074, "lon": -0.1278, "name": "London, UK"},
    "paris": {"lat": 48.8566, "lon": 2.3522, "name": "Paris, France"},
    "tokyo": {"lat": 35.6762, "lon": 139.6503, "name": "Tokyo, Japan"},
    "berlin": {"lat": 52.5200, "lon": 13.4050, "name": "Berlin, Germany"},
    "madrid": {"lat": 40.4168, "lon": -3.7038, "name": "Madrid, Spain"},
    "rome": {"lat": 41.9028, "lon": 12.4964, "name": "Rome, Italy"},
    "moscow": {"lat": 55.7558, "lon": 37.6173, "name": "Moscow, Russia"},
    "beijing": {"lat": 39.9042, "lon": 116.4074, "name": "Beijing, China"},
    "sydney": {"lat": -33.8688, "lon": 151.2093, "name": "Sydney, Australia"},
    "rio de janeiro": {"lat": -22.9068, "lon": -43.1729, "name": "Rio de Janeiro, Brazil"},
    "los angeles": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, USA"},
    "chicago": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, USA"},
    "toronto": {"lat": 43.6532, "lon": -79.3832, "name": "Toronto, Canada"},
    "mexico city": {"lat": 19.4326, "lon": -99.1332, "name": "Mexico City, Mexico"},
    "buenos aires": {"lat": -34.6037, "lon": -58.3816, "name": "Buenos Aires, Argentina"},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "name": "Mumbai, India"},
    "dubai": {"lat": 25.2048, "lon": 55.2708, "name": "Dubai, UAE"},
    "singapore": {"lat": 1.3521, "lon": 103.8198, "name": "Singapore"},
    "hong kong": {"lat": 22.3193, "lon": 114.1694, "name": "Hong Kong"},
    "basel": {"lat": 47.56, "lon": 7.57, "name": "Basel, Switzerland"},
}

# Made with Bob
