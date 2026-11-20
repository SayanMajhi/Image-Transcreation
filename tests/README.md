# Tests: read by pipeline stage

The test modules check software behavior with synthetic inputs, mocked model responses, and temporary files. They do not measure real-image quality or provide genuine human approvals.

## Reading order

| Group | Test files | What they check |
| --- | --- | --- |
| Caption | [test_smolvlm.py](test_smolvlm.py) | Caption model interface, decoding, configuration, and application behavior. |
| Plan | [test_planning.py](test_planning.py), [test_ollama_planner.py](test_ollama_planner.py), [test_planning_policy.py](test_planning_policy.py), [test_source_anchor_prompt.py](test_source_anchor_prompt.py) | Structured plans, mocked Ollama responses, decision rules, and original-object anchoring. |
| Review the proposal | [test_edit_intent.py](test_edit_intent.py), [test_instruction_review.py](test_instruction_review.py), [test_uncertainty_review.py](test_uncertainty_review.py) | Review records, instruction-bearing proposals, and unresolved uncertainty. |
| Locate the object | [test_grounding.py](test_grounding.py), [test_grounding_review.py](test_grounding_review.py) | Detector outputs and selected-box review. |
| Select pixels | [test_segmentation.py](test_segmentation.py), [test_mask_review.py](test_mask_review.py) | SAM outputs, mask binding, and mask review. |
| Generate and preserve | [test_inpainting.py](test_inpainting.py), [test_refined_inpainting.py](test_refined_inpainting.py), [test_mask_blending.py](test_mask_blending.py) | Mocked diffusion, refined-mask validation, and compositing behavior. |
| Alternative editors | [test_appearance_transfer.py](test_appearance_transfer.py), [test_instruction_editor.py](test_instruction_editor.py), [test_reference_replacement.py](test_reference_replacement.py) | Classical transfer, mocked instruction editing, and reference compositing. |
| Connect the stages | [test_orchestration.py](test_orchestration.py), [test_guided_research.py](test_guided_research.py) | Stage handoffs, review boundaries, and research execution with mocks. |
| Run the pilot | [test_pilot.py](test_pilot.py) | Manifest validation, synthetic runs, verification, packaging, and relocation. |
| Connected workflow | [test_workflow.py](test_workflow.py) | Two-pass editing with synthetic adapters, review gates, resume/retry, tamper detection, and independent verification. |

`fixtures/planning/` holds saved planning scenarios used for repeatable checks.

## How to read a test

Read its `setUp` method to understand the synthetic image or record. Then read a `test_...` method: setup defines the input, the call exercises the behavior, and assertions state the expected outcome. A test that rejects an invalid plan or mismatched image hash is a successful check of rejection behavior.

For a short presentation, show `test_planning.py`, `test_inpainting.py`, and `test_pilot.py`: these explain plan validation, image preservation, and repeatability at three different levels.

## Running checks

From the repository root, using the existing environment:

```powershell
# Full suite
.venv\Scripts\python.exe -B -m unittest discover -s tests -v

# One area, keeping the tests directory on the discovery path
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_planning.py" -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_inpainting.py" -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_pilot.py" -v
```

Several modules import fixture classes from other test files. Keeping the current flat layout preserves those imports and existing discovery commands. A future move into subfolders should first extract shared fixtures and update imports and packaging references.

The Phase 9 report records a historical 482-test run. An earlier check in this repository-review chat ran 483 tests successfully. Neither count is an image-quality score; no tests were rerun for this documentation cleanup.
