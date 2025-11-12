# Granite4Nano-1B Chat Interface & API

This is a FastAPI application that exposes the IBM Granite 4.0 1B model through both a modern chat interface and a REST API. The application allows you to interact with the model through a user-friendly web interface or programmatically via API endpoints.

## ⚠️ Important Performance Notes

### Document Processing Performance
**For optimal performance with large document OCR processing, GPU acceleration is highly recommended.** Processing large PDF documents, scanned images, or complex layouts requires significant computational resources. Without GPU acceleration, document processing may be slow, especially for:
- Multi-page PDF documents
- High-resolution scanned images
- Documents with complex layouts or tables
- Batch processing of multiple files

### Model Context Window Performance
**Granite 4.0 1B performs best with smaller contexts on CPU.** The model's performance characteristics vary significantly based on context size and hardware:

**CPU Performance:**
- ✅ **Optimal**: Short contexts (< 2,000 tokens) - Fast inference, low latency
- ⚠️ **Acceptable**: Medium contexts (2,000-8,000 tokens) - Slower but usable
- ❌ **Poor**: Large contexts (> 8,000 tokens) - Very slow, high memory usage

**GPU Performance:**
- ✅ **Excellent**: All context sizes up to model's maximum (32K tokens)
- ✅ **Fast inference** even with large document contexts
- ✅ **Low latency** for real-time streaming responses

**Recommended Setup:**
- **For Document Processing**: NVIDIA GPU with CUDA support, 8GB+ VRAM
- **For Large Context Windows**: GPU acceleration required for acceptable performance
- **For CPU-Only**: Limit document size to generate smaller contexts (< 2,000 tokens)

**CPU-Only Environment Best Practices:**
- Process smaller documents (< 5 pages)
- Use document summaries instead of full text
- Limit max_tokens parameter to reduce context size
- Enable document caching to avoid reprocessing
- Consider chunking large documents into smaller segments

## Features

### Chat Interface
- Modern, responsive chat interface similar to ChatGPT
- Real-time message streaming for a dynamic experience
- **📎 File Upload & Document Processing** (NEW)
  - Drag & drop file attachment with visual overlay
  - Support for PDF, DOCX, PPTX, XLSX, and images
  - Real-time file preview with status indicators
  - Automatic document processing with Docling
  - Context-aware responses based on document content
- Configurable model parameters through an intuitive settings panel
- Message history persistence using localStorage
- Markdown rendering in responses with syntax highlighting for code
- Light/dark mode toggle for user preference
- Mobile-responsive design with touch optimizations
- Smooth transition animations for all interactions
- Visual indicators for loading/processing states

### Document Processing System (NEW)
- **Docling Integration**: Advanced document conversion to markdown
- **Multi-Format Support**: PDF, DOCX, PPTX, XLSX, JPG, PNG, GIF, BMP, TIFF
- **Intelligent Caching**: 24-hour TTL cache for processed documents
- **Automatic Cleanup**: 1-hour retention for uploaded files
- **Parallel Processing**: Handle multiple files simultaneously
- **Context Injection**: Extracted document content enhances LLM responses
- **File Validation**: Size limits (50MB), type checking, duplicate detection
- **Background Jobs**: Scheduled cleanup tasks for storage management

### API
- Text generation endpoint with configurable parameters
- OpenAI-compatible chat completion endpoint
- **File upload endpoint with document processing** (NEW)
- Function calling capabilities
- Real-time streaming response endpoint
- Asynchronous processing
- Proper error handling
- API documentation via Swagger UI

## Requirements

- Python 3.8+
- PyTorch (with CUDA support recommended for document processing)
- Transformers
- FastAPI
- Uvicorn
- **Docling** (for document processing)
- **Additional dependencies**: aiofiles, python-multipart, diskcache, APScheduler

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

**Note:** For GPU-accelerated document processing, ensure you have:
- NVIDIA GPU with CUDA support
- CUDA toolkit installed
- PyTorch with CUDA support: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`

3. Configure environment variables (optional):

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` to customize:
- `MAX_FILE_SIZE_MB`: Maximum file upload size (default: 50)
- `UPLOAD_DIR`: Directory for temporary file storage (default: ./uploads)
- `CACHE_DIR`: Directory for document cache (default: ./cache)
- `ALLOWED_EXTENSIONS`: Comma-separated list of allowed file extensions

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
- **Attach and process documents** (drag & drop or click attach button)
- View responses with proper markdown formatting
- Configure model parameters via the settings panel
- Toggle between light and dark mode
- Start new conversations
- Access your chat history

### Using File Upload in Chat Interface

The chat interface now supports document uploads for context-aware conversations:

1. **Attach Files:**
   - **Drag & Drop**: Drag files from your desktop onto the browser window - a drop zone will appear
   - **Attach Button**: Click the paperclip icon next to the message input
   - **Supported Formats**: PDF, DOCX, PPTX, XLSX, JPG, PNG, GIF, BMP, TIFF

2. **Preview Files:**
   - Attached files appear in a preview list with icons, names, and sizes
   - Status indicators show: Pending → Processing → Success/Error
   - Remove individual files or clear all before sending

3. **Send Message:**
   - Type your question or prompt about the documents
   - Click send or press Enter
   - Files are automatically processed and used as context

4. **Receive Response:**
   - The AI analyzes your documents and generates a response
   - Responses reference the document content
   - Files are automatically cleared after successful submission

**Example Use Cases:**
- "Summarize this PDF report"
- "What are the key findings in this research paper?"
- "Extract the data from this spreadsheet"
- "Analyze the content of these images"
- "Compare these two documents"

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

### File Upload with Document Processing (NEW)

```
POST /v1/chat/upload
```

Upload and process documents (PDF, DOCX, PPTX, XLSX, images) to generate context-aware responses.

**Request:** Multipart form data

**Form Fields:**
- `prompt` (string, required): The user's question or message
- `files` (file[], required): One or more document files to process
- `max_tokens` (integer, optional): Maximum tokens to generate (default: 100)
- `temperature` (float, optional): Sampling temperature (default: 0.7)
- `top_p` (float, optional): Nucleus sampling parameter (default: 0.9)
- `top_k` (integer, optional): Top-k sampling parameter (default: 50)
- `system_prompt` (string, optional): Custom system prompt

**Supported File Formats:**
- **Documents**: PDF, DOCX, PPTX, XLSX
- **Images**: JPG, JPEG, PNG, GIF, BMP, TIFF
- **Size Limit**: 50MB per file

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
        "content": "Based on the document you provided..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 250,
    "completion_tokens": 150,
    "total_tokens": 400
  },
  "file_processing_info": {
    "files_processed": 1,
    "total_processing_time": 2.5,
    "cache_hits": 0,
    "documents": [
      {
        "filename": "report.pdf",
        "pages": 5,
        "processing_time": 2.5,
        "cached": false
      }
    ]
  }
}
```

**Example using cURL:**

```bash
curl -X POST "http://localhost:8000/v1/chat/upload" \
  -F "prompt=Summarize this document" \
  -F "files=@document.pdf" \
  -F "max_tokens=200" \
  -F "temperature=0.7"
```

**Example using Python:**

```python
import requests

url = "http://localhost:8000/v1/chat/upload"
files = {"files": open("document.pdf", "rb")}
data = {
    "prompt": "What are the key points in this document?",
    "max_tokens": 200,
    "temperature": 0.7
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Document Processing Features:**
- Automatic text extraction from PDFs and Office documents
- OCR for scanned images and PDFs
- Table and layout preservation
- Intelligent caching (24-hour TTL)
- Parallel processing for multiple files
- Automatic cleanup after 1 hour

## Error Handling

The API includes proper error handling for various scenarios:

- 400 Bad Request: Invalid input parameters
- 500 Internal Server Error: Error during text generation
- 503 Service Unavailable: Model not loaded

## Performance Considerations

### Model Performance
- The model is loaded at startup and kept in memory
- The API supports asynchronous processing for better performance
- The model runs on GPU if available, otherwise falls back to CPU

### Document Processing Performance
- **GPU Acceleration Highly Recommended**: Document OCR and processing is computationally intensive
- **Caching**: Processed documents are cached for 24 hours to avoid reprocessing
- **Parallel Processing**: Multiple files are processed simultaneously
- **Automatic Cleanup**: Uploaded files are deleted after 1 hour to save disk space
- **File Size Limits**: 50MB per file to prevent memory issues

**Performance Tips:**
- Use GPU acceleration for processing large documents (10+ pages)
- Enable caching to speed up repeated queries on the same documents
- Process smaller batches of files for faster response times
- Pre-process documents to text format when possible for CPU-only environments

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.