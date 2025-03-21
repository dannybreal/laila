from typing import Dict, Optional, List, AsyncGenerator, Any
import os
from openai import OpenAI
import logging
from datetime import datetime
import asyncio
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantManager:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
        self.user_threads: Dict[str, str] = {}  # Lightweight cache of user_id -> thread_id
        self.rate_limit_delay = 2  # seconds between API calls
        self.max_retries = 15
        self.retry_delay = 2
        self.poll_interval = 0.5

    async def check_quota(self) -> bool:
        """Check if we have available API quota using a lightweight check"""
        try:
            self.client.models.list(limit=1)
            return True
        except Exception as e:
            error_msg = str(e)
            if "exceeded your current quota" in error_msg.lower():
                logger.error("API quota exceeded")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "quota_exceeded",
                        "message": "API quota exceeded. Please try again later or contact support.",
                        "docs_url": "https://platform.openai.com/account/billing"
                    }
                )
            return False

    async def get_or_create_thread(self, user_id: str) -> str:
        """Get existing thread or create new one for user"""
        if user_id in self.user_threads:
            # Verify thread still exists
            try:
                self.client.beta.threads.retrieve(self.user_threads[user_id])
                return self.user_threads[user_id]
            except:
                del self.user_threads[user_id]

        # Create new thread
        await self.check_quota()
        thread = self.client.beta.threads.create()
        self.user_threads[user_id] = thread.id
        logger.info(f"Created new thread for user {user_id}: {thread.id}")
        return thread.id

    async def get_conversation_history(self, user_id: str, limit: int = 100) -> List[dict]:
        """Get conversation history directly from OpenAI"""
        try:
            thread_id = await self.get_or_create_thread(user_id)
            if not thread_id:
                return []
                
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=min(limit, 100)  # Cap at 100 messages
            )
            
            history = []
            for msg in messages.data:
                history.append({
                    "role": msg.role,
                    "content": msg.content[0].text.value if msg.content else "",
                    "message_id": msg.id,
                    "created_at": msg.created_at
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_message_by_id(self, user_id: str, message_id: str) -> Optional[dict]:
        """Get a specific message directly from OpenAI"""
        try:
            thread_id = await self.get_or_create_thread(user_id)
            if not thread_id:
                return None
            
            message = self.client.beta.threads.messages.retrieve(
                thread_id=thread_id,
                message_id=message_id
            )
            
            if message:
                return {
                    "role": message.role,
                    "content": message.content[0].text.value if message.content else "",
                    "message_id": message.id,
                    "created_at": message.created_at
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting message: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_run_status(self, thread_id: str, run_id: str) -> dict:
        """Handle run status checks with adaptive polling"""
        retry_count = 0
        initial_delay = 1
        max_delay = 10
        
        while retry_count < self.max_retries:
            try:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run_status.status == "completed":
                    # Get the latest message
                    messages = self.client.beta.threads.messages.list(
                        thread_id=thread_id,
                        order="desc",
                        limit=1
                    )
                    if not messages.data:
                        raise Exception("No messages found after completion")
                    
                    latest_message = messages.data[0]
                    return {
                        "response": latest_message.content[0].text.value if latest_message.content else "",
                        "thread_id": thread_id,
                        "message_id": latest_message.id,
                        "timestamp": datetime.now().isoformat(),
                        "status": "completed"
                    }
                
                elif run_status.status == "failed":
                    error_msg = getattr(run_status, 'last_error', {}).get('message', 'Unknown error')
                    if "exceeded your current quota" in error_msg.lower():
                        raise HTTPException(
                            status_code=429,
                            detail={
                                "error": "quota_exceeded",
                                "message": "API quota exceeded",
                                "docs_url": "https://platform.openai.com/account/billing"
                            }
                        )
                    raise Exception(f"Assistant run failed: {error_msg}")
                
                # Adaptive polling based on status
                if run_status.status == "queued":
                    delay = min(initial_delay * (1.5 ** retry_count), max_delay)
                    logger.info(f"Run queued. Waiting {delay}s before next check.")
                    await asyncio.sleep(delay)
                else:
                    delay = min(initial_delay * (2 ** retry_count), max_delay)
                    logger.info(f"Run status: {run_status.status}. Waiting {delay}s before next check.")
                    await asyncio.sleep(delay)
                
                retry_count += 1
                
            except Exception as e:
                if "rate_limit" in str(e).lower():
                    retry_count += 1
                    if retry_count < self.max_retries:
                        delay = self.retry_delay * (2 ** retry_count)
                        logger.warning(f"Rate limited. Waiting {delay}s before retry {retry_count + 1}")
                        await asyncio.sleep(delay)
                        continue
                raise

        logger.error(f"Run timed out after {self.max_retries} retries")
        raise HTTPException(status_code=504, detail="Request timed out")

    async def send_message(self, user_id: str, message: str) -> dict:
        """Send a message and get the response"""
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                # Get or create thread
                thread_id = await self.get_or_create_thread(user_id)
                
                # Add delay between API calls
                await asyncio.sleep(self.rate_limit_delay)
                
                # Create message
                self.client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=message
                )
                
                # Add delay between API calls
                await asyncio.sleep(self.rate_limit_delay)
                
                # Create run
                run = self.client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=self.assistant_id
                )
                
                # Handle run status and get response
                return await self.handle_run_status(thread_id, run.id)
                
            except Exception as e:
                if "rate_limit" in str(e).lower():
                    retry_count += 1
                    if retry_count <= self.max_retries:
                        await asyncio.sleep(self.rate_limit_delay * (2 ** retry_count))
                        continue
                    
                logger.error(f"Error in send_message: {str(e)}")
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(status_code=500, detail=str(e))

    async def delete_thread(self, user_id: str):
        """Delete user's thread from OpenAI and local cache"""
        if user_id in self.user_threads:
            thread_id = self.user_threads[user_id]
            try:
                self.client.beta.threads.delete(thread_id)
                del self.user_threads[user_id]
                logger.info(f"Deleted thread for user {user_id}")
            except Exception as e:
                logger.error(f"Error deleting thread: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

    async def stream_run_status(self, thread_id: str, run_id: str) -> AsyncGenerator[dict, None]:
        """Stream run status and messages as they become available"""
        retry_count = 0
        last_message_id = None
        
        while retry_count < self.max_retries:
            try:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run_status.status in ["completed", "requires_action", "failed"]:
                    messages = self.client.beta.threads.messages.list(
                        thread_id=thread_id,
                        order="desc",
                        limit=1
                    )
                    
                    if messages.data and messages.data[0].id != last_message_id:
                        last_message_id = messages.data[0].id
                        yield {
                            "response": messages.data[0].content[0].text.value,
                            "thread_id": thread_id,
                            "message_id": messages.data[0].id,
                            "timestamp": datetime.now().isoformat(),
                            "status": run_status.status
                        }
                        
                        if run_status.status == "completed":
                            break
                
                await asyncio.sleep(self.poll_interval)
                retry_count += 1
                
            except Exception as e:
                if "rate_limit" in str(e).lower():
                    retry_count += 1
                    if retry_count < self.max_retries:
                        await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                        continue
                raise

    async def send_message_stream(self, user_id: str, message: str) -> AsyncGenerator[dict, None]:
        """Send message to assistant and stream the response"""
        try:
            # Get or create thread for user
            thread_id = await self.get_or_create_thread(user_id)
            
            # Add message to thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            # Run assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            # Stream the response
            async for response in self.stream_run_status(thread_id, run.id):
                yield response
                
        except Exception as e:
            logger.error(f"Error in send_message_stream: {str(e)}")
            if "exceeded your current quota" in str(e).lower():
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "quota_exceeded",
                        "message": "API quota exceeded",
                        "docs_url": "https://platform.openai.com/account/billing"
                    }
                )
            raise HTTPException(status_code=500, detail=str(e)) 