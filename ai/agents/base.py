"""Base agent: prompt loading, LLM call, JSON-schema validation with retry."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, ClassVar

from pydantic import ValidationError

from ai.models.llm import LLMClient, LLMError
from ai.models.schemas import OUTPUT_MODELS

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class AgentError(RuntimeError):
    pass


class BaseAgent:
    agent_type: ClassVar[str] = "base"
    prompt_file: ClassVar[str] = "base.txt"
    prompt_version: ClassVar[str] = "v1.0"

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    # ------------------------------------------------------------------
    def run(self, context: dict) -> dict:
        """Run the agent and return a schema-validated output dict."""
        system = self._load_prompt()
        user = self._build_user_prompt(context)
        raw = self.llm.complete(system, user, json_mode=True)
        output = self._validate(raw, context)
        output["_provider"] = self.llm.provider
        output["_model"] = self.llm.config.model
        return output

    # ------------------------------------------------------------------
    def _build_user_prompt(self, context: dict) -> str:
        raise NotImplementedError

    def _load_prompt(self) -> str:
        return (PROMPTS_DIR / self.prompt_file).read_text(encoding="utf-8")

    def _validate(self, raw: str, context: dict) -> dict:
        model = OUTPUT_MODELS[self.agent_type]
        try:
            data = json.loads(raw)
            validated = model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as first_exc:
            # One repair attempt: feed the error back to the LLM
            try:
                repair = self.llm.complete(
                    "You produced invalid JSON. Fix it and return valid JSON matching the schema.",
                    f"Your previous output:\n{raw}\n\nError: {first_exc}\n\nContext:\n{json.dumps(context, ensure_ascii=False, default=str)[:4000]}",
                    json_mode=True,
                )
                validated = model.model_validate(json.loads(repair))
            except (json.JSONDecodeError, ValidationError, LLMError):
                raise AgentError(
                    f"{self.agent_type} agent produced schema-invalid output: {first_exc}"
                ) from first_exc
        return validated.model_dump()

    def _snippet(self, context: dict, keys: list[str], max_len: int = 8000) -> str:
        """Compact, JSON-serializable view of the context for the prompt."""
        subset = {k: context.get(k) for k in keys if context.get(k) is not None}
        return json.dumps(subset, ensure_ascii=False, default=str)[:max_len]
