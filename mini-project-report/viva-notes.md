# Viva notes

## One-minute description

The project studies culture-aware image transcreation: changing a culturally associated object while protecting the rest of the picture. It is a guarded research pipeline, not a claim that AI can reliably understand cultures. Captioning and planning are separated from grounded editing; uncertain automated plans stop for review. Guided research uses an explicit specification and verifies every saved pixel outside the allowed region.

## Key algorithms

- **SmolVLM:** writes an image caption used as evidence, not ground truth.
- **Qwen2.5 planner:** proposes an edit and may return a review/abstain decision.
- **Grounding DINO:** proposes object boxes from text queries.
- **SAM:** produces object-mask candidates from a box or points.
- **Reference-guided compositor:** removes the source object in a permitted region, reconstructs a simple background, adds a shadow and places a selected reference cutout.
- **Verifier:** compares source and output RGB pixels, checks protected regions, hashes inputs and replays deterministic requests.

## Strongest result

The Phase 9 pilot completed 6/6 technically, with zero changed pixels outside the permitted region and deterministic replay for selected attempts. This is a locality/reproducibility result.

## Most important limitation

Technical pixel preservation does not measure realism or cultural appropriateness. Five new pilot cases still have no human review, and the clean white-background set does not represent real scenes.

## Likely questions

**Why not claim success?** Because visual/human evidence is incomplete and diffusion attempts were visibly weak.

**Why use a human review boundary?** Cultural interpretation and edit authorization cannot be safely inferred from a planner response alone.

**Why is reference compositing reproducible?** Its request freezes the source, reference, mask, placement and shadow parameters; the verifier checks hashes and pixel equality.

**What would you do next?** Obtain blinded human ratings, test complex backgrounds, use better reference-camera matching and evaluate an appropriately licensed stronger editor.
