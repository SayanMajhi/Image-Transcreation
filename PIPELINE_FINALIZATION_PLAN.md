# Pipeline Finalization Plan

This document lists the layers that must be fixed and verified before the image-transcreation pipeline is considered complete.

## Target end-to-end flow

```text
User image + request
        ↓
VLM caption
        ↓
Human confirmation
        ↓
LLM cultural plan
        ↓
Human approval
        ↓
Grounding
        ↓
SAM segmentation
        ↓
Mask review/combination
        ↓
Inpainting prompt generation
        ↓
Stable Diffusion inpainting
        ↓
Final image review and evidence
```

## Layer 1: Input and user request

Files:

- `data/`
- `inputs/`
- `captioning/`

Required fixes:

- Accept an image and a plain-language user request.
- Record the source culture only when supplied or verified by the user.
- Record the target culture and the requested transformation.
- Stop if the request is missing or ambiguous.

Done when:

- A user can provide an image and a request without manually designing JSON.
- The application creates the required input JSON automatically.

## Layer 2: VLM captioning

Main files:

- `src/transcreation/stages/caption.py`
- `configs/models.yaml`

Current status: working.

Required checks:

- Caption contains visible objects only.
- Cultural identity is not guessed from appearance.
- Caption status is recorded as `COMPLETE`, `TRUNCATED`, or `UNKNOWN`.
- Caption JSON stores the image hash and model revision.

Done when:

- The VLM output is saved automatically for every new image.
- The user can correct the detected object before planning.

## Layer 3: Human confirmation

Required fixes:

- Show the VLM caption to the user.
- Let the user confirm or correct the object identity.
- Let the user confirm the source and target cultures.
- Let the user confirm which objects may be changed.

Done when:

- The user confirms the object through a simple form or prompt.
- The user does not need to manually edit JSON files.

## Layer 4: LLM cultural planning

Main files:

- `src/transcreation/stages/ollama_planner.py`
- `configs/planner.yaml`

Current status: partially working.

Known issue:

- The raw planner proposed replacements, but its localization phrases used future labels such as `Japanese flatbreads` instead of the original labels. The deterministic validator correctly changed the final decision to `REVIEW`.

Required fixes:

- Ensure `localization_phrase` always names the original object.
- Keep `proposed_change` limited to the future replacement.
- Preserve verified object IDs exactly.
- Return `REVIEW` when the proposal is uncertain or culturally unsupported.
- Show the plan to the user before editing.

Done when:

- A valid `PROPOSE` result contains original-object localization and a separate proposed change.
- A `REVIEW` or `ABSTAIN` result cannot reach inpainting.

## Layer 5: Planner-to-prompt bridge

Current status: missing; the prompt is currently written manually in `inpainting.json`.

Required implementation:

Convert approved planner fields into an inpainting prompt:

```text
[candidate proposed changes].
Preserve [must_preserve items].
Edit only the approved masked areas.
```

The bridge must:

- Read only an approved planner result.
- Reject `REVIEW` and `ABSTAIN` results.
- Include every approved proposed change.
- Include all preservation requirements.
- Avoid inventing food, objects, or cultural replacements.
- Save the generated prompt and its source plan in the output evidence.

Done when:

- The user does not manually copy planner text into `inpainting.json`.
- The prompt clearly states exactly what each mask region should become.

## Layer 6: Grounding

Main files:

- `src/transcreation/stages/grounding.py`
- `configs/grounding.yaml`

Current status: working for requested objects.

Required fixes:

- Ground one requested object phrase at a time.
- Support multiple requested objects by storing each detection result.
- Require visual inspection of every selected box.
- Preserve original image coordinates and hashes.

Done when:

- Every edited object has a confirmed grounding box.
- Incorrect or low-quality boxes stop the pipeline.

## Layer 7: SAM segmentation

Main files:

- `scripts/segment_sam.py`
- `src/transcreation/stages/segmentation.py`
- `configs/sam.yaml`

Current status: working.

Required fixes:

- Select one valid SAM candidate for each grounded object.
- Save the selected candidate and selection note.
- Reject masks that include protected objects or large unwanted regions.

Done when:

- Each selected mask is original-resolution, grayscale, and binary.
- Each selected mask is visually reviewed before inpainting.

## Layer 8: Mask combination

Main files:

- `combine_masks.py`
- `outputs/combined_puris_chole/combined_mask.png`

Current status: implemented for the current research workflow.

Required fixes:

- Store provenance for every source mask.
- Verify all masks have identical dimensions.
- Combine masks using logical OR only.
- Display the combined mask for final human review.
- Keep the combined mask hash in the inpainting input.

Done when:

- The combined mask contains every intended object and no unintended object.
- The mask provenance identifies each source segmentation and candidate index.

## Layer 9: Inpainting model and generation

Main files:

- `src/transcreation/stages/inpainting.py`
- `scripts/inpaint.py`
- `configs/inpainting.yaml`

Current status: functional but image quality is weak.

Current model:

```text
stable-diffusion-v1-5/stable-diffusion-inpainting
```

Known limitations:

- The model generates at approximately 512×512 processing resolution.
- A large combined mask reduces detail quality.
- The current GPU has 4 GB VRAM, so a direct SDXL upgrade may not fit reliably.

Required fixes:

- Use precise prompts generated from the approved plan.
- Prefer separate inpainting passes for separate objects when quality is poor.
- Add an explicit negative prompt if supported by the selected pipeline.
- Keep unmasked pixels unchanged.
- Save the exact prompt, model revision, seed, settings, and mask hash.
- Test whether a higher processing size fits the available GPU.

Done when:

- The generated objects are recognizable and photorealistic.
- The background and protected objects remain unchanged.
- The same input, model revision, and seed produce reproducible output.

## Layer 10: Chained or separate inpainting passes

Current status: not fully automated.

Required fixes:

- Support a first pass using one object mask.
- Use the first output as the source for the second pass.
- Recompute the source hash after every pass.
- Preserve mask provenance across passes.
- Prevent later passes from changing protected earlier results.

Done when:

- Puri and chole can be edited separately without invalid hash or segmentation errors.
- The final output records both passes and their masks.

## Layer 11: Output and evidence

Output location:

```text
outputs/<run_name>/
```

Required files:

- `final.png`
- `comparison.png`
- `inpainting.json`
- source image hash
- mask hash and provenance
- planner output
- approved prompt
- model and configuration details

Done when:

- A reviewer can trace the final image back to the input, plan, boxes, masks, prompt, and model.
- Existing outputs are never overwritten.

## Recommended fix order

1. Fix planner localization validation and confirm the planner output.
2. Implement the planner-to-inpainting prompt bridge.
3. Add user approval before grounding and inpainting.
4. Improve mask provenance and separate-pass support.
5. Improve inpainting prompts and test smaller masks.
6. Test higher processing resolution within the 4 GB GPU limit.
7. Evaluate whether a stronger model is feasible.
8. Run the complete reproducibility and quality checks.

## Final acceptance checklist

- [ ] User gives only an image and a plain-language request.
- [ ] VLM caption is generated and human-confirmed.
- [ ] LLM plan is generated and human-approved.
- [ ] Planner output is converted automatically into an inpainting prompt.
- [ ] Grounding boxes are reviewed.
- [ ] SAM masks are reviewed.
- [ ] Combined or separate masks have provenance.
- [ ] Inpainting edits only approved regions.
- [ ] Final image quality is visually acceptable.
- [ ] Output evidence is complete and reproducible.
