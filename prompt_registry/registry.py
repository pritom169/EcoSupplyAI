"""Versioned prompt registry for tracking, deploying, and rolling back prompts."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PromptTemplate:
    id: str
    name: str
    version: str
    system_prompt: str
    user_template: str  # Contains {variable} placeholders
    description: str = ""
    author: str = "ecosupplyai-team"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    tags: list[str] = field(default_factory=list)
    model_config: dict = field(default_factory=lambda: {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 1024})
    is_active: bool = False


class PromptRegistry:
    def __init__(self, persistence_path: str | None = None) -> None:
        self._templates: dict[str, dict[str, PromptTemplate]] = {}  # name -> version -> template
        self._lock = threading.Lock()
        self._persistence_path = persistence_path
        if persistence_path and Path(persistence_path).exists():
            self.load_from_file(persistence_path)

    def register(self, template: PromptTemplate) -> None:
        with self._lock:
            if template.name not in self._templates:
                self._templates[template.name] = {}
            self._templates[template.name][template.version] = template
            logger.info("prompt_registry.registered", name=template.name, version=template.version)

    def get(self, name: str, version: str = "latest") -> PromptTemplate:
        with self._lock:
            versions = self._templates.get(name, {})
            if not versions:
                raise KeyError(f"Prompt '{name}' not found")
            if version == "latest":
                # Get the active version, or the highest version
                active = [v for v in versions.values() if v.is_active]
                if active:
                    return active[0]
                return sorted(versions.values(), key=lambda t: t.version)[-1]
            if version not in versions:
                raise KeyError(f"Version '{version}' not found for prompt '{name}'")
            return versions[version]

    def get_all_versions(self, name: str) -> list[PromptTemplate]:
        return sorted(self._templates.get(name, {}).values(), key=lambda t: t.version)

    def activate(self, name: str, version: str) -> None:
        with self._lock:
            for v, template in self._templates.get(name, {}).items():
                template.is_active = v == version
            logger.info("prompt_registry.activated", name=name, version=version)

    def render(self, name: str, variables: dict, version: str = "latest") -> tuple[str, str]:
        template = self.get(name, version)
        rendered_user = template.user_template.format(**variables)
        return template.system_prompt, rendered_user

    def diff(self, name: str, v1: str, v2: str) -> str:
        t1 = self.get(name, v1)
        t2 = self.get(name, v2)
        lines = [f"Diff for '{name}': {v1} → {v2}\n"]
        if t1.system_prompt != t2.system_prompt:
            lines.append("--- System Prompt Changed ---")
            lines.append(f"- {t1.system_prompt[:200]}...")
            lines.append(f"+ {t2.system_prompt[:200]}...")
        if t1.user_template != t2.user_template:
            lines.append("--- User Template Changed ---")
            lines.append(f"- {t1.user_template[:200]}...")
            lines.append(f"+ {t2.user_template[:200]}...")
        return "\n".join(lines)

    def export_all(self) -> dict:
        result = {}
        for name, versions in self._templates.items():
            result[name] = {v: {"system_prompt": t.system_prompt, "user_template": t.user_template, "version": t.version, "is_active": t.is_active} for v, t in versions.items()}
        return result

    def load_from_file(self, path: str) -> None:
        data = json.loads(Path(path).read_text())
        for name, versions in data.items():
            for version, fields in versions.items():
                self.register(PromptTemplate(
                    id=f"{name}_{version}",
                    name=name,
                    version=version,
                    **fields,
                ))
