from __future__ import annotations

from pathlib import Path

from guardian.scripts import ensure_embed_model


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


def test_model_status_flags_missing_weights(tmp_path: Path) -> None:
    model_dir = tmp_path / "bge-large-en-v1.5"
    model_dir.mkdir()
    _touch(model_dir / "config.json")
    _touch(model_dir / "tokenizer.json")
    _touch(model_dir / "modules.json")
    _touch(model_dir / ensure_embed_model.SUCCESS_SENTINEL)
    (model_dir / "onnx").mkdir()

    present, reason = ensure_embed_model._model_status(model_dir)

    assert present is False
    assert "missing model weights" in reason


def test_model_status_accepts_root_weights(tmp_path: Path) -> None:
    model_dir = tmp_path / "bge-large-en-v1.5"
    model_dir.mkdir()
    _touch(model_dir / "modules.json")
    _touch(model_dir / "model.safetensors")

    present, reason = ensure_embed_model._model_status(model_dir)

    assert present is True
    assert reason == "model ready"


def test_model_status_accepts_transformer_subdir_weights(
    tmp_path: Path,
) -> None:
    model_dir = tmp_path / "bge-large-en-v1.5"
    model_dir.mkdir()
    _touch(model_dir / "modules.json")
    _touch(model_dir / "0_Transformer" / "pytorch_model.bin")

    present, reason = ensure_embed_model._model_status(model_dir)

    assert present is True
    assert reason == "model ready"
