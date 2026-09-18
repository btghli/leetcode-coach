from pathlib import Path

import pytest
from pydantic import ValidationError

from leetcode_coach.config import initialize_model, load_config
from leetcode_coach.schemas import ProblemMetadata, TeachBackAssessment


def test_problem_metadata_validation():
    item = ProblemMetadata(id=1, slug="two-sum", title="Two Sum", difficulty="Easy")
    assert item.slug == "two-sum"
    with pytest.raises(ValidationError):
        ProblemMetadata(id=0, slug="Two Sum", title="", difficulty="Unknown")


def test_teach_back_completion():
    assessment = TeachBackAssessment(
        invariant_correct=True,
        complexity_correct=True,
        edge_case_identified=True,
        pattern_boundary_understood=True,
        suggested_quality=5,
        feedback="ok",
    )
    assert assessment.complete


def test_model_precedence_and_missing_key(tmp_path: Path, monkeypatch):
    (tmp_path / "leetcode-coach.toml").write_text('model = "anthropic:configured"\n', encoding="utf-8")
    monkeypatch.setenv("LEETCODE_COACH_MODEL", "openai:environment")
    assert load_config(tmp_path).model == "openai:environment"
    assert load_config(tmp_path, "anthropic:override").model == "anthropic:override"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        initialize_model("openai:test-model")


def test_decision_engine_configuration_defaults_to_codex_cli(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LEETCODE_COACH_ENGINE", raising=False)
    config = load_config(tmp_path)
    assert config.engine == "codex-cli"
    monkeypatch.setenv("LEETCODE_COACH_ENGINE", "langchain")
    assert load_config(tmp_path).engine == "langchain"
    assert load_config(tmp_path, engine_override="codex-cli").engine == "codex-cli"


def test_invalid_codex_timeout_is_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LEETCODE_COACH_CODEX_TIMEOUT", "0")
    with pytest.raises(ValueError, match="greater than zero"):
        load_config(tmp_path)
