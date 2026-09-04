"""LLM service for exam generation using Groq API with OpenRouter fallback."""

import logging
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, timedelta
import json

from openai import AsyncOpenAI
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """
    LLM service abstraction for exam generation.
    
    Primary: Groq API (cost-effective, OpenAI-compatible)
    Fallback: OpenRouter (multiple models)
    
    Groq Rate Limits (Developer Plan):
    - llama-3.3-70b-versatile: 30 RPM, 1K RPD, 12K TPM, 100K TPD
    - llama-3.1-8b-instant: 30 RPM, 14.4K RPD, 6K TPM, 500K TPD
    """
    
    # Groq models with rate limits
    GROQ_MODELS = {
        "llama-3.3-70b-versatile": {
            "rpm": 30,  # Requests per minute
            "rpd": 1000,  # Requests per day
            "tpm": 12000,  # Tokens per minute
            "tpd": 100000,  # Tokens per day
            "cost_per_1k_tokens": 0.0005,  # Estimated cost in USD
        },
        "llama-3.1-8b-instant": {
            "rpm": 30,
            "rpd": 14400,
            "tpm": 6000,
            "tpd": 500000,
            "cost_per_1k_tokens": 0.0002,
        },
    }
    
    # Default model for exam generation
    DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        groq_base_url: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
    ):
        """
        Initialize LLM service.
        
        Args:
            groq_api_key: Groq API key (uses env var if not provided)
            groq_base_url: Groq base URL (uses env var if not provided)
            openrouter_api_key: OpenRouter API key for fallback
        """
        # Initialize Groq client (OpenAI-compatible)
        self.groq_api_key = groq_api_key or settings.groq_api_key
        self.groq_base_url = groq_base_url or settings.groq_base_url
        
        if self.groq_api_key:
            self.groq_client = AsyncOpenAI(
                api_key=self.groq_api_key,
                base_url=self.groq_base_url,
                timeout=settings.llm_timeout_seconds,
                max_retries=1,
            )
            logger.info(f"✅ Groq API client initialized: {self.groq_base_url}")
        else:
            self.groq_client = None
            logger.warning("⚠️ Groq API key not provided")
        
        # Initialize OpenRouter client for fallback
        self.openrouter_api_key = openrouter_api_key or getattr(settings, 'openrouter_api_key', None)
        
        if self.openrouter_api_key:
            self.openrouter_client = AsyncOpenAI(
                api_key=self.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=settings.llm_timeout_seconds,
                max_retries=1,
            )
            logger.info("✅ OpenRouter fallback client initialized")
        else:
            self.openrouter_client = None
            logger.warning("⚠️ OpenRouter API key not provided (no fallback)")
        
        # Rate limiting tracking (simple in-memory for MVP)
        self._request_times: List[datetime] = []
        self._token_usage: Dict[str, int] = {}
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_fallback_on_error: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate text using LLM (Groq primary, OpenRouter fallback).
        
        Args:
            prompt: The prompt to send to the LLM
            model: Model to use (default: llama-3.3-70b-versatile)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            use_fallback_on_error: Use OpenRouter if Groq fails
            
        Returns:
            Dict with:
                - content: Generated text
                - model: Model used
                - tokens_used: Total tokens consumed
                - cost: Estimated cost in USD
                - provider: "groq" or "openrouter"
                
        Raises:
            ValueError: If generation fails
        """
        model = model or self.DEFAULT_GROQ_MODEL
        
        # Try Groq first
        if self.groq_client:
            try:
                # Check rate limits
                await self._check_rate_limits(model)
                
                logger.info(f"Generating with Groq model: {model}")
                
                response = await self.groq_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                # Extract response
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
                
                # Calculate cost
                cost = self._calculate_cost(model, tokens_used, "groq")
                
                # Track usage
                self._track_usage(tokens_used)
                
                logger.info(f"✅ Groq generation successful: {tokens_used} tokens, ${cost:.4f}")
                
                return {
                    "content": content,
                    "model": model,
                    "tokens_used": tokens_used,
                    "cost": cost,
                    "provider": "groq",
                }
                
            except Exception as e:
                logger.error(f"âŒ Groq generation failed: {str(e)}")
                
                if not use_fallback_on_error or not self.openrouter_client:
                    raise ValueError(f"Groq generation failed: {str(e)}")
                
                logger.warning("âš ï¸ Falling back to OpenRouter...")
        
        # Fallback to OpenRouter
        if self.openrouter_client:
            try:
                logger.info("Generating with OpenRouter fallback")
                
                response = await self.openrouter_client.chat.completions.create(
                    model="meta-llama/llama-3.1-70b-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
                cost = self._calculate_cost("llama-3.1-70b", tokens_used, "openrouter")
                
                logger.info(f"✅ OpenRouter generation successful: {tokens_used} tokens, ${cost:.4f}")
                
                return {
                    "content": content,
                    "model": "meta-llama/llama-3.1-70b-instruct",
                    "tokens_used": tokens_used,
                    "cost": cost,
                    "provider": "openrouter",
                }
                
            except Exception as e:
                logger.error(f"âŒ OpenRouter generation failed: {str(e)}")
                raise ValueError(f"All LLM providers failed: {str(e)}")
        
        raise ValueError("No LLM provider available")
    
    async def _check_rate_limits(self, model: str) -> None:
        """
        Check if we're within rate limits for the model.
        
        Args:
            model: Model to check limits for
            
        Raises:
            ValueError: If rate limit exceeded
        """
        if model not in self.GROQ_MODELS:
            return
        
        limits = self.GROQ_MODELS[model]
        now = datetime.now()
        
        # Clean old request times (older than 1 minute)
        self._request_times = [
            t for t in self._request_times
            if (now - t).total_seconds() < 60
        ]
        
        # Check RPM (Requests Per Minute)
        if len(self._request_times) >= limits["rpm"]:
            wait_time = 60 - (now - self._request_times[0]).total_seconds()
            logger.warning(f"⚠️ Rate limit approaching: {len(self._request_times)}/{limits['rpm']} RPM")
            
            if wait_time > 0:
                logger.info(f"⏳ Waiting {wait_time:.1f}s for rate limit...")
                await asyncio.sleep(wait_time)
        
        # Track this request
        self._request_times.append(now)
    
    def _track_usage(self, tokens: int) -> None:
        """Track token usage for analytics."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self._token_usage:
            self._token_usage = {today: 0}  # Reset for new day
        
        self._token_usage[today] += tokens
    
    def _calculate_cost(self, model: str, tokens: int, provider: str) -> float:
        """
        Calculate estimated cost for token usage.
        
        Args:
            model: Model used
            tokens: Total tokens consumed
            provider: "groq" or "openrouter"
            
        Returns:
            Estimated cost in USD
        """
        if provider == "groq" and model in self.GROQ_MODELS:
            cost_per_1k = self.GROQ_MODELS[model]["cost_per_1k_tokens"]
            return (tokens / 1000) * cost_per_1k
        elif provider == "openrouter":
            # OpenRouter pricing (approximate)
            return (tokens / 1000) * 0.001  # ~$0.001 per 1K tokens
        
        return 0.0
    
    def get_rate_limits(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get rate limit information for a model.
        
        Args:
            model: Model to get limits for (default: DEFAULT_GROQ_MODEL)
            
        Returns:
            Dict with rate limit information
        """
        model = model or self.DEFAULT_GROQ_MODEL
        
        if model in self.GROQ_MODELS:
            return self.GROQ_MODELS[model]
        
        return {}
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get current usage statistics.
        
        Returns:
            Dict with usage stats
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        return {
            "requests_last_minute": len(self._request_times),
            "tokens_today": self._token_usage.get(today, 0),
            "date": today,
        }


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    
    if _llm_service is None:
        _llm_service = LLMService()
    
    return _llm_service
