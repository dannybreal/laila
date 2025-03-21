from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import OpenAI
import os
from dotenv import load_dotenv
import asyncio
import time
import logging
from assistant_manager import AssistantManager
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Custom exception handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": str(exc)}
    )

# Add CORS middleware with all origins allowed for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model configuration
MODEL_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.9,
}

# Assistant configuration
ASSISTANT_CONFIG = {
    "assistant_id": os.getenv("OPENAI_ASSISTANT_ID"),
    "model": "gpt-4-turbo-preview",
}

# Initialize AssistantManager
assistant_manager = AssistantManager()

class ChatRequest(BaseModel):
    message: str
    user_id: str
    thread_id: Optional[str] = None

@app.get("/api/health")
async def health_check():
    return JSONResponse(content={
        "status": "healthy",
        "assistant_id": os.getenv("OPENAI_ASSISTANT_ID")
    })

@app.post("/api/chat")
async def chat_with_assistant(request: ChatRequest):
    """Chat with the assistant"""
    try:
        response = await assistant_manager.send_message(
            user_id=request.user_id,
            message=request.message
        )
        return JSONResponse(content=response)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in chat endpoint: {error_msg}")
        
        # Handle different types of errors
        if "rate limit" in error_msg.lower():
            return JSONResponse(
                status_code=429, 
                content={"error": "rate_limited", "message": "Rate limit exceeded. Please try again later."}
            )
        elif "quota exceeded" in error_msg.lower():
            return JSONResponse(
                status_code=429, 
                content={"error": "quota_exceeded", "message": "API quota exceeded. Please try again later."}
            )
        elif "not found" in error_msg.lower():
            return JSONResponse(
                status_code=404, 
                content={"error": "not_found", "message": error_msg}
            )
        else:
            return JSONResponse(
                status_code=500, 
                content={"error": "server_error", "message": error_msg}
            )

@app.get("/api/chat/history/{user_id}")
async def get_chat_history(
    user_id: str,
    limit: int = Query(default=100, le=1000, gt=0)
):
    """Get conversation history for a user"""
    try:
        history = await assistant_manager.get_conversation_history(
            user_id=user_id,
            limit=limit
        )
        return JSONResponse(content=history)
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "message": str(e)}
        )

@app.get("/api/chat/message/{user_id}/{message_id}")
async def get_message(user_id: str, message_id: str):
    """Get a specific message from a user's conversation"""
    try:
        message = await assistant_manager.get_message_by_id(
            user_id=user_id,
            message_id=message_id
        )
        return JSONResponse(content=message)
    except Exception as e:
        logger.error(f"Error getting message: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "message": str(e)}
        )

@app.delete("/api/thread/{user_id}")
async def delete_user_thread(user_id: str):
    """Delete a user's thread"""
    try:
        await assistant_manager.delete_thread(user_id)
        return JSONResponse(content={"status": "success", "message": f"Thread deleted for user {user_id}"})
    except Exception as e:
        logger.error(f"Error deleting thread: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "message": str(e)}
        )

@app.post("/api/chat/stream")
async def chat_with_assistant_stream(request: ChatRequest):
    """Chat with the assistant with streaming response"""
    try:
        async def generate_responses():
            try:
                async for response in assistant_manager.send_message_stream(
                    user_id=request.user_id,
                    message=request.message
                ):
                    yield f"data: {json.dumps(response)}\n\n"
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error in stream generation: {error_msg}")
                yield f"data: {json.dumps({'error': 'stream_error', 'message': error_msg})}\n\n"
                
        return StreamingResponse(
            generate_responses(),
            media_type="text/event-stream"
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in chat stream endpoint: {error_msg}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "message": error_msg}
        )

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 