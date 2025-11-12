import requests
import json
import time
import argparse

def test_health(base_url):
    """Test the health check endpoint"""
    print("\n=== Testing Health Check Endpoint ===")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_generate(base_url):
    """Test the text generation endpoint"""
    print("\n=== Testing Text Generation Endpoint ===")
    payload = {
        "prompt": "Do you know who you are?",
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 0.9,
        "do_sample": True,
        "num_return_sequences": 1
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{base_url}/generate", json=payload)
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Time taken: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Generated Text: {result['generated_text']}")
            print(f"Execution Time: {result['execution_time']:.2f} seconds")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_chat_completion(base_url):
    """Test the OpenAI-compatible chat completion endpoint"""
    print("\n=== Testing Chat Completion Endpoint ===")
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Do you know who you are?"}
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{base_url}/v1/chat/completions", json=payload)
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Time taken: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Generated Text: {result['choices'][0]['message']['content']}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_function_call(base_url):
    """Test the function calling endpoint"""
    print("\n=== Testing Function Call Endpoint ===")
    payload = {
        "messages": [
            {"role": "user", "content": "What's the weather like in Boston right now?"}
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather information for a specific location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city or location name"
                            },
                            "units": {
                                "type": "string",
                                "description": "Temperature units (celsius or fahrenheit)",
                                "enum": ["celsius", "fahrenheit"]
                            }
                        },
                        "required": ["location"]
                    }
                }
            }
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{base_url}/v1/function_call", json=payload)
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Time taken: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Generated Text: {result['choices'][0]['message']['content']}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_execute_function(base_url):
    """Test the function execution endpoint"""
    print("\n=== Testing Function Execution Endpoint ===")
    
    # First, get available functions
    print("\n1. Getting available functions...")
    try:
        response = requests.get(f"{base_url}/api/functions")
        if response.status_code == 200:
            functions_data = response.json()
            print(f"Available functions: {len(functions_data['functions'])}")
            for func in functions_data['functions']:
                print(f"  - {func['name']}: {func['description']}")
        else:
            print(f"Error getting functions: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    
    # Test weather function with different locations
    test_cases = [
        {"location": "São Paulo, Brazil", "units": "celsius"},
        {"location": "New York, USA", "units": "fahrenheit"},
        {"location": "Tokyo, Japan", "units": "celsius"}
    ]
    
    print("\n2. Testing weather function execution...")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {test_case['location']} ({test_case['units']})")
        payload = {
            "function_name": "get_weather",
            "arguments": test_case
        }
        
        try:
            start_time = time.time()
            response = requests.post(f"{base_url}/api/execute_function", json=payload)
            elapsed = time.time() - start_time
            
            print(f"  Status Code: {response.status_code}")
            print(f"  Time taken: {elapsed:.2f} seconds")
            
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    weather = result['result']
                    print(f"  ✓ Success!")
                    print(f"    Location: {weather.get('location', 'N/A')}")
                    print(f"    Temperature: {weather.get('temperature', 'N/A')}{weather.get('unit', '')}")
                    print(f"    Condition: {weather.get('condition', 'N/A')}")
                    print(f"    Humidity: {weather.get('humidity', 'N/A')}%")
                    print(f"    Wind Speed: {weather.get('wind_speed', 'N/A')} km/h")
                    if 'description' in weather:
                        print(f"    Description: {weather['description']}")
                else:
                    print(f"  ✗ Function execution failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"  ✗ Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            return False
    
    print("\n✓ All function execution tests passed!")
    return True

def test_stream(base_url):
    """Test the streaming endpoint"""
    print("\n=== Testing Streaming Endpoint ===")
    payload = {
        "messages": [
            {"role": "user", "content": "Write a short poem about programming."}
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    try:
        print("Sending request to streaming endpoint...")
        start_time = time.time()
        
        # Using a session for better connection handling
        with requests.Session() as session:
            with session.post(
                f"{base_url}/v1/stream",
                json=payload,
                stream=True,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    # Process the streaming response
                    print("Receiving stream:")
                    print("-" * 40)
                    
                    full_response = ""
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            chunk_str = chunk.decode('utf-8')
                            print(chunk_str, end='', flush=True)
                            full_response += chunk_str
                    
                    print("\n" + "-" * 40)
                    elapsed = time.time() - start_time
                    print(f"Time taken: {elapsed:.2f} seconds")
                    print(f"Total response length: {len(full_response)} bytes")
                    return True
                else:
                    print(f"Error: {response.text}")
                    return False
                
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test the Granite4Nano-1B API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--test", choices=["all", "health", "generate", "chat", "function", "execute", "stream"], default="all",
                        help="Which test to run")
    args = parser.parse_args()
    
    base_url = args.url
    
    if args.test == "all" or args.test == "health":
        health_ok = test_health(base_url)
        if not health_ok:
            print("Health check failed. Make sure the API is running.")
            if args.test == "health":
                return
    
    if args.test == "all" or args.test == "generate":
        test_generate(base_url)
    
    if args.test == "all" or args.test == "chat":
        test_chat_completion(base_url)
    
    if args.test == "all" or args.test == "function":
        test_function_call(base_url)
    
    if args.test == "all" or args.test == "execute":
        test_execute_function(base_url)
        
    if args.test == "all" or args.test == "stream":
        test_stream(base_url)

if __name__ == "__main__":
    main()

# Made with Bob
