# Project Guidelines & Copilot Behavior

## Copilot Behavior Constraints
- Prioritize providing raw, functional code over conceptual explanations.
- Omit conversational filler. Do not explain the code unless explicitly requested.
- strictly adhere to the types and constraints defined below.

## Stack
- Python ≥3.11, hatchling, uv
- OpenCV, PaddleOCR (PaddlePaddle), NumPy, Matplotlib, Typer
- pytest (parametrize, MagicMock, approx)

## Code Style
- Add `from __future__ import annotations` to all modules.
- Strict PEP 484 typing on all signatures. No `Any` unless unavoidable.
- Third-party untyped imports: `type: ignore` (e.g., paddleocr).
- Lazy in-function imports: `# noqa: PLC0415`.
- Docstrings: Google-style (English).
- Naming: `snake_case` (vars/funcs), `PascalCase` (classes).
- Logging: Per-module `logging.getLogger(__name__)`. No `print()`.
- Imports: stdlib → third-party → local.

## Architecture & State
- Pipeline flow: Sampler → Detector → Cropper → Recognizer → Parser → Orchestrator → Visualizer.
- Pipeline implementation: `src/genshin_damage_track/pipeline/`.
- Data models (`models.py`): `FrameRecord`, `DpsRecord`, `CharacterDamage`, `ExtractionResult`. Must be immutable dataclasses where possible.
- Types: `BoundingBox = dict[str, int]`.
- Constants (`config.py`): ROI coordinates mapped to 1920×1080 resolution.
- Resource management: Lazy initialization for heavy operations (e.g., `OCREngine._get_ocr()`). Iterator-based frame streaming.

## Testing Standards
- Naming: `tests/test_<module>.py`. Group by `Test<Feature>` classes.
- Parametrization: Mandate `@pytest.mark.parametrize` for data variations.
- Mocks: `MagicMock(side_effect=...)` for stateful/sequential OCR returns.
- Asserts: `pytest.approx()` for floats, `pytest.raises(Error, match="...")` for exceptions.
- Teardown: Explicitly verify `*.release.assert_called_once()` for memory resources.

## Mandatory Implementation Rules
- Inject all file paths dynamically via `config.py` constants exclusively.
- Catch exact, narrow exception types (e.g., `ValueError`, `KeyError`) in all error handling blocks.
- Enforce complete PEP 484 type signatures (arguments and returns) on all public APIs.
- Implement all operational diagnostics exclusively through the `logging.getLogger(__name__)` interface.
