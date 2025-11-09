"""Tests for prompt registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompt_registry" / "prompts"


class TestPromptRegistry:
    """Test prompt template loading and versioning."""

    def test_all_prompts_valid_json(self) -> None:
        """All prompt files should be valid JSON."""
        for f in PROMPTS_DIR.glob("*.json"):
            with open(f) as fp:
                data = json.load(fp)
            assert "name" in data
            assert "versions" in data

    def test_each_prompt_has_active_version(self) -> None:
        """Each prompt should have exactly one active version."""
        for f in PROMPTS_DIR.glob("*.json"):
            with open(f) as fp:
                data = json.load(fp)
            active = [v for v in data["versions"] if v.get("active")]
            assert len(active) == 1, f"{data['name']} should have exactly 1 active version, found {len(active)}"

    def test_versions_have_required_fields(self) -> None:
        """Each version should have system_prompt, user_template, version."""
        for f in PROMPTS_DIR.glob("*.json"):
            with open(f) as fp:
                data = json.load(fp)
            for v in data["versions"]:
                assert "version" in v, f"{data['name']} version missing 'version'"
                assert "system_prompt" in v, f"{data['name']} version missing 'system_prompt'"
                assert "user_template" in v, f"{data['name']} version missing 'user_template'"

    def test_rag_qa_has_multiple_versions(self) -> None:
        """RAG QA prompt should have multiple versions showing iteration."""
        with open(PROMPTS_DIR / "rag_qa.json") as f:
            data = json.load(f)
        assert len(data["versions"]) >= 3

    def test_template_rendering(self) -> None:
        """Templates should be renderable with format strings."""
        with open(PROMPTS_DIR / "rag_qa.json") as f:
            data = json.load(f)
        active = next(v for v in data["versions"] if v["active"])
        rendered = active["user_template"].format(
            context="CSRD requires sustainability reporting.",
            question="What is CSRD?",
        )
        assert "CSRD requires" in rendered
        assert "What is CSRD?" in rendered
