"""Shared pytest fixtures.

The optional LLM card refiner runs automatically whenever an OpenAI key is
present. To keep the suite deterministic and offline by default, it is disabled
for all tests here; the refiner's own tests re-enable it and mock the LLM call.
"""

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _disable_llm_refiner_by_default(monkeypatch):
    monkeypatch.setattr(settings, "research_enable_llm_refiner", False, raising=False)
    # Disable Pass 9 academic providers to keep all tests offline by default.
    # Pass 9 adapter tests mock HTTP directly and do not need this flag.
    monkeypatch.setattr(settings, "research_enable_academic_search", False, raising=False)
    yield
