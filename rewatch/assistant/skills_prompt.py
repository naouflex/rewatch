"""Load bundled skill guides into the assistant system prompt."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from rewatch import settings

_PACKAGE_GUIDES = Path(__file__).resolve().parent / "skill_guides"
_REPO_SKILLS = Path(__file__).resolve().parents[2] / ".cursor" / "skills"

_GUIDE_SOURCES = (
    ("visualizations.md", "rewatch-visualizations-dashboards/SKILL.md"),
    ("visualization_reference.md", "rewatch-visualizations-dashboards/reference.md"),
    ("alerts.md", "rewatch-alerts-destinations/SKILL.md"),
)


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3 :].lstrip()
    return text


def _read_guide(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return _strip_frontmatter(path.read_text(encoding="utf-8")).strip()


def _resolve_guide(bundled_name: str, cursor_relative: str) -> Optional[str]:
    bundled = _read_guide(_PACKAGE_GUIDES / bundled_name)
    if bundled:
        return bundled
    cursor_path = _REPO_SKILLS / cursor_relative
    return _read_guide(cursor_path)


def build_skills_prompt() -> Optional[str]:
    if not settings.ASSISTANT_INCLUDE_SKILL_GUIDES:
        return None

    sections: list[str] = []
    budget = settings.ASSISTANT_SKILL_GUIDES_MAX_CHARS

    for bundled_name, cursor_relative in _GUIDE_SOURCES:
        content = _resolve_guide(bundled_name, cursor_relative)
        if not content:
            continue
        remaining = budget - sum(len(s) for s in sections)
        if remaining <= 500:
            break
        if len(content) > remaining:
            content = content[: remaining - 3] + "..."
        sections.append(content)

    if not sections:
        return None

    joined = "\n\n---\n\n".join(sections)
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return (
        "## Extended workflow guides (same content as Cursor agent skills)\n\n"
        "Prefer dedicated tools over call_api when they cover the task.\n\n"
        f"{joined}"
    )
