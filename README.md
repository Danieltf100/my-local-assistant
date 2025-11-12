# Granite4Nano-1B Chat Interface & API

This is a FastAPI application that exposes the IBM Granite 4.0 1B model through both a modern chat interface and a REST API. The application allows you to interact with the model through a user-friendly web interface or programmatically via API endpoints.

## Features

### Chat Interface
- Modern, responsive chat interface similar to ChatGPT
- Real-time message streaming for a dynamic experience
- Configurable model parameters through an intuitive settings panel
- Message history persistence using localStorage
- Markdown rendering in responses with syntax highlighting for code
- Light/dark mode toggle for user preference
- Mobile-responsive design with touch optimizations
- Smooth transition animations for all interactions
- Visual indicators for loading/processing states

### API
- Text generation endpoint with configurable parameters
- OpenAI-compatible chat completion endpoint
- Function calling capabilities
- Real-time streaming response endpoint
- Asynchronous processing
- Proper error handling
- API documentation via Swagger UI

## Requirements

- Python 3.8+
- PyTorch
- Transformers
- FastAPI
- Uvicorn

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

Run the following command to start the server:

```bash
python app.py
```

This will start the server on `http://0.0.0.0:8000`.

Alternatively, you can use Uvicorn directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Accessing the Chat Interface

Once the server is running, you can access the chat interface by opening your browser and navigating to:

```
http://localhost:8000/
```

This will open the chat interface where you can:
- Send messages to the model
- View responses with proper markdown formatting
- Configure model parameters via the settings panel
- Toggle between light and dark mode
- Start new conversations
- Access your chat history

### API Documentation

If you prefer to use the API directly, you can access the API documentation at:

```
http://localhost:8000/docs
```

This will open the Swagger UI where you can explore and test all available endpoints.

## API Endpoints

### Health Check

```
GET /health
```

Returns the status of the API and model.

### Text Generation

```
POST /generate
```

Generate text based on a prompt with configurable parameters.

**Request Body:**

```json
{
  "prompt": "Do you know who you are?",
  "max_tokens": 100,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 50,
  "repetition_penalty": 1.1,
  "do_sample": true,
  "num_return_sequences": 1
}
```

**Parameters:**

- `prompt` (string, required): The text prompt to generate from
- `max_tokens` (integer, default: 100): Maximum number of tokens to generate (1-1000)
- `temperature` (float, default: 1.0): Sampling temperature (0.0-2.0)
- `top_p` (float, default: 1.0): Nucleus sampling parameter (0.0-1.0)
- `top_k` (integer, optional): Top-k sampling parameter
- `repetition_penalty` (float, optional): Repetition penalty
- `do_sample` (boolean, default: true): Whether to use sampling or greedy decoding
- `num_return_sequences` (integer, default: 1): Number of sequences to return (1-5)

**Response:**

```json
{
  "generated_text": "I am an AI assistant based on the IBM Granite 4.0 1B model...",
  "execution_time": 1.23,
  "model_name": "ibm-granite/granite-4.0-1b",
  "prompt": "Do you know who you are?",
  "parameters": {
    "max_tokens": 100,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 50,
    "repetition_penalty": 1.1,
    "do_sample": true,
    "num_return_sequences": 1
  }
}
```

### OpenAI-Compatible Chat Completion

```
POST /v1/chat/completions
```

An endpoint that mimics the OpenAI chat completion API format for easier integration with existing applications.

**Request Body:**

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Do you know who you are?"}
  ],
  "max_tokens": 100,
  "temperature": 0.7,
  "top_p": 0.9
}
```

**Response:**

```json
{
  "id": "chatcmpl-1234567890",
  "object": "chat.completion",
  "created": 1698765432,
  "model": "ibm-granite/granite-4.0-1b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I am an AI assistant based on the IBM Granite 4.0 1B model..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 30,
    "total_tokens": 50
  }
}
```

### Function Calling

```
POST /v1/function_call
```

An endpoint for function calling capabilities.

**Request Body:**

```json
{
  "messages": [
    {"role": "user", "content": "What's the weather like in Boston right now?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_current_weather",
        "description": "Get the current weather for a specified city.",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "Name of the city"
            }
          },
          "required": ["city"]
        }
      }
    }
  ],
  "max_tokens": 100,
  "temperature": 0.7
}
```

**Response:**

```json
{
  "id": "funcall-1234567890",
  "object": "function.call",
  "created": 1698765432,
  "model": "ibm-granite/granite-4.0-1b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I need to get the current weather for Boston..."
      }
    }
  ]
}
```

## Error Handling

The API includes proper error handling for various scenarios:

- 400 Bad Request: Invalid input parameters
- 500 Internal Server Error: Error during text generation
- 503 Service Unavailable: Model not loaded

## Performance Considerations

- The model is loaded at startup and kept in memory
- The API supports asynchronous processing for better performance
- The model runs on GPU if available, otherwise falls back to CPU

## Chat Interface Features

### Real-time Message Streaming
The chat interface supports real-time message streaming, showing the model's response as it's being generated, token by token. This provides a more interactive and engaging experience compared to waiting for the complete response.

### Configurable Model Parameters
The settings panel allows you to customize various model parameters:
- **Temperature**: Controls randomness (0.0-2.0)
- **Max Tokens**: Limits the length of generated responses
- **Top P**: Nucleus sampling parameter for controlling diversity
- **Top K**: Limits vocabulary to top K most likely tokens
- **Streaming**: Toggle real-time response streaming
- **Save History**: Toggle chat history persistence

### Message History
Your conversations are automatically saved to your browser's localStorage (if enabled in settings). This allows you to:
- Access previous conversations
- Continue conversations where you left off
- Start new conversations without losing history

### Responsive Design
The interface is fully responsive and works well on:
- Desktop computers
- Tablets
- Mobile phones

Special touch-optimized controls are provided for mobile devices.

### Markdown and Code Support
The chat interface supports:
- Full markdown rendering for rich text formatting
- Syntax highlighting for code blocks
- Tables, lists, and other formatting elements

### Accessibility Features
- Light/dark mode toggle for different lighting conditions
- Keyboard shortcuts for common actions
- Responsive design for various screen sizes

## Testing

A test script is provided to verify that the API is working correctly. You can run it with:

```bash
python test_api.py
```

This will test all endpoints. You can also test specific endpoints:

```bash
# Test only the health endpoint
python test_api.py --test health

# Test only the text generation endpoint
python test_api.py --test generate

# Test only the chat completion endpoint
python test_api.py --test chat

# Test only the function call endpoint
python test_api.py --test function
```

If your API is running on a different URL, you can specify it:

```bash
python test_api.py --url http://your-api-url:port
```

## License

[Specify your license here]