"""Tests for bundled skill guide loading."""

from rewatch.assistant.skills_prompt import build_skills_prompt


def test_build_skills_prompt_includes_visualizations(monkeypatch):
    monkeypatch.setattr("rewatch.assistant.skills_prompt.settings.ASSISTANT_INCLUDE_SKILL_GUIDES", True)
    monkeypatch.setattr("rewatch.assistant.skills_prompt.settings.ASSISTANT_SKILL_GUIDES_MAX_CHARS", 50000)
    prompt = build_skills_prompt()
    assert prompt is not None
    assert "build_dashboard_from_spec" in prompt
    assert "alert" in prompt.lower() or "Alert" in prompt


def test_build_skills_prompt_disabled(monkeypatch):
    monkeypatch.setattr("rewatch.assistant.skills_prompt.settings.ASSISTANT_INCLUDE_SKILL_GUIDES", False)
    assert build_skills_prompt() is None
