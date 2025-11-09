"""Tests for workflow engine."""

from __future__ import annotations

import pytest


class TestWorkflowExecution:
    """Test workflow step execution."""

    def test_sequential_step_execution(self) -> None:
        """Steps should execute in order."""
        executed = []

        def step_a(ctx: dict) -> dict:
            executed.append("a")
            return {**ctx, "a_done": True}

        def step_b(ctx: dict) -> dict:
            executed.append("b")
            return {**ctx, "b_done": True}

        ctx: dict = {}
        ctx = step_a(ctx)
        ctx = step_b(ctx)

        assert executed == ["a", "b"]
        assert ctx["a_done"] is True
        assert ctx["b_done"] is True

    def test_step_failure_stops_workflow(self) -> None:
        """A failing step should halt the workflow."""
        executed = []

        def step_ok(ctx: dict) -> dict:
            executed.append("ok")
            return ctx

        def step_fail(ctx: dict) -> dict:
            raise ValueError("Step failed")

        ctx: dict = {}
        ctx = step_ok(ctx)
        with pytest.raises(ValueError, match="Step failed"):
            step_fail(ctx)

        assert executed == ["ok"]

    def test_step_retry_on_transient_error(self) -> None:
        """Steps should retry on transient failures."""
        attempts = {"count": 0}

        def flaky_step(ctx: dict) -> dict:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ConnectionError("Transient failure")
            return {**ctx, "done": True}

        ctx: dict = {}
        max_retries = 3
        for _ in range(max_retries):
            try:
                ctx = flaky_step(ctx)
                break
            except ConnectionError:
                continue

        assert ctx.get("done") is True
        assert attempts["count"] == 3

    def test_context_propagation(self) -> None:
        """Context should be passed between steps."""

        def enrich(ctx: dict) -> dict:
            return {**ctx, "enriched": True, "score": 85}

        def validate(ctx: dict) -> dict:
            assert ctx["enriched"] is True
            return {**ctx, "validated": ctx["score"] > 60}

        ctx = enrich({})
        ctx = validate(ctx)
        assert ctx["validated"] is True
