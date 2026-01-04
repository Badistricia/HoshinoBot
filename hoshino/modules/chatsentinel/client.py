import logging
import os
import httpx
from openai import AsyncOpenAI
from . import config

logger = logging.getLogger("hoshino.chatsentinel")

class GeminiClient:
    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model_name = model_name
        self.client = self._create_client()

    def _create_client(self):
        if not self.api_key:
            logger.error(f"API Key for {self.model_name} is missing.")
            return None

        # Gemini OpenAI Compatible Endpoint
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        
        http_client = None
        if config.PROXY_URL:
            logger.info(f"Using Proxy: {config.PROXY_URL}")
            # httpx >= 0.23.0 uses 'proxy' or 'proxies' depending on version?
            # Actually AsyncClient uses 'proxy' (singular) for a single proxy or 'proxies' (mounts).
            # But recent httpx versions deprecated 'proxies' in favor of 'proxy' or 'mounts'.
            # However, 'proxies' param was removed in newer versions or changed behavior.
            # Let's try passing it as 'proxy' if it's a simple string, or checking version.
            # For simplicity and compatibility, we can just set mount directly or use 'proxy' param if simple.
            # But AsyncOpenAI expects us to pass an AsyncClient.
            
            # Let's use 'proxy' parameter which is common in newer httpx for all-traffic proxy
            # Or 'proxies' (dict) was supported in older versions.
            # The error says "unexpected keyword argument 'proxies'", so it must be a version where it's removed or renamed.
            # In httpx 0.24+, it is 'proxy' or 'mounts'.
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
            logger.info(f"Sending request to Gemini ({self.model_name})...")
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=15.0
            )
            
            content = response.choices[0].message.content
            if content:
                logger.info(f"Gemini Response: {content[:50]}...")
                return content
            return ""
        except Exception as e:
            logger.error(f"Gemini API Error ({self.model_name}): {e}")
            return ""
