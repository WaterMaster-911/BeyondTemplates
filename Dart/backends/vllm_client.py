"""
Backend for interacting with a vLLM-served OpenAI-compatible API.
"""
import logging
import time
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Callable, Optional

from openai import OpenAI

class VLLMClient:
    def __init__(self, base_url: str, model: str, max_tokens: int, temperature: float):
        self.client = OpenAI(base_url=base_url, api_key="EMPTY")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def make_request(self, prompt: str, sample_id: str = "unk") -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=2000,  
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logging.warning("Request failed: %s", e)
            return ""