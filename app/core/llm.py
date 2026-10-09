"""LLM service for exam generation using Groq API with OpenRouter fallback."""

import logging
import re
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, timedelta
import json

import httpx
from openai import AsyncOpenAI
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """
    LLM service abstraction for exam generation.

    Primary: Groq API (cost-effective, OpenAI-compatible)
    Fallback: OpenRouter (multiple models)

    Groq Rate Limits (Developer / on-demand plan) — verified 2026-10:
    - openai/gpt-oss-20b : 30 RPM, 1K RPD, 8K total-TPM, ~6K OTPM
    - openai/gpt-oss-120b: 30 RPM, 1K RPD, 8K total-TPM, ~6K OTPM
    - qwen/qwen3.8-27b   : 30 RPM, 1K RPD, 8K total-TPM, 1K OTPM  ← low!
    """

    # Groq models with verified rate limits.
    # otpm = output tokens per minute (enforced separately from total TPM)
    GROQ_MODELS = {
        "openai/gpt-oss-20b": {
            "rpm": 30,
            "rpd": 1000,
            "tpm": 8000,
            "otpm": 6000,          # output tokens per minute (safe headroom)
            "cost_per_1k_tokens": 0.0003,
        },
        "openai/gpt-oss-120b": {
            "rpm": 30,
            "rpd": 1000,
            "tpm": 8000,
            "otpm": 6000,
            "cost_per_1k_tokens": 0.0005,
        },
        "qwen/qwen3.8-27b": {
            "rpm": 30,
            "rpd": 1000,
            "tpm": 8000,
            "otpm": 1000,          # strict 1K OTPM — only use for small payloads
            "cost_per_1k_tokens": 0.0003,
        },
        "llama-3.3-70b-versatile": {
            "rpm": 30,
            "rpd": 1000,
            "tpm": 12000,
            "otpm": 6000,
            "cost_per_1k_tokens": 0.0005,
        },
        "llama-3.1-8b-instant": {
            "rpm": 30,
            "rpd": 14400,
            "tpm": 6000,
            "otpm": 6000,
            "cost_per_1k_tokens": 0.0002,
        },
    }

    # Default primary model: gpt-oss-20b tolerates large exams (up to 6K OTPM)
    DEFAULT_GROQ_MODEL = getattr(settings, "groq_model", "openai/gpt-oss-20b")

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        groq_base_url: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        groq_model: Optional[str] = None,
        openrouter_model: Optional[str] = None,
    ):
        """
        Initialize LLM service.

        Args:
            groq_api_key: Groq API key (uses env var if not provided)
            groq_base_url: Groq base URL (uses env var if not provided)
            openrouter_api_key: OpenRouter API key for fallback
            groq_model: Model name for Groq
            openrouter_model: Model name for OpenRouter fallback
        """
        # Initialize Groq client (OpenAI-compatible)
        self.groq_api_key = groq_api_key or settings.groq_api_key
        self.groq_base_url = groq_base_url or settings.groq_base_url
        self.groq_model = groq_model or getattr(settings, "groq_model", "openai/gpt-oss-20b")
        self.openrouter_model = openrouter_model or getattr(settings, "openrouter_model", "meta-llama/llama-3.3-70b-instruct")

        if self.groq_api_key:
            self.groq_client = AsyncOpenAI(
                api_key=self.groq_api_key,
                base_url=self.groq_base_url,
                timeout=settings.llm_timeout_seconds,
                max_retries=1,
            )
            logger.info(f"✅ Groq API client initialized: {self.groq_base_url} (model: {self.groq_model})")
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

        # Initialize Gemini API (high token capacity & STEM reasoning fallback)
        self.gemini_api_key = getattr(settings, "gemini_api_key", None)
        self.gemini_model = getattr(settings, "gemini_model", "gemini-3.1-flash-lite")
        if self.gemini_api_key:
            logger.info(f"✅ Gemini API client configured: model={self.gemini_model}")

        # Rate limiting tracking (simple in-memory for MVP)
        self._request_times: List[datetime] = []
        self._token_usage: Dict[str, int] = {}

    def _safe_max_tokens(self, model: str, requested: int) -> int:
        """
        Cap max_tokens to the model's OTPM headroom so we never trigger
        Groq's 429 'Request too large' on output tokens per minute.

        Leaves a 15 % safety margin below the OTPM ceiling.
        """
        info = self.GROQ_MODELS.get(model)
        if not info:
            return requested
        otpm = info.get("otpm", requested)
        safe_ceiling = int(otpm * 0.85)
        capped = min(requested, safe_ceiling)
        if capped < requested:
            logger.debug(
                "max_tokens capped %d → %d to stay within %s OTPM=%d",
                requested, capped, model, otpm,
            )
        return capped

    @staticmethod
    def _strip_thinking(content: str) -> str:
        """
        Strip reasoning-model chain-of-thought wrappers (<think>…</think>)
        before JSON parsing.  Qwen3 and some OpenAI-oss models emit these.
        """
        if not content:
            return content
        # Remove <think>...</think> blocks (Qwen3 reasoning mode)
        stripped = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        return stripped.strip()

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_fallback_on_error: bool = True,
        preferred_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate text using LLM with intelligent class/subject-aware routing.

        Providers:
        - Groq: ultra-fast (sub-6s), primary for Primary & JSS (<30 questions).
        - Gemini: high-token (up to 8,192 tokens) & STEM reasoning (SSS Physics/Chem/Further Maths or >30 questions).
        - OpenRouter: multi-provider tertiary fallback.
        """
        # If Gemini is preferred (e.g. SSS STEM or >30 questions)
        if preferred_provider == "gemini" and self.gemini_api_key:
            try:
                logger.info(
                    "llm.route provider=gemini model=%s max_tokens=%s",
                    self.gemini_model,
                    max_tokens,
                )
                return await self._generate_gemini(
                    prompt=prompt,
                    model=self.gemini_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.exception(
                    "llm.provider_failed provider=gemini model=%s preferred=true error_type=%s error=%s; falling back",
                    self.gemini_model,
                    type(e).__name__,
                    str(e)[:300],
                )

        model = model or getattr(self, "groq_model", self.DEFAULT_GROQ_MODEL)

        # Try Groq (primary for speed)
        if self.groq_client:
            safe_max_tokens = self._safe_max_tokens(model, max_tokens)
            for attempt in range(2):
                try:
                    # Check request-rate limits
                    await self._check_rate_limits(model)

                    logger.info(
                        "Generating with Groq model: %s (max_tokens=%d)",
                        model, safe_max_tokens,
                    )

                    response = await self.groq_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=safe_max_tokens,
                    )

                    # Extract response and strip thinking tags
                    raw_content = response.choices[0].message.content or ""
                    content = self._strip_thinking(raw_content)
                    tokens_used = response.usage.total_tokens

                    # Calculate cost
                    cost = self._calculate_cost(model, tokens_used, "groq")

                    # Track usage
                    self._track_usage(tokens_used)

                    logger.info("✅ Groq generation successful: %d tokens, $%.4f", tokens_used, cost)

                    return {
                        "content": content,
                        "model": model,
                        "tokens_used": tokens_used,
                        "cost": cost,
                        "provider": "groq",
                    }

                except Exception as e:
                    err_msg = str(e)
                    is_rate_limit = "429" in err_msg or "rate_limit" in err_msg.lower()
                    if is_rate_limit and attempt == 0:
                        logger.warning(
                            "⚠️ Groq rate limit (attempt 1/2): %s. Waiting 3s...", err_msg[:200]
                        )
                        await asyncio.sleep(3.0)
                        continue

                    logger.exception(
                        "llm.provider_failed provider=groq model=%s attempt=%s error_type=%s error=%s",
                        model,
                        attempt + 1,
                        type(e).__name__,
                        err_msg[:300],
                    )

                    if not use_fallback_on_error or not (self.gemini_api_key or self.openrouter_client):
                        raise ValueError(f"Groq generation failed: {err_msg}")

                    logger.warning("⚠️ Falling back from Groq to secondary provider...")
                    break

        # Fallback to Gemini (if not already tried as preferred)
        if self.gemini_api_key and use_fallback_on_error and preferred_provider != "gemini":
            try:
                logger.info("llm.route provider=gemini model=%s preferred=false", self.gemini_model)
                return await self._generate_gemini(
                    prompt=prompt,
                    model=self.gemini_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.exception(
                    "llm.provider_failed provider=gemini model=%s preferred=false error_type=%s error=%s; falling back",
                    self.gemini_model,
                    type(e).__name__,
                    str(e)[:300],
                )

        # Fallback to OpenRouter
        if self.openrouter_client:
            try:
                logger.info("llm.route provider=openrouter model=%s", self.openrouter_model)

                response = await self.openrouter_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                raw_content = response.choices[0].message.content or ""
                content = self._strip_thinking(raw_content)
                tokens_used = response.usage.total_tokens
                cost = self._calculate_cost("llama-3.3-70b", tokens_used, "openrouter")

                logger.info("✅ OpenRouter generation successful: %d tokens, $%.4f", tokens_used, cost)

                return {
                    "content": content,
                    "model": self.openrouter_model,
                    "tokens_used": tokens_used,
                    "cost": cost,
                    "provider": "openrouter",
                }

            except Exception as e:
                logger.exception(
                    "llm.provider_failed provider=openrouter model=%s error_type=%s error=%s",
                    self.openrouter_model,
                    type(e).__name__,
                    str(e)[:300],
                )
                raise ValueError(f"All LLM providers failed: {str(e)}")

        raise ValueError("No LLM provider available")

    async def _generate_gemini(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """
        Generate text using Google Gemini API.

        Provides up to 8,192 output tokens and high mathematical/scientific
        reasoning without Groq on-demand OTPM ceilings.
        """
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        models_to_try = [model or self.gemini_model]
        for candidate in ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]:
            if candidate not in models_to_try:
                models_to_try.append(candidate)

        last_err = None
        # Ensure Gemini always has the full 8,192 tokens so thought tokens and long exams never get truncated
        gemini_max_tokens = max(max_tokens, 8192)

        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={self.gemini_api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": gemini_max_tokens,
                    "responseMimeType": "application/json" if "json" in prompt.lower() else "text/plain",
                },
            }

            try:
                async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates and candidates[0].get("content"):
                            cand = candidates[0]
                            parts = cand["content"].get("parts", [])
                            finish_reason = cand.get("finishReason", "")
                            if finish_reason == "MAX_TOKENS":
                                logger.warning("⚠️ Gemini model %s reached MAX_TOKENS limit", current_model)

                            # Combine all text parts (skipping pure thought blocks)
                            content_parts = [
                                p.get("text", "")
                                for p in parts
                                if p.get("text") and not p.get("thought", False)
                            ]
                            if not content_parts:
                                content_parts = [p.get("text", "") for p in parts if p.get("text")]
                            raw_content = "".join(content_parts)
                            content = self._strip_thinking(raw_content)

                            usage = data.get("usageMetadata", {})
                            tokens_used = usage.get("totalTokenCount", 0)
                            cost = (tokens_used / 1000) * 0.000075
                            self._track_usage(tokens_used)
                            logger.info(
                                "✅ Gemini generation successful with %s (finishReason=%s): %d tokens, $%.4f",
                                current_model, finish_reason, tokens_used, cost,
                            )
                            return {
                                "content": content,
                                "model": current_model,
                                "tokens_used": tokens_used,
                                "cost": cost,
                                "provider": "gemini",
                            }
                    last_err = f"Status {response.status_code}: {response.text[:200]}"
                    logger.warning(
                        "llm.provider_attempt_failed provider=gemini model=%s status=%s response=%s",
                        current_model,
                        response.status_code,
                        response.text[:200],
                    )
            except Exception as e:
                last_err = str(e)
                logger.exception(
                    "llm.provider_attempt_failed provider=gemini model=%s error_type=%s error=%s",
                    current_model,
                    type(e).__name__,
                    last_err[:300],
                )

        logger.error(
            "llm.provider_exhausted provider=gemini models=%s last_error=%s",
            ",".join(models_to_try),
            str(last_err)[:300],
        )
        raise ValueError(f"All Gemini models failed. Last error: {last_err}")

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
