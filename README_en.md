# AnyRouter Transparent Proxy

A lightweight transparent HTTP proxy service based on FastAPI, specifically designed to resolve the 500 error issue with AnyRouter's Anthropic API in the Claude Code for VS Code plugin.

## Demo Screenshots

![Demo Screenshot](./screenshot/效果图.png)

![Dashboard Page](./screenshot/仪表板页面.png)


## Table of Contents

- [Core Features](#core-features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
  - [Docker Deployment (Recommended)](#docker-deployment-recommended)
  - [Local Setup](#local-setup)
- [Configuration](#configuration)
- [Core Functionality](#core-functionality)
- [Usage Example](#usage-example)
- [Architecture & Technology](#architecture--technology)
- [Security](#security)
- [Contributing](#contributing)

## Core Features

- **Fully Transparent** - Supports all HTTP methods, seamlessly proxies requests
- **Streaming Response** - Asynchronous architecture based on `httpx.AsyncClient`, perfect streaming support
- **Standards Compliant** - Strictly follows RFC 7230 specification, correctly handles HTTP headers
- **Flexible Configuration** - Supports environment variable configuration for target URL and System Prompt replacement
- **High Performance** - Connection pool reuse, asynchronous processing, efficiently handles concurrent requests
- **Intelligent Processing** - Automatically calculates Content-Length, avoiding protocol errors caused by request body modifications
- **Web Management Dashboard** - Provides real-time monitoring, statistics analysis, and configuration management

## Project Structure

```
AnyRouter-Transparent-Proxy/
├── backend/              # Backend service (FastAPI)
│   ├── app.py           # Core proxy logic
│   └── requirements.txt # Python dependencies
├── frontend/            # Frontend project (Vue 3 + TypeScript)
│   ├── src/            # Source code
│   ├── package.json    # Frontend dependencies
│   └── vite.config.ts  # Vite configuration
├── env/                 # Configuration files directory
│   ├── .env             # Environment variables config (copy from .env.example)
│   └── .env.headers.json # Custom request headers configuration
├── docs/                # Documentation
├── static/              # Frontend build artifacts (.gitignore)
├── Dockerfile           # Docker image build
├── docker-compose.yml   # Docker Compose configuration
├── .env.example         # Environment variable template
└── CLAUDE.md           # AI context index
```

**Notes**:
- `backend/` - Backend Python service, handles proxy logic and API processing
- `frontend/` - Frontend Vue project, provides Web management dashboard
- `static/` - Frontend build artifacts, automatically generated during Docker build, not committed to Git
- `env/` - Runtime configuration files directory

## Quick Start

### Docker Deployment (Recommended)

**Using Docker Compose:**

```bash
# Clone the project
git clone <repository-url>
cd AnyRouter-Transparent-Proxy

# Copy environment variable template (optional)
cp .env.example env/.env

# Edit env/.env file to modify configuration (optional)
# Default uses https://anyrouter.top

# Start the service
docker-compose up -d
# If you modified the source code after deployment, rebuild with --build --remove-orphans
docker-compose up -d --build --remove-orphans

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Restart the service
docker-compose down && docker-compose up -d
```

**Or using Docker commands:**

```bash
# Build and run
docker build -t anthropic-proxy .
docker run -d --name anthropic-proxy -p 8088:8088 anthropic-proxy

# Custom target URL
docker run -d --name anthropic-proxy -p 8088:8088 \
  -e API_BASE_URL=https://anyrouter.top \
  anthropic-proxy
```

The service will start at [http://localhost:8088](http://localhost:8088), then configure this address in Claude Code.

~~Access the management dashboard at [http://localhost:8088/admin](http://localhost:8088/admin).~~

The management dashboard can now be accessed directly from the homepage [http://localhost:8088](http://localhost:8088) with automatic redirection.

### Local Setup

**Requirements:** Python 3.7+

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Or install manually
pip install fastapi uvicorn httpx python-dotenv

# Copy environment variable template
cp env/.env.example env/.env

# Start the service (run from project root directory)
python -m backend.app
```

The service will start at [http://localhost:8088](http://localhost:8088).

**Note**: For local development, if you need to use the Web management dashboard, you need to build the frontend first:

```bash
cd frontend
npm install
npm run build
cd ..
```

The build artifacts will be output to the `static/` directory (this directory is ignored in `.gitignore`).

~~Access the management dashboard at [http://localhost:8088/admin](http://localhost:8088/admin).~~

The management dashboard can now be accessed directly from the homepage [http://localhost:8088](http://localhost:8088) with automatic redirection.

## Configuration

### Environment Variables

Create a `env/.env` file or set environment variables:

```bash
# API target address (default: https://anyrouter.top) or use reverse proxy address
API_BASE_URL=https://anyrouter.top

# System Prompt replacement (optional)
# Replaces the text content of the first element in the system array in the request body
SYSTEM_PROMPT_REPLACEMENT="You are Claude Code, Anthropic's official CLI for Claude."

# If you need to access through a proxy, please uncomment the two lines below and set the proxy address
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890

# Debug mode (default: false)
DEBUG_MODE=false

# Service port (default: 8088)
PORT=8088

# Enable Web management dashboard (default: true)
ENABLE_DASHBOARD=true

# Enable log persistence (default: true)
LOG_PERSISTENCE_ENABLED=true

# Log storage path (default: data/logs)
LOG_STORAGE_PATH=data/logs

# Log retention days (default: 7)
LOG_RETENTION_DAYS=7

# Daily log limit (default: 1000)
LOG_DAILY_LIMIT=1000
```

### Custom Request Headers (Optional)

You can configure custom request headers through the `env/.env.headers.json` file, which will be injected into all proxied requests.

**Configuration Steps:**

1. Copy the template file to create configuration:
   ```bash
   cp .env.headers.json.example env/.env.headers.json
   ```

2. Edit the `env/.env.headers.json` file and add the headers you need:
   ```json
   {
     "User-Agent": "claude-cli/2.0.8 (external, cli)"
   }
   ```

3. Restart the service for the configuration to take effect

**Notes:**
- Configuration file uses standard JSON format
- Fields starting with `__` will be ignored (can be used for comments)
- If the file doesn't exist, defaults to empty configuration `{}`
- Custom request headers will override headers with the same name in the original request

> Note: Service restart required after configuration changes

## Core Functionality

### System Prompt Replacement

Dynamically replaces the `text` content of the first element in the `system` array in Anthropic API request bodies:

- Customize Claude Code CLI behavior
- Adjust Claude Agent SDK responses
- Uniformly inject system-level prompts

Enable this feature by configuring the `SYSTEM_PROMPT_REPLACEMENT` variable.

### Intelligent Request Header Handling

- **Automatic Filtering** - Removes hop-by-hop headers (Connection, Keep-Alive, etc.)
- **Host Rewriting** - Automatically rewrites to target server domain
- **Content-Length Auto-calculation** - Automatically calculates based on actual content, avoiding length mismatches
- **Custom Injection** - Supports overriding or adding arbitrary request headers
- **IP Tracking** - Automatically maintains X-Forwarded-For chain

## Usage Example

Change requests originally pointing to `anyrouter.top` or other APIs to point to the proxy service:

```bash
# Original request
curl https://anyrouter.top/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model": "claude-3-5-sonnet-20241022", "messages": [...]}'

# Through proxy
curl http://localhost:8088/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model": "claude-3-5-sonnet-20241022", "messages": [...]}'
```

## Architecture & Technology

### Request Processing Flow

```
Client Request
    ↓
proxy() catches route
    ↓
filter_request_headers() filters request headers
    ↓
process_request_body() processes request body (optional system prompt replacement)
    ↓
Rewrite Host header + Inject custom headers + Add X-Forwarded-For
    ↓
httpx.AsyncClient initiates upstream request via build_request() + send(stream=True)
    ↓
filter_response_headers() filters response headers
    ↓
StreamingResponse streams back to client with BackgroundTask for automatic connection cleanup
```

### Key Technologies

- **Routing** - `@app.api_route("/{path:path}")` catches all paths and HTTP methods
- **Lifecycle Management** - Uses FastAPI lifespan events to manage HTTP client lifecycle
- **Connection Pool Reuse** - Globally shared `httpx.AsyncClient` for connection reuse
- **Asynchronous Requests** - 60-second timeout, supports long-running streaming responses
- **Streaming Transfer** - `build_request()` + `send(stream=True)` + `aiter_bytes()` + `BackgroundTask` efficiently handles large payloads with automatic connection lifecycle management
- **Header Filtering** - RFC 7230 compliant, bidirectional filtering of hop-by-hop headers

### Technical Details

**Request Header Filtering Rules (RFC 7230):**

Removed headers: Connection, Keep-Alive, Proxy-Authenticate, Proxy-Authorization, TE, Trailers, Transfer-Encoding, Upgrade, Content-Length (automatically recalculated by httpx)

**System Prompt Replacement Logic:**

1. Check `SYSTEM_PROMPT_REPLACEMENT` configuration
2. Parse request body as JSON
3. Verify `system` field exists and is a non-empty array
4. Replace `system[0].text` content
5. Re-serialize to JSON

Falls back to original request body on failure, ensuring service stability.

**HTTP Client Lifecycle:**

- Creates shared `httpx.AsyncClient` instance on startup
- All requests reuse the same client during runtime, benefiting from connection pooling
- Gracefully releases all connection resources on shutdown

### Log Output Example

```
[Proxy] Original body (123 bytes): {...}
[System Replacement] Successfully parsed JSON body
[System Replacement] Original system[0].text: You are Claude Code...
[System Replacement] Replaced with: 你是一个有用的AI助手
[System Replacement] Successfully modified body (original size: 123 bytes, new size: 145 bytes)
```

## Security

- **Redirect Attack Prevention** - `follow_redirects=False`
- **Request Timeout** - 60-second timeout prevents resource exhaustion
- **Error Handling** - Returns 502 status code when upstream request fails
- **Automatic Fault Tolerance** - Content-Length auto-calculation avoids protocol errors
- **Connection Management** - Shared client pool ensures connections are properly closed
- **Logging** - Detailed debugging information (recommend removing sensitive info in production)

## Contributing

Issues and Pull Requests are welcome!

---

**Note**: This project is for learning and development testing purposes only. Please ensure compliance with the terms of service of related services.
