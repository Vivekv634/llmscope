from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from llmscope.types.events import (
    DoneEvent,
    QueueEvent,
    RunStartEvent,
    TTFTEvent,
    TokenEvent,
)


class TestRunStartEvent:
    def test_valid_construction(self) -> None:
        event = RunStartEvent(
            type="start",
            run_id="r1",
            model="llama3",
            backend="ollama",
            prompt_hash="abc123",
            prompt_text="hello",
        )
        assert event.model == "llama3"
        assert event.backend == "ollama"

    def test_run_id_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RunStartEvent(
                type="start",
                run_id="",
                model="llama3",
                backend="ollama",
                prompt_hash="abc",
                prompt_text="hi",
            )

    def test_model_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RunStartEvent(
                type="start",
                run_id="r1",
                model="",
                backend="ollama",
                prompt_hash="abc",
                prompt_text="hi",
            )

    def test_empty_prompt_text_allowed(self) -> None:
        event = RunStartEvent(
            type="start",
            run_id="r1",
            model="llama3",
            backend="ollama",
            prompt_hash="abc",
            prompt_text="",
        )
        assert event.prompt_text == ""

    def test_serialisation_round_trip(self) -> None:
        event = RunStartEvent(
            type="start",
            run_id="r1",
            model="llama3",
            backend="ollama",
            prompt_hash="deadbeef",
            prompt_text="test prompt",
        )
        restored = RunStartEvent.model_validate_json(event.model_dump_json())
        assert restored == event


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


class TestQueueEventUnion:
    _adapter: TypeAdapter[QueueEvent] = TypeAdapter(QueueEvent)

    def test_parse_start_payload(self) -> None:
        raw = '{"type":"start","run_id":"r1","model":"llama3","backend":"ollama","prompt_hash":"abc","prompt_text":"hi"}'
        event = self._adapter.validate_json(raw)
        assert isinstance(event, RunStartEvent)
        assert event.model == "llama3"

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
