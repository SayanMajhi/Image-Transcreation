# Connected guided workflow

The new `scripts.workflow` command connects the existing model stages into a resumable research session. Input is an image and a plain-language request; intermediate JSON, hashes, prompts, and paths are generated automatically.

## Run it

Run commands from the repository root with the existing Python environment:

```powershell
.venv\Scripts\python.exe -m scripts.workflow doctor
.venv\Scripts\python.exe -m scripts.workflow download-models
.venv\Scripts\python.exe -m scripts.workflow start --image data\workflow_demo\croissant.jpg --request "Replace the croissant with one samosa, preserving the white background and camera viewpoint." --target-culture Indian --out outputs\guided_demo_001 --open
```

`download-models` restores the configured pinned files; it may download several gigabytes. Qwen must also be installed in the local Ollama service. `doctor` checks package availability, CUDA, checkpoint cache presence, and Ollama. Cache presence alone does not prove that a model can load.

For a different photo, change `--image`, `--request`, and `--target-culture`. `--source-culture` is optional and should only be supplied when known. Use a new output directory for each new session.

## Review sequence

1. SmolVLM captions the copied source image. Inspect it, enter a complete confirmed or corrected caption, and name the source objects.
2. Qwen plans the changes. The existing deterministic validator checks its output. `REVIEW` returns to source clarification and a fresh planning attempt; `ABSTAIN` ends without editing. Neither can be approved into generation.
3. Inspect and approve a valid proposal, including its preservation requirements.
4. Grounding DINO finds each source object. Select a box explicitly. The image labels start at 1; the terminal displays the corresponding zero-based index.
5. SAM generates mask candidates. Inspect the overlay and choose a valid mask that excludes protected content.
6. The workflow builds a prompt from that approved candidate and the preservation requirements. Inspect the prompt and selected mask, then authorize the research generation.
7. Stable Diffusion edits the region. Independent saved-pixel checks require a nonempty change inside the mask and zero changes outside it.
8. For multiple candidates, the next pass uses the previous output as its actual source, with a new source hash, detection, and segmentation. Later masks cannot overlap earlier edited regions.
9. Inspect the final image and record either acceptance or a need for changes. Technical verification does not automatically accept visual quality.

The browser page displays images and records. Enter review decisions in the terminal and refresh the page after each stage. It has no browser form controls. Type `pause` at a prompt to stop safely. Model-stage failures retain their logs and can be retried in a new attempt folder.

```powershell
.venv\Scripts\python.exe -m scripts.workflow resume --run outputs\guided_demo_001 --open
.venv\Scripts\python.exe -m scripts.workflow status --run outputs\guided_demo_001
```

## Saved evidence

Each session contains a source copy, configuration snapshots, model attempts, reviewer records, generated prompts, per-pass verification, and a final union-mask verification. `final.png` is created after all planned passes meet the pixel checks. `session.json` records progress, including the separate visual-review outcome. `review.html` gathers the current images and evidence for inspection.

Recorded artifacts are checked against their hashes when resuming and before and after transitions. Editing them invalidates the session. Existing sessions retain absolute paths and must be resumed from their original location. Only one process should operate on a session at a time; after a process crash, confirm it has stopped before removing its `.workflow.lock` file.

## Limits and validation

The coordinator is implemented and tested with synthetic model adapters, including two sequential edits, resume/retry behavior, review boundaries, tampered inputs, and outside-mask changes. Synthetic tests are not evidence of live model quality. A successful real run requires downloaded checkpoints and actual operator reviews.

This initial connected route selects original SAM candidates. If no candidate is suitable, reject the session; manual mask refinement remains available through the separate existing research tools. Overlapping edits and automatic mask correction are not supported by this coordinator. Cultural correctness and image realism remain matters for evaluation.

The generation module retains its `RESEARCH_ONLY` metadata. New session review records authorize operator-directed experiments without rewriting historical approvals or claiming automated cultural validation.

## Downloaded example

The demo source is *Croissant-Petr Kratochvil.jpg* by Petr Kratochvil, listed as CC0 on [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Croissant-Petr_Kratochvil.jpg). Original source: [Public Domain Pictures](https://www.publicdomainpictures.net/view-image.php?image=12541&picture=croissant). The download is stored locally at `data/workflow_demo/croissant.jpg`; this is an input photograph, not an example of newly successful generation.
