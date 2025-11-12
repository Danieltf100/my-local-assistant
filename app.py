from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union, AsyncIterator, Callable
from contextlib import asynccontextmanager
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
import logging
import time
import json
import uvicorn
from datetime import datetime
from threading import Thread
import os
import httpx
import re
import asyncio
import inspect
from dotenv import load_dotenv

# Import file processing utilities
from utils import FileManager, DoclingProcessor, CacheManager, CleanupScheduler

# Load environment variables from .env file
load_dotenv()

# Context manager for timing operations
class Timer:
    """
    Context manager for timing operations.
    
    Usage:
        with Timer() as t:
            # code to time
        elapsed_time = t.elapsed
    """
    def __init__(self):
        self.elapsed = 0
        self._start_time = 0
        
    def __enter__(self):
        self._start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self._start_time

# Function Registry System
class FunctionRegistry:
    """
    Registry for managing available functions that the model can call.
    """
    def __init__(self):
        self.functions: Dict[str, Dict[str, Any]] = {}
        
    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ):
        """Register a new function"""
        self.functions[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler
        }
        logger.info(f"Registered function: {name}")
        
    def get_function(self, name: str) -> Optional[Dict[str, Any]]:
        """Get function definition by name"""
        return self.functions.get(name)
        
    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function with given arguments (supports both sync and async functions)"""
        func = self.functions.get(name)
        if not func:
            return {"success": False, "error": f"Function '{name}' not found"}
            
        try:
            # Validate required parameters
            params_schema = func["parameters"]
            for param_name, param_def in params_schema.items():
                if param_def.get("required", False) and param_name not in arguments:
                    return {
                        "success": False,
                        "error": f"Missing required parameter: {param_name}"
                    }
            
            # Execute the function (handle both sync and async)
            handler = func["handler"]
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.error(f"Error executing function {name}: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def get_all_functions(self) -> List[Dict[str, Any]]:
        """Get all registered functions"""
        return [
            {
                "name": func["name"],
                "description": func["description"],
                "parameters": func["parameters"]
            }
            for func in self.functions.values()
        ]
        
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get functions in OpenAI tools format"""
        tools = []
        for func in self.functions.values():
            # Convert parameters to JSON schema format
            properties = {}
            required = []
            
            for param_name, param_def in func["parameters"].items():
                properties[param_name] = {
                    "type": param_def.get("type", "string"),
                    "description": param_def.get("description", "")
                }
                if "enum" in param_def:
                    properties[param_name]["enum"] = param_def["enum"]
                if param_def.get("required", False):
                    required.append(param_name)
            
            tools.append({
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            })
        return tools

# Common city coordinates mapping for geocoding
CITY_COORDINATES = {
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

# Weather API Function
async def get_weather(location: str, units: str = "celsius") -> Dict[str, Any]:
    """
    Get current weather for a location using Meteoblue Forecast API.
    
    The API uses the basic-1h package which provides 7-day forecast with hourly values
    for temperature, wind speed, humidity, and precipitation.
    
    Args:
        location: City name or location (e.g., "São Paulo, Brazil" or "New York, USA")
        units: Temperature units (celsius or fahrenheit)
        
    Returns:
        Weather information including temperature, condition, humidity, wind speed, etc.
    """
    api_key = os.getenv("METEOBLUE_API_KEY", "demo")
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
            # The API returns arrays with hourly data for 7 days (168 hours)
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
                
                # Determine condition based on pictocode or precipitation
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
                
                # Create comprehensive weather data with full hourly forecast
                # Build hourly forecast array with all available data
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
                    "summary": f"Weather forecast for {location_name}: Currently {condition.lower()} with {round(temp_c if units == 'celsius' else temp_f, 1)}{unit_symbol} (feels like {round(felt_temp_c if units == 'celsius' else felt_temp_f, 1)}{unit_symbol}). {len(hourly_forecast)} hours of forecast data available. Use the hourly_forecast array to get detailed hour-by-hour predictions."
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

# Web Search Function using DuckDuckGo API
async def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo Instant Answer API.
    
    The API provides instant answers, abstracts, and related topics for search queries.
    Returns structured information including abstracts from Wikipedia, official websites,
    and related topics.
    
    Args:
        query: The search query string
        max_results: Maximum number of related topics to return (default: 5)
        
    Returns:
        Dictionary containing search results with abstract, related topics, and sources
    """
    try:
        logger.info(f"Searching web for: {query}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1
                },
                timeout=10.0,
                headers={"User-Agent": "GraniteChat/1.0"}
            )
            
            if response.status_code != 200:
                logger.error(f"DuckDuckGo API error: {response.status_code}")
                return {
                    "error": f"Search API returned status {response.status_code}",
                    "query": query
                }
            
            # Check if response has content
            response_text = response.text.strip()
            if not response_text:
                logger.warning(f"DuckDuckGo API returned empty response for: {query}")
                return {
                    "query": query,
                    "abstract": "",
                    "summary": f"No instant answer available for '{query}'. The search API returned an empty response. This query may require a more specific search or the information may not be available in the instant answer database."
                }
            
            try:
                data = response.json()
            except Exception as json_error:
                logger.error(f"Failed to parse JSON response: {json_error}")
                return {
                    "query": query,
                    "error": "Failed to parse search results",
                    "summary": f"Unable to retrieve search results for '{query}'. Please try rephrasing your query."
                }
            
            logger.info(f"DuckDuckGo API response received for query: {query}")
            
            # Extract relevant information
            result = {
                "query": query,
                "abstract": data.get("Abstract", ""),
                "abstract_source": data.get("AbstractSource", ""),
                "abstract_url": data.get("AbstractURL", ""),
                "answer": data.get("Answer", ""),
                "heading": data.get("Heading", ""),
                "entity": data.get("Entity", ""),
                "related_topics": [],
                "results": []
            }
            
            # Add image if available
            if data.get("Image"):
                result["image_url"] = f"https://duckduckgo.com{data['Image']}"
            
            # Add official website if available
            if data.get("OfficialWebsite"):
                result["official_website"] = data["OfficialWebsite"]
            
            # Extract related topics (limit to max_results)
            related_topics = data.get("RelatedTopics", [])
            for topic in related_topics[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    result["related_topics"].append({
                        "text": topic.get("Text", ""),
                        "url": topic.get("FirstURL", "")
                    })
            
            # Extract instant answer results
            results = data.get("Results", [])
            for res in results[:max_results]:
                if isinstance(res, dict):
                    result["results"].append({
                        "text": res.get("Text", ""),
                        "url": res.get("FirstURL", "")
                    })
            
            # Create a summary description
            if result["abstract"]:
                summary = f"Search results for '{query}':\n\n"
                summary += f"{result['abstract']}\n\n"
                if result["abstract_source"]:
                    summary += f"Source: {result['abstract_source']}"
                    if result["abstract_url"]:
                        summary += f" ({result['abstract_url']})"
                    summary += "\n\n"
                
                if result["official_website"]:
                    summary += f"Official Website: {result['official_website']}\n\n"
                
                if result["related_topics"]:
                    summary += "Related Topics:\n"
                    for i, topic in enumerate(result["related_topics"], 1):
                        summary += f"{i}. {topic['text']}\n"
                
                result["summary"] = summary
            elif result["answer"]:
                result["summary"] = f"Answer for '{query}': {result['answer']}"
            else:
                result["summary"] = f"No detailed information found for '{query}'. Try rephrasing your search query."
            
            return result
            
    except httpx.TimeoutException:
        logger.error(f"DuckDuckGo API timeout for query: {query}")
        return {"error": "Search API request timed out", "query": query}
    except Exception as e:
        logger.error(f"Error searching web with DuckDuckGo: {str(e)}", exc_info=True)
        return {"error": str(e), "query": query}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global variables for model and tokenizer
model = None
tokenizer = None
device = "cpu"
function_registry = FunctionRegistry()

# Global variables for file processing
file_manager = None
docling_processor = None
cache_manager = None
cleanup_scheduler = None

# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model and tokenizer
    global model, tokenizer, device, function_registry
    global file_manager, docling_processor, cache_manager, cleanup_scheduler
    
    logger.info("Loading model and tokenizer...")
    start_time = time.time()
    
    try:
        # Set device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        # Load model and tokenizer
        model_path = "ibm-granite/granite-4.0-1b"
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path, device_map=device)
        model.eval()
        
        logger.info(f"Model loaded successfully in {time.time() - start_time:.2f} seconds")
        
        # Initialize file processing components
        logger.info("Initializing file processing system...")
        
        file_manager = FileManager(
            upload_dir=os.getenv("UPLOAD_DIR", "./uploads"),
            max_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
            allowed_extensions=os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,pptx,xlsx,png,jpg,jpeg,gif,txt,md").split(",")
        )
        
        docling_processor = DoclingProcessor()
        
        cache_manager = CacheManager(
            cache_dir=os.getenv("CACHE_DIR", "./cache"),
            ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24"))
        )
        
        # Start cleanup scheduler
        cleanup_scheduler = CleanupScheduler(file_manager, cache_manager)
        cleanup_scheduler.start()
        
        logger.info("File processing system initialized")
        
        # Register functions
        logger.info("Registering functions...")
        
        # Register weather function
        function_registry.register(
            name="get_weather",
            description="Get current weather information for a specific location",
            parameters={
                "location": {
                    "type": "string",
                    "description": "The city or location name",
                    "required": True
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units (celsius or fahrenheit)",
                    "enum": ["celsius", "fahrenheit"],
                    "required": False
                }
            },
            handler=get_weather
        )
        
        # Register web search function
        function_registry.register(
            name="search_web",
            description="Search the web for information using DuckDuckGo. Returns abstracts, related topics, and sources. Use this when you need current information, facts, or details about any topic.",
            parameters={
                "query": {
                    "type": "string",
                    "description": "The search query or question",
                    "required": True
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of related topics to return (default: 5)",
                    "required": False
                }
            },
            handler=search_web
        )
        
        logger.info(f"Registered {len(function_registry.functions)} functions")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise e
    
    yield
    
    # Shutdown: Cleanup
    logger.info("Shutting down application...")
    if cleanup_scheduler:
        cleanup_scheduler.shutdown()

# Create FastAPI app with lifespan
app = FastAPI(
    title="Granite4Nano-1B API",
    description="API for text generation using the IBM Granite 4.0 1B model",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates setup
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Helper function to check if model is loaded
def ensure_model_loaded():
    if model is None or tokenizer is None:
        raise HTTPException(
            status_code=503, 
            detail="Model not loaded. Please wait for initialization to complete."
        )

# Define request and response models
class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="The text prompt to generate from")
    max_tokens: int = Field(100, description="Maximum number of tokens to generate", ge=1, le=1000)
    temperature: float = Field(1.0, description="Sampling temperature", ge=0.0, le=2.0)
    top_p: float = Field(1.0, description="Nucleus sampling parameter", ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, description="Top-k sampling parameter", ge=0)
    repetition_penalty: Optional[float] = Field(None, description="Repetition penalty", ge=0.0)
    do_sample: bool = Field(True, description="Whether to use sampling or greedy decoding")
    num_return_sequences: Optional[int] = Field(1, description="Number of sequences to return", ge=1, le=5)
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "Do you know who you are?",
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True,
                "num_return_sequences": 1
            }
        }

class GenerationResponse(BaseModel):
    generated_text: str
    execution_time: float
    model_name: str = "ibm-granite/granite-4.0-1b"
    prompt: str
    parameters: Dict[str, Any]

# Health check endpoint
@app.get("/health")
async def health_check():
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ok", "model": "ibm-granite/granite-4.0-1b"}

# Helper function to prepare generation parameters
def prepare_generation_params(request):
    """
    Prepare generation parameters from the request.
    
    Args:
        request: The generation request containing parameters
        
    Returns:
        dict: Dictionary of generation parameters
    """
    # Start with required parameters
    params = {
        "max_new_tokens": request.max_tokens,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "do_sample": request.do_sample,
    }
    
    # Add optional parameters if provided
    if request.num_return_sequences is not None:
        params["num_return_sequences"] = request.num_return_sequences
    else:
        params["num_return_sequences"] = 1  # Default to 1 if not provided
        
    if request.top_k is not None:
        params["top_k"] = request.top_k
    if request.repetition_penalty is not None:
        params["repetition_penalty"] = request.repetition_penalty
        
    return params

# Helper function to format chat prompt
def format_chat_prompt(prompt: str) -> list:
    """
    Format a text prompt as a chat message.
    
    Args:
        prompt: The text prompt
        
    Returns:
        list: A list containing the formatted chat message
    """
    return [{"role": "user", "content": prompt}]

# Helper functions for document processing
def format_document_context(processed_files: List[Dict[str, Any]]) -> str:
    """Format processed documents as context for LLM"""
    if not processed_files:
        return ""
    
    context_parts = ["=== ATTACHED DOCUMENTS ===\n"]
    
    for i, file_data in enumerate(processed_files, 1):
        metadata = file_data.get("metadata", {})
        markdown = file_data.get("markdown", "")
        
        context_parts.append(f"\n--- Document {i}: {metadata.get('filename', 'Unknown')} ---")
        context_parts.append(f"Format: {metadata.get('format', 'Unknown')}")
        
        if metadata.get('page_count'):
            context_parts.append(f"Pages: {metadata['page_count']}")
        
        context_parts.append(f"\nContent:\n{markdown}\n")
        context_parts.append("--- End of Document ---\n")
    
    context_parts.append("\n=== END OF DOCUMENTS ===\n")
    
    return "\n".join(context_parts)

def prepare_prompt_with_context(
    user_prompt: str,
    processed_files: List[Dict[str, Any]],
    system_prompt: Optional[str] = None
) -> str:
    """Build enhanced prompt with document context"""
    
    # Format document context
    doc_context = format_document_context(processed_files)
    
    # Build instruction for the model
    instruction = """You have been provided with document(s) as reference material.
Please analyze the documents and answer the user's question based on the information provided.
If the answer cannot be found in the documents, please state that clearly."""
    
    # Combine all parts
    if doc_context:
        enhanced_prompt = f"""{instruction}

{doc_context}

User Question: {user_prompt}

Please provide a detailed answer based on the documents above."""
    else:
        enhanced_prompt = user_prompt
    
    return enhanced_prompt

async def process_document_with_cache(file_path: str) -> Dict[str, Any]:
    """Process document with caching"""
    # Check cache first
    cached = cache_manager.get(file_path)
    if cached:
        logger.info(f"Cache hit for {file_path}")
        return cached
    
    # Process document
    logger.info(f"Cache miss for {file_path}, processing...")
    result = await docling_processor.process_document(file_path)
    
    # Cache result
    if result.get("success"):
        cache_manager.set(file_path, result)
    
    return result

# Text generation endpoint
@app.post("/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest, background_tasks: BackgroundTasks):
    """
    Generate text based on the provided prompt and parameters.
    
    This endpoint processes a text generation request with the following steps:
    1. Formats the prompt as a chat message
    2. Applies the model's chat template
    3. Tokenizes the formatted prompt
    4. Generates text using the specified parameters
    5. Returns the generated text with metadata
    
    Args:
        request: The generation request containing prompt and parameters
        background_tasks: FastAPI background tasks manager
        
    Returns:
        GenerationResponse: The generated text and metadata
        
    Raises:
        HTTPException: If an error occurs during text generation
    """
    # Ensure model is loaded
    ensure_model_loaded()
    
    try:
        # Use the Timer context manager for accurate timing
        with Timer() as timer:
            # Format the prompt as a chat
            chat = format_chat_prompt(request.prompt)
            
            # Apply chat template
            formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
            
            # Tokenize the text
            input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
            
            # Prepare generation parameters
            generation_params = prepare_generation_params(request)
            
            # Generate output tokens
            output = model.generate(**input_tokens, **generation_params)
            
            # Decode output tokens into text
            # Extract only the new tokens (exclude the input prompt)
            input_length = input_tokens["input_ids"].shape[1]
            generated_texts = tokenizer.batch_decode(output[:, input_length:], skip_special_tokens=True)
        
        # Log completion
        logger.info(f"Text generation completed in {timer.elapsed:.2f} seconds")
        
        # Return the first generated text (or we could return all if num_return_sequences > 1)
        # Use dictionary comprehension for cleaner parameter mapping
        return GenerationResponse(
            generated_text=generated_texts[0],
            execution_time=timer.elapsed,
            prompt=request.prompt,
            parameters={field: getattr(request, field) for field in [
                "max_tokens", "temperature", "top_p", "top_k",
                "repetition_penalty", "do_sample", "num_return_sequences"
            ]}
        )
    
    except torch.cuda.OutOfMemoryError as e:
        logger.error(f"CUDA out of memory error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="GPU memory exceeded. Try reducing max_tokens or using a smaller model."
        )
    except ValueError as e:
        logger.error(f"Value error in text generation: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid request parameters: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating text: {str(e)}")

# Chat completion endpoint (similar to OpenAI's chat completion)
@app.post("/v1/chat/completions")
async def chat_completion(request: dict):
    """
    OpenAI-compatible chat completion endpoint.
    
    This endpoint mimics the OpenAI chat completion API format for easier integration
    with existing applications.
    """
    # Ensure model is loaded
    ensure_model_loaded()
    
    try:
        # Extract parameters from the request
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 100)
        temperature = request.get("temperature", 1.0)
        top_p = request.get("top_p", 1.0)
        custom_system_prompt = request.get("system_prompt", "")  # Custom system prompt from frontend
        
        # Validate messages
        if not messages or not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="Invalid messages format")
        
        # Format messages for our model
        chat = []
        
        # Add system message
        if custom_system_prompt:
            # Use custom system prompt if provided
            chat.append({"role": "system", "content": custom_system_prompt})
        else:
            # Use default system message with function calling instructions
            available_functions = function_registry.get_all_functions()
            if available_functions:
                functions_desc = "\n".join([
                    f"- {func['name']}: {func['description']}\n  Parameters: {json.dumps(func['parameters'])}"
                    for func in available_functions
                ])
                
                # Get current date and time
                from datetime import datetime
                current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                system_message = f"""You are a helpful assistant with access to the following functions:

{functions_desc}

Current date and time: {current_datetime}

When you need to use a function, respond with:
<function_call>
{{"name": "function_name", "arguments": {{"param1": "value1", "param2": "value2"}}}}
</function_call>

You can include reasoning text before the function call to explain what you're doing."""
                
                chat.append({"role": "system", "content": system_message})
        
        # Add user messages and handle function results
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise HTTPException(status_code=400, detail="Invalid message format")
            
            # Convert function role to user role with special formatting
            if msg["role"] == "function":
                function_name = msg.get("name", "unknown_function")
                function_content = msg["content"]
                # Format function result as a user message so the model can process it
                chat.append({
                    "role": "user",
                    "content": f"Function '{function_name}' returned:\n{function_content}"
                })
            else:
                chat.append({"role": msg["role"], "content": msg["content"]})
        
        # Apply chat template
        formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        
        # Start timing
        start_time = time.time()
        
        # Tokenize the text
        input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Generate output tokens
        output = model.generate(
            **input_tokens,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0.0
        )
        
        # Decode output tokens into text
        # Extract only the new tokens (exclude the input prompt)
        input_length = input_tokens["input_ids"].shape[1]
        generated_text = tokenizer.batch_decode(output[:, input_length:], skip_special_tokens=True)[0]
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Format response in OpenAI-like structure
        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "ibm-granite/granite-4.0-1b",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": generated_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(input_tokens["input_ids"][0]),
                "completion_tokens": len(output[0]) - len(input_tokens["input_ids"][0]),
                "total_tokens": len(output[0])
            }
        }
        
        return response
    
    except Exception as e:
        logger.error(f"Error in chat completion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in chat completion: {str(e)}")

# Function calling endpoint
@app.post("/v1/function_call")
async def function_call(request: dict):
    """
    Endpoint for function calling capabilities.
    
    This endpoint allows the model to use tools/functions defined in the request.
    """
    # Ensure model is loaded
    ensure_model_loaded()
    
    try:
        # Extract parameters from the request
        messages = request.get("messages", [])
        tools = request.get("tools", [])
        max_tokens = request.get("max_tokens", 100)
        temperature = request.get("temperature", 1.0)
        
        # Validate messages
        if not messages or not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="Invalid messages format")
        
        # Format messages for our model
        chat = []
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise HTTPException(status_code=400, detail="Invalid message format")
            chat.append({"role": msg["role"], "content": msg["content"]})
        
        # Apply chat template with tools
        formatted_prompt = tokenizer.apply_chat_template(
            chat, 
            tokenize=False, 
            add_generation_prompt=True,
            tools=tools
        )
        
        # Tokenize the text
        input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Generate output tokens
        output = model.generate(
            **input_tokens,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0.0
        )
        
        # Decode output tokens into text
        # Extract only the new tokens (exclude the input prompt)
        input_length = input_tokens["input_ids"].shape[1]
        generated_text = tokenizer.batch_decode(output[:, input_length:], skip_special_tokens=True)[0]
        
        # Format response
        response = {
            "id": f"funcall-{int(time.time())}",
            "object": "function.call",
            "created": int(time.time()),
            "model": "ibm-granite/granite-4.0-1b",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": generated_text
                    }
                }
            ]
        }
        
        return response
    
    except Exception as e:
        logger.error(f"Error in function call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in function call: {str(e)}")

# Serve the chat interface
@app.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """
    Serve the main chat interface page
    """
    return templates.TemplateResponse("index.html", {"request": request})

# Get available functions
@app.get("/api/functions")
async def get_available_functions():
    """
    Get list of all available functions that can be called
    """
    return JSONResponse(content={
        "functions": function_registry.get_all_functions(),
        "tools": function_registry.get_tools_schema()
    })

# Execute a function
@app.post("/api/execute_function")
async def execute_function(request: dict):
    """
    Execute a registered function with given arguments
    
    Request format:
    {
        "function_name": "get_weather",
        "arguments": {"location": "São Paulo", "units": "celsius"}
    }
    """
    try:
        function_name = request.get("function_name")
        arguments = request.get("arguments", {})
        
        if not function_name:
            raise HTTPException(status_code=400, detail="function_name is required")
        
        logger.info(f"Executing function: {function_name} with arguments: {arguments}")
        
        # Execute the function (await since it's async now)
        result = await function_registry.execute(function_name, arguments)
        
        if not result["success"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result["error"]}
            )
        
        return JSONResponse(content={
            "success": True,
            "function_name": function_name,
            "result": result["result"]
        })
        
    except Exception as e:
        logger.error(f"Error executing function: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# File upload endpoint with document processing
@app.post("/v1/chat/upload")
async def chat_with_files(
    prompt: str = Form(...),
    files: List[UploadFile] = File(None),
    max_tokens: int = Form(100),
    temperature: float = Form(0.7),
    top_p: float = Form(0.9),
    system_prompt: Optional[str] = Form(None)
):
    """
    Chat endpoint that accepts text prompt and optional file attachments.
    Processes files with Docling and includes content as context.
    """
    ensure_model_loaded()
    
    try:
        start_time = time.time()
        processed_files = []
        
        # Process files if provided
        if files and len(files) > 0:
            logger.info(f"Processing {len(files)} uploaded files")
            
            for file in files:
                # Read file content
                content = await file.read()
                
                # Validate file
                is_valid, error_msg = file_manager.validate_file(file.filename, len(content))
                if not is_valid:
                    raise HTTPException(status_code=400, detail=error_msg)
                
                # Save file
                file_path = await file_manager.save_file(content, file.filename)
                
                # Process with Docling (with caching)
                processed_content = await process_document_with_cache(file_path)
                
                if processed_content.get("success"):
                    processed_files.append(processed_content)
                else:
                    logger.warning(f"Failed to process {file.filename}: {processed_content.get('error')}")
        
        # Prepare enhanced prompt with document context
        if processed_files:
            enhanced_prompt = prepare_prompt_with_context(prompt, processed_files, system_prompt)
        else:
            enhanced_prompt = prompt
        
        # Format messages for chat completion
        messages = [{"role": "user", "content": enhanced_prompt}]
        
        # Add custom system prompt if provided and no files
        if system_prompt and not processed_files:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Format chat
        chat = []
        for msg in messages:
            chat.append({"role": msg["role"], "content": msg["content"]})
        
        # Apply chat template
        formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        
        # Tokenize
        input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Generate
        output = model.generate(
            **input_tokens,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0.0
        )
        
        # Decode
        input_length = input_tokens["input_ids"].shape[1]
        generated_text = tokenizer.batch_decode(output[:, input_length:], skip_special_tokens=True)[0]
        
        execution_time = time.time() - start_time
        
        # Format response
        response = {
            "response": generated_text,
            "files_processed": [
                {
                    "filename": f.get("metadata", {}).get("filename", "Unknown"),
                    "pages": f.get("metadata", {}).get("page_count"),
                    "status": "success" if f.get("success") else "failed"
                }
                for f in processed_files
            ],
            "execution_time": execution_time
        }
        
        logger.info(f"Chat with files completed in {execution_time:.2f}s, processed {len(processed_files)} files")
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_with_files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# Streaming endpoint for real-time responses
@app.post("/v1/stream")
async def stream_response(request: dict):
    """
    Stream response tokens in real-time
    
    This endpoint accepts chat messages and streams the generated response
    token by token in a format compatible with OpenAI's streaming API.
    """
    # Ensure model is loaded
    ensure_model_loaded()
    
    try:
        # Extract parameters from the request
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 100)
        temperature = request.get("temperature", 1.0)
        top_p = request.get("top_p", 1.0)
        top_k = request.get("top_k", None)
        do_sample = request.get("do_sample", temperature > 0.0)
        custom_system_prompt = request.get("system_prompt", "")  # Custom system prompt from frontend
        
        # Validate messages
        if not messages or not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="Invalid messages format")
        
        # Format messages for our model
        chat = []
        
        # Add system message
        if custom_system_prompt:
            # Use custom system prompt if provided
            chat.append({"role": "system", "content": custom_system_prompt})
        else:
            # Use default system message with function calling instructions
            available_functions = function_registry.get_all_functions()
            if available_functions:
                functions_desc = "\n".join([
                    f"- {func['name']}: {func['description']}\n  Parameters: {json.dumps(func['parameters'])}"
                    for func in available_functions
                ])
                
                # Get current date and time
                from datetime import datetime
                current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                system_message = f"""You are a helpful assistant with access to the following functions:

{functions_desc}

Current date and time: {current_datetime}

When you need to use a function, respond with:
<function_call>
{{"name": "function_name", "arguments": {{"param1": "value1", "param2": "value2"}}}}
</function_call>

You can include reasoning text before the function call to explain what you're doing.
After the function executes, you'll receive the result and can continue the conversation."""
                
                chat.append({"role": "system", "content": system_message})
        
        # Add user messages and handle function results
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise HTTPException(status_code=400, detail="Invalid message format")
            
            # Convert function role to user role with special formatting
            if msg["role"] == "function":
                function_name = msg.get("name", "unknown_function")
                function_content = msg["content"]
                # Format function result as a user message so the model can process it
                chat.append({
                    "role": "user",
                    "content": f"Function '{function_name}' returned:\n{function_content}"
                })
            else:
                chat.append({"role": msg["role"], "content": msg["content"]})
        
        # Apply chat template
        formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        
        # Tokenize the text
        input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Set up streamer - skip prompt tokens to only stream the generated response
        streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True, skip_prompt=True)
        
        # Prepare generation parameters
        generation_kwargs = {
            **input_tokens,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "do_sample": do_sample,
            "streamer": streamer
        }
        
        # Add optional parameters if provided
        if top_k is not None:
            generation_kwargs["top_k"] = top_k
        
        # Define async generator for streaming
        async def token_generator() -> AsyncIterator[str]:
            # Start with a JSON opening
            yield '{"id": "stream-' + str(int(time.time())) + '", "choices": ['
            
            # Generate in a separate thread to avoid blocking
            thread = Thread(target=model.generate, kwargs=generation_kwargs)
            thread.start()
            
            # Stream tokens as they're generated
            i = 0
            for token in streamer:
                # Yield each token as a JSON chunk
                chunk = {
                    "index": i,
                    "delta": {"content": token},
                    "finish_reason": None
                }
                
                if i > 0:
                    yield ','
                yield json.dumps(chunk)
                i += 1
            
            # Final chunk with finish reason
            yield '], "finish_reason": "stop"}'
        
        return StreamingResponse(token_generator(), media_type="application/json", headers={'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache', 'Expires': '0'})
    
    except torch.cuda.OutOfMemoryError as e:
        logger.error(f"CUDA out of memory error in streaming: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="GPU memory exceeded. Try reducing max_tokens or using a smaller model."
        )
    except ValueError as e:
        logger.error(f"Value error in streaming: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid request parameters: {str(e)}")
    except Exception as e:
        logger.error(f"Error in streaming: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in streaming: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

# Made with Bob
