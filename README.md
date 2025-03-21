# Laila Self Guide Chat API

A FastAPI application that provides a REST API for integrating OpenAI's Assistant API (GPT-4) with Webflow sites, specifically built for the Laila Self Guide chatbot experience.

## Features

- **OpenAI Assistant Integration**: Connects to OpenAI's Assistants API, allowing for specialized, context-aware conversations
- **User Thread Management**: Maintains separate conversation threads for each user
- **Chat History**: Retrieves and preserves conversation history
- **Rate Limit Handling**: Implements retry mechanisms and exponential backoff for API rate limits
- **Streaming Responses**: Supports streaming responses for real-time chat experiences
- **CORS Support**: Configured to work with Webflow sites

## Requirements

- Python 3.8+
- OpenAI API key with access to the Assistants API
- An Assistant created in the OpenAI platform

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/laila-self-chat-api.git
cd laila-self-chat-api
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your OpenAI API key and Assistant ID:
```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ASSISTANT_ID=your_assistant_id_here
```

## Running Locally

To start the server locally:

```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000.

## API Endpoints

- **POST /api/chat**: Send a message to the assistant
- **GET /api/chat/history/{user_id}**: Get conversation history for a user
- **GET /api/chat/message/{user_id}/{message_id}**: Get a specific message
- **DELETE /api/thread/{user_id}**: Delete a user's thread
- **POST /api/chat/stream**: Chat with streaming response
- **GET /api/health**: Health check endpoint

## Testing

You can test the API with the included test scripts:

```bash
# Test with multiple users
python test_multiple_users.py

# Test concurrent requests (advanced)
python test_concurrent.py
```

## Deployment to Vercel

This API is designed to be deployed to Vercel for production use.

1. Install the Vercel CLI:
```bash
npm install -g vercel
```

2. Login to Vercel:
```bash
vercel login
```

3. Deploy:
```bash
vercel
```

4. Configure environment variables on Vercel:
   - Go to your project on the Vercel dashboard
   - Navigate to Settings > Environment Variables
   - Add the same variables from your `.env` file

## Web Integration

After deploying the API, you can integrate it with your Webflow site using the provided HTML template in `static/webflow-chat.html`. See the `static/webflow-integration-guide.md` for detailed instructions.

## Architecture

This application uses a simple and efficient architecture:

- **FastAPI**: Provides the web API framework
- **OpenAI API**: Handles the AI conversation capabilities
- **Built-in Thread Management**: Each user gets their own thread in OpenAI, with history maintained by OpenAI's system

The API supports handling multiple concurrent users, with each user's conversation history maintained separately.

## Configuration

Key configuration options in `assistant_manager.py`:

- `rate_limit_delay`: Seconds to wait between API calls (default: 2)
- `max_retries`: Maximum number of retries for API calls (default: 15)
- `retry_delay`: Initial delay for retries in seconds (default: 2)
- `poll_interval`: Interval for checking run status in seconds (default: 0.5)

## License

[MIT License](LICENSE)

## Support

For support, please open an issue on the GitHub repository. 