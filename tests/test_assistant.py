import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from backend.admitflow.assistant import ask_admitflow


def test_assistant_reports_unavailable_without_provider_key(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)

    with pytest.raises(HTTPException) as error:
        ask_admitflow('What is the largest funnel drop-off?', {'funnel': []})

    assert error.value.status_code == 503
    assert 'GROQ_API_KEY' in error.value.detail


def test_assistant_uses_server_provider_and_validates_response(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-only-key')
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
        'answer': 'Submission is the largest observed drop-off.',
        'data_used': ['funnel stage counts'],
        'follow_up_questions': ['Compare by programme?'],
    })))])
    create = Mock(return_value=completion)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    groq_client = Mock(return_value=client)
    groq = SimpleNamespace(Groq=groq_client)
    monkeypatch.setitem(__import__('sys').modules, 'groq', groq)

    answer = ask_admitflow('Where is the biggest drop-off?', {'funnel': [{'stage': 'submitted'}]})

    assert answer.answer.startswith('Submission')
    assert answer.data_used == ['funnel stage counts']
    groq_client.assert_called_once_with(api_key='test-only-key')
    create.assert_called_once()
