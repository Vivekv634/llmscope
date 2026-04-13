from __future__ import annotations

import pathlib

import pytest

from llmscope.store.db import DatabaseStore
from llmscope.types.events import DoneEvent, RunStartEvent, TokenEvent, TTFTEvent


@pytest.fixture
def db(tmp_path: pathlib.Path) -> DatabaseStore:
    return DatabaseStore(str(tmp_path / "test.db"))


def _start_event(run_id: str = "r1", model: str = "llama3") -> RunStartEvent:
    return RunStartEvent(
        type="start",
        run_id=run_id,
        model=model,
        backend="ollama",
        prompt_hash="abc123",
        prompt_text="hello",
    )


class TestDatabaseStore:
    def test_schema_applied_on_init(self, db: DatabaseStore) -> None:
        runs = db.list_runs()
        assert runs == []

    def test_record_start_creates_run(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        runs = db.list_runs()
        assert len(runs) == 1
        assert runs[0].run_id == "r1"
        assert runs[0].model == "llama3"
        assert runs[0].backend == "ollama"

    def test_record_start_idempotent(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        db.record_start(_start_event())
        runs = db.list_runs()
        assert len(runs) == 1

    def test_record_ttft_sets_field(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        db.record_ttft(TTFTEvent(type="ttft", run_id="r1", ttft_ms=42.5))
        run = db.get_run("r1")
        assert run is not None
        assert run.ttft_ms == pytest.approx(42.5)

    def test_record_token_stores_row(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        db.record_token(
            TokenEvent(
                type="token", run_id="r1", position=0, text="Hi", arrived_at_ms=5.0
            )
        )
        tokens = db.get_tokens("r1")
        assert len(tokens) == 1
        assert tokens[0].text == "Hi"
        assert tokens[0].position == 0

    def test_record_token_idempotent_on_conflict(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        token = TokenEvent(
            type="token", run_id="r1", position=0, text="Hi", arrived_at_ms=5.0
        )
        db.record_token(token)
        db.record_token(token)
        tokens = db.get_tokens("r1")
        assert len(tokens) == 1

    def test_finalize_run_computes_tps_and_output(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        for i, word in enumerate(["Hello", " ", "world"]):
            db.record_token(
                TokenEvent(
                    type="token",
                    run_id="r1",
                    position=i,
                    text=word,
                    arrived_at_ms=float(i * 100),
                )
            )
        db.finalize_run(DoneEvent(type="done", run_id="r1", total_ms=300.0))

        run = db.get_run("r1")
        assert run is not None
        assert run.token_count == 3
        assert run.tps is not None
        assert run.tps > 0

        output = db.get_output("r1")
        assert output is not None
        assert output.full_text == "Hello world"
        assert output.token_count == 3

    def test_finalize_run_idempotent(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        db.record_token(
            TokenEvent(
                type="token", run_id="r1", position=0, text="Hi", arrived_at_ms=10.0
            )
        )
        done = DoneEvent(type="done", run_id="r1", total_ms=100.0)
        db.finalize_run(done)
        db.finalize_run(done)
        assert db.get_output("r1") is not None

    def test_get_run_returns_none_for_missing(self, db: DatabaseStore) -> None:
        result = db.get_run("nonexistent")
        assert result is None

    def test_get_output_returns_none_before_finalize(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        assert db.get_output("r1") is None

    def test_list_runs_multiple(self, db: DatabaseStore) -> None:
        db.record_start(_start_event(run_id="r1", model="llama3"))
        db.record_start(_start_event(run_id="r2", model="mistral"))
        runs = db.list_runs()
        assert len(runs) == 2

    def test_list_runs_respects_limit(self, db: DatabaseStore) -> None:
        for i in range(5):
            db.record_start(_start_event(run_id=f"r{i}"))
        runs = db.list_runs(limit=3)
        assert len(runs) == 3

    def test_get_tokens_returns_ordered_by_position(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        for i in range(3):
            db.record_token(
                TokenEvent(
                    type="token",
                    run_id="r1",
                    position=i,
                    text=str(i),
                    arrived_at_ms=float(i),
                )
            )
        tokens = db.get_tokens("r1")
        assert [t.position for t in tokens] == [0, 1, 2]

    def test_prompt_hash_stored(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        run = db.get_run("r1")
        assert run is not None
        assert run.prompt_hash == "abc123"

    def test_close_does_not_raise(self, db: DatabaseStore) -> None:
        db.close()

    def test_finalize_persists_quality_score(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        for i, text in enumerate(["the", "cat", "sat", "on", "the", "mat"]):
            db.record_token(
                TokenEvent(
                    type="token",
                    run_id="r1",
                    position=i,
                    text=text,
                    arrived_at_ms=float(i * 100),
                )
            )
        db.finalize_run(DoneEvent(type="done", run_id="r1", total_ms=600.0))
        run = db.get_run("r1")
        assert run is not None
        assert run.quality_score is not None
        assert 0.0 <= run.quality_score <= 1.0

    def test_set_tags_updates_run(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        db.set_tags("r1", ["fast", "prod"])
        run = db.get_run("r1")
        assert run is not None
        assert "fast" in run.tags
        assert "prod" in run.tags

    def test_set_tags_replaces_existing(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        db.set_tags("r1", ["a", "b"])
        db.set_tags("r1", ["c"])
        run = db.get_run("r1")
        assert run is not None
        assert run.tags == ["c"]

    def test_set_tags_empty_clears_all(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        db.set_tags("r1", ["x"])
        db.set_tags("r1", [])
        run = db.get_run("r1")
        assert run is not None
        assert run.tags == []

    def test_get_stats_empty_db(self, db: DatabaseStore) -> None:
        stats = db.get_stats()
        assert stats.total_runs == 0
        assert stats.total_tokens == 0
        assert stats.avg_tps == 0.0
        assert stats.avg_ttft_ms == 0.0
        assert stats.model_breakdown == {}

    def test_get_stats_counts_runs_and_tokens(self, db: DatabaseStore) -> None:
        db.record_start(_start_event(run_id="r1", model="llama3"))
        db.record_start(_start_event(run_id="r2", model="mistral"))
        for i in range(3):
            db.record_token(
                TokenEvent(
                    type="token",
                    run_id="r1",
                    position=i,
                    text="a",
                    arrived_at_ms=float(i),
                )
            )
        db.record_token(
            TokenEvent(
                type="token", run_id="r2", position=0, text="b", arrived_at_ms=1.0
            )
        )
        stats = db.get_stats()
        assert stats.total_runs == 2
        assert stats.total_tokens == 4

    def test_get_stats_model_breakdown(self, db: DatabaseStore) -> None:
        db.record_start(_start_event(run_id="r1", model="llama3"))
        db.record_start(_start_event(run_id="r2", model="llama3"))
        db.record_start(_start_event(run_id="r3", model="mistral"))
        stats = db.get_stats()
        assert stats.model_breakdown["llama3"] == 2
        assert stats.model_breakdown["mistral"] == 1

    def test_get_stats_avg_tps_after_finalize(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        for i in range(4):
            db.record_token(
                TokenEvent(
                    type="token",
                    run_id="r1",
                    position=i,
                    text="x",
                    arrived_at_ms=float(i * 50),
                )
            )
        db.finalize_run(DoneEvent(type="done", run_id="r1", total_ms=400.0))
        stats = db.get_stats()
        assert stats.avg_tps > 0.0
        assert stats.avg_ttft_ms == 0.0

    def test_list_runs_filter_by_model(self, db: DatabaseStore) -> None:
        db.record_start(_start_event(run_id="r1", model="llama3"))
        db.record_start(_start_event(run_id="r2", model="mistral"))
        runs = db.list_runs(model="llama3")
        assert len(runs) == 1
        assert runs[0].model == "llama3"

    def test_list_runs_filter_by_model_no_match(self, db: DatabaseStore) -> None:
        db.record_start(_start_event(run_id="r1", model="llama3"))
        runs = db.list_runs(model="nonexistent")
        assert runs == []

    def test_list_runs_filter_by_tag(self, db: DatabaseStore) -> None:
        db.record_start(_start_event(run_id="r1"))
        db.record_start(_start_event(run_id="r2"))
        db.set_tags("r1", ["prod"])
        runs = db.list_runs(tag="prod")
        assert len(runs) == 1
        assert runs[0].run_id == "r1"

    def test_list_runs_filter_by_tag_no_match(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        db.set_tags("r1", ["staging"])
        runs = db.list_runs(tag="prod")
        assert runs == []

    def test_list_runs_filter_by_q(self, db: DatabaseStore) -> None:
        db.record_start(_start_event(run_id="r1"))
        db.record_start(
            RunStartEvent(
                type="start",
                run_id="r2",
                model="llama3",
                backend="ollama",
                prompt_hash="xyz",
                prompt_text="something else entirely",
            )
        )
        runs = db.list_runs(q="hello")
        assert len(runs) == 1
        assert runs[0].run_id == "r1"

    def test_list_runs_filter_q_case_insensitive(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        runs = db.list_runs(q="HELLO")
        assert len(runs) == 1

    def test_list_tags_empty_when_no_tags(self, db: DatabaseStore) -> None:
        db.record_start(_start_event())
        assert db.list_tags() == []

    def test_list_tags_returns_unique_sorted(self, db: DatabaseStore) -> None:
        db.record_start(_start_event(run_id="r1"))
        db.record_start(_start_event(run_id="r2"))
        db.set_tags("r1", ["prod", "fast"])
        db.set_tags("r2", ["prod", "slow"])
        tags = db.list_tags()
        assert tags == sorted(set(tags))
        assert "prod" in tags
        assert "fast" in tags
        assert "slow" in tags
        assert tags.count("prod") == 1
