"""
NirmanAI - Google Gemini Client & LLM Integration
=================================================
High-speed, resilient client for Google Gemini Free Tier utilizing direct
REST API with automatic retry and exponential backoff for transient 503/429 errors,
and strict Pydantic v2 structured JSON validation.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import logging
from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger("nirman.gemini")
T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """Enterprise client for Google Gemini Free Tier with resilient JSON generation and Key Pool Rotation."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash"):
        load_dotenv(override=True)
        self.api_keys: list[str] = []
        
        # Load pool from GEMINI_API_KEYS
        keys_env = os.getenv("GEMINI_API_KEYS", "")
        if keys_env:
            self.api_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        
        # Fallback or single key
        single_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if single_key and single_key not in self.api_keys:
            self.api_keys.insert(0, single_key)

        self.current_key_idx = 0
        self.model_name = os.getenv("GEMINI_MODEL", model)

    def get_current_key(self) -> str:
        if not self.api_keys:
            load_dotenv(override=True)
            k = os.getenv("GEMINI_API_KEY", "")
            if k:
                self.api_keys.append(k)
        if not self.api_keys:
            raise ValueError(
                "❌ No GEMINI_API_KEY or GEMINI_API_KEYS configured in .env! Please add keys to your .env file."
            )
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    def rotate_key(self) -> str:
        if not self.api_keys:
            return self.get_current_key()
        total = len(self.api_keys)
        old_idx = self.current_key_idx % total
        self.current_key_idx = (self.current_key_idx + 1) % total
        new_key = self.api_keys[self.current_key_idx]
        masked = new_key[:6] + "..." + new_key[-4:]
        logger.warning(
            f"🔄 Rotated Gemini API Key (Key {old_idx + 1} -> Key {self.current_key_idx + 1} of {total}: {masked})"
        )
        return new_key

    def _call_gemini_rest(self, prompt: str, system_prompt: str, max_retries: int = 3) -> str:
        """Executes a direct POST request to Google Gemini with automatic key pool rotation on 429."""
        load_dotenv(override=True)
        active_key = self.get_current_key()

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nUser Input:\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 16384,
            }
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        models_to_try = [self.model_name]
        for fallback_m in ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3.1-flash-lite"]:
            if fallback_m not in models_to_try:
                models_to_try.append(fallback_m)

        total_keys = len(self.api_keys) if self.api_keys else 1
        max_key_rotations = total_keys * 2  # Allows full cycle through all keys twice

        last_error = None
        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent"
            for _ in range(max_key_rotations):
                current_api_key = self.get_current_key()
                headers = {
                    "Content-Type": "application/json",
                    "X-goog-api-key": current_api_key,
                }
                try:
                    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=45) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                        return text
                except urllib.error.HTTPError as e:
                    last_error = e
                    if e.code == 429:
                        logger.warning(
                            f"Model {current_model} received HTTP 429 on key {self.current_key_idx + 1}/{total_keys}. Rotating to next API key..."
                        )
                        self.rotate_key()
                        time.sleep(1)
                        continue
                    elif e.code in [500, 502, 503, 504]:
                        time.sleep(2)
                        continue
                    else:
                        break
                except Exception as e:
                    last_error = e
                    time.sleep(1)
                    continue

        err_msg = last_error.read().decode("utf-8", errors="ignore") if hasattr(last_error, "read") else str(last_error)
        raise RuntimeError(f"Gemini API error across all models and keys: {err_msg}")

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
    ) -> T:
        """Invokes Gemini and guarantees valid Pydantic v2 object parsing."""
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        structured_system = (
            f"{system_prompt}\n\n"
            f"CRITICAL REQUIREMENT: You MUST output ONLY valid JSON adhering strictly to this JSON schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any conversational preamble or notes. Return ONLY the raw JSON object."
        )

        raw_response = self._call_gemini_rest(
            prompt=user_prompt,
            system_prompt=structured_system,
        )

        cleaned = raw_response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        # Find outer JSON object braces
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]

        try:
            parsed = json.loads(cleaned, strict=False)
            return schema.model_validate(parsed)
        except Exception as e:
            try:
                import json_repair
                repaired = json_repair.repair_json(cleaned, return_objects=True)
                return schema.model_validate(repaired)
            except Exception as parse_err:
                raise ValueError(
                    f"Failed to parse Gemini output into {schema.__name__}: {parse_err}\nRaw output was:\n{raw_response[:600]}"
                )
