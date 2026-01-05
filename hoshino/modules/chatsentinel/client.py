import logging
import os
import httpx
from openai import AsyncOpenAI
from . import config

logger = logging.getLogger("hoshino.chatsentinel")

class APIClient:
    def __init__(self, api_key, model_name, base_url=None):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.client = self._create_client()

    def _create_client(self):
        if not self.api_key:
            logger.error(f"API Key for {self.model_name} is missing.")
            return None

        # Default to Gemini if not specified (backward compatibility)
        # But we prefer explicit base_url
        base_url = self.base_url if self.base_url else "https://generativelanguage.googleapis.com/v1beta/openai/"
        
        http_client = None
        if config.PROXY_URL:
            logger.info(f"Using Proxy: {config.PROXY_URL}")
            # Use 'proxy' parameter which is common in newer httpx for all-traffic proxy
            http_client = httpx.AsyncClient(proxy=config.PROXY_URL)
        
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url,
            http_client=http_client
        )

    async def generate(self, prompt: str) -> str:
        if not self.client:
            logger.error("Client not initialized (Missing API Key).")
            return ""

        try:
            # logger.info(f"Sending request to API ({self.model_name})...")
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=15.0,
                temperature=1.3 # High temperature for creative/varied judging? Or low for stability?
                # Judge needs to be consistent. 1.3 is high (from aichat default). 
                # DeepSeek V3 recommends 1.3? Let's use default or 0.7 for Judge.
                # But aichat config uses 1.3. Let's stick to default 1.0 or explicit.
            )
            
            content = response.choices[0].message.content
            if content:
                # logger.info(f"API Response: {content[:50]}...")
                return content
            return ""
        except Exception as e:
            logger.error(f"API Error ({self.model_name}): {e}")
            return ""
