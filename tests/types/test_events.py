"""Tests for llmscope/types/events.py.

Covers: model construction, field validation, discriminated union parsing,
and rejection of invalid payloads. Every public field constraint is tested.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from llmscope.types.events import (
    DoneEvent,
    QueueEvent,
    TTFTEvent,
    TokenEvent,
)

# ---------------------------------------------------------------------------
# TTFTEvent
# ---------------------------------------------------------------------------


class TestTTFTEvent:
    def test_valid_construction(self) -> None:
        event = TTFTEvent(type="ttft", run_id="abc123", ttft_ms=42.5)
        assert event.type == "ttft"
        assert event.run_id == "abc123"
        assert event.ttft_ms == 42.5

    def test_ttft_ms_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            TTFTEvent(type="ttft", run_id="abc123", ttft_ms=0.0)

    def test_ttft_ms_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TTFTEvent(type="ttft", run_id="abc123", ttft_ms=-1.0)

    def test_run_id_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TTFTEvent(type="ttft", run_id="", ttft_ms=10.0)

    def test_wrong_literal_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TTFTEvent(type="token", run_id="abc123", ttft_ms=10.0)  # type: ignore[arg-type]

    def test_serialisation_round_trip(self) -> None:
        event = TTFTEvent(type="ttft", run_id="abc123", ttft_ms=100.0)
        restored = TTFTEvent.model_validate_json(event.model_dump_json())
        assert restored == event


# ---------------------------------------------------------------------------
# TokenEvent
# ---------------------------------------------------------------------------


class TestTokenEvent:
    def test_valid_construction(self) -> None:
        event = TokenEvent(
            type="token", run_id="abc123", position=0, text="Hello", arrived_at_ms=5.0
        )
        assert event.position == 0
        assert event.text == "Hello"

    def test_position_zero_allowed(self) -> None:
        event = TokenEvent(
            type="token", run_id="r1", position=0, text="x", arrived_at_ms=0.0
        )
        assert event.position == 0

    def test_position_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TokenEvent(
                type="token", run_id="r1", position=-1, text="x", arrived_at_ms=0.0
            )

    def test_arrived_at_ms_zero_allowed(self) -> None:
        event = TokenEvent(
            type="token", run_id="r1", position=0, text="x", arrived_at_ms=0.0
        )
        assert event.arrived_at_ms == 0.0

    def test_arrived_at_ms_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TokenEvent(
                type="token", run_id="r1", position=0, text="x", arrived_at_ms=-1.0
            )

    def test_empty_text_is_valid(self) -> None:
        # Empty tokens can arrive from backends — not an error
        event = TokenEvent(
            type="token", run_id="r1", position=0, text="", arrived_at_ms=0.0
        )
        assert event.text == ""

    def test_serialisation_round_trip(self) -> None:
        event = TokenEvent(
            type="token", run_id="r1", position=3, text="world", arrived_at_ms=55.2
        )
        restored = TokenEvent.model_validate_json(event.model_dump_json())
        assert restored == event


# ---------------------------------------------------------------------------
# DoneEvent
# ---------------------------------------------------------------------------


class TestDoneEvent:
    def test_valid_construction(self) -> None:
        event = DoneEvent(type="done", run_id="r1", total_ms=1234.5)
        assert event.total_ms == 1234.5

    def test_total_ms_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            DoneEvent(type="done", run_id="r1", total_ms=0.0)

    def test_total_ms_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DoneEvent(type="done", run_id="r1", total_ms=-100.0)

    def test_serialisation_round_trip(self) -> None:
        event = DoneEvent(type="done", run_id="r1", total_ms=999.9)
        restored = DoneEvent.model_validate_json(event.model_dump_json())
        assert restored == event


# ---------------------------------------------------------------------------
# QueueEvent discriminated union
# ---------------------------------------------------------------------------


class TestQueueEventUnion:
    """Verifies that the discriminated union dispatches to the correct model."""

    _adapter: TypeAdapter[QueueEvent] = TypeAdapter(QueueEvent)

    def test_parse_ttft_payload(self) -> None:
        raw = '{"type": "ttft", "run_id": "r1", "ttft_ms": 50.0}'
        event = self._adapter.validate_json(raw)
        assert isinstance(event, TTFTEvent)
        assert event.ttft_ms == 50.0

    def test_parse_token_payload(self) -> None:
        raw = '{"type": "token", "run_id": "r1", "position": 2, "text": "hi", "arrived_at_ms": 10.0}'
        event = self._adapter.validate_json(raw)
        assert isinstance(event, TokenEvent)
        assert event.position == 2

    def test_parse_done_payload(self) -> None:
        raw = '{"type": "done", "run_id": "r1", "total_ms": 800.0}'
        event = self._adapter.validate_json(raw)
        assert isinstance(event, DoneEvent)
        assert event.total_ms == 800.0

    def test_unknown_type_rejected(self) -> None:
        raw = '{"type": "unknown", "run_id": "r1"}'
        with pytest.raises(ValidationError):
            self._adapter.validate_json(raw)

    def test_missing_discriminator_rejected(self) -> None:
        raw = '{"run_id": "r1", "ttft_ms": 10.0}'
        with pytest.raises(ValidationError):
            self._adapter.validate_json(raw)
