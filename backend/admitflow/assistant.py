from __future__ import annotations

import json
import os
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError


class AssistantAnswer(BaseModel):
    answer: str = Field(min_length=1)
    data_used: list[str]
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3)


def assistant_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def ask_admitflow(question: str, context: dict[str, Any]) -> AssistantAnswer:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI assistant is unavailable. Configure GROQ_API_KEY on the backend.")

    try:
        from groq import Groq
    except ImportError as error:
        raise HTTPException(status_code=503, detail="AI provider SDK is not installed on the backend.") from error

    system_message = (
        "You are AdmitFlow Intelligence, an admissions analytics assistant. Answer the user's "
        "question concisely using only the supplied aggregate context. Never invent metrics or "
        "causes. Clearly distinguish observed associations from causal claims; attribution is "
        "descriptive only. Do not reveal hidden reasoning or chain-of-thought. Summarize your "
        "conclusion and cite the relevant supplied data names. If evidence is insufficient, say "
        "so. Return one JSON object with exactly: answer (string), data_used (array of short "
        "source labels), follow_up_questions (array of up to three concise questions)."
    )
    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=os.getenv("ADMITFLOW_AI_MODEL", "openai/gpt-oss-120b"),
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": json.dumps({"question": question, "admitflow_data": context})},
            ],
        )
        content = completion.choices[0].message.content
        return AssistantAnswer.model_validate_json(content or "")
    except HTTPException:
        raise
    except (json.JSONDecodeError, IndexError, AttributeError, ValidationError) as error:
        raise HTTPException(status_code=502, detail="AI provider returned an invalid response.") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="Unable to retrieve an answer from the AI provider.") from error
