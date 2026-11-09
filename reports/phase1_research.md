# Phase 1: Research and architecture

## Objective
Investigate how an image could be adapted to a requested cultural context while preserving its activity, people and important relationships.

## Models and tools
The implemented research sequence uses SmolVLM-500M, Qwen2.5-3B through Ollama, Grounding DINO Tiny and SAM ViT-Base. Python 3.11, PyTorch, Transformers and typed Python contracts connect the independent stages. These selections were established in later experiments; they are not claimed as Phase 1 experimental results.

## Implementation summary
The intended sequence is image → caption → cultural plan → source-object box → object mask → future inpainting. Each stage has its own input/output evidence. Current commands are independent research tools, not a complete automated transcreation pipeline.

The separation is deliberate: a caption is an unverified description; a plan is a suggestion; a detection score is not object verification; a SAM score is not measured mask accuracy. Human review and evidence hashes provide additional checks, without granting editing permission.

## Experimental setup and important experiments
No separately identifiable original Phase 1 protocol, quantitative benchmark or signed architectural review was found among the current reports. This document consolidates the architecture visible in the implementation and later evidence. It does not invent early experiments or dates. Experiments begin with the [VLM study](phase2_vlm.md).

## Results and findings
Implemented through Phase 5: captioning, typed planning, deterministic candidate quarantine, localization, segmentation and review utilities. Phase 6 inpainting has not started. Sequential model use was chosen for the available 4 GB GPU; later reports contain actual measurements.

## Limitations and final status
The project demonstrates separate components, not verified cultural correctness or completed image adaptation. No genuine human-approved SAM mask is recorded in the prepared cases. Original Phase 1 research notes, if held elsewhere, remain a documentation gap.

## Essential references
- [Application and contracts](../src/transcreation)
- [Model and runtime settings](../configs)
- [Planner research](phase3_llm.md)
- [Localization research](phase4_grounding.md)
- [Segmentation research](phase5_segmentation.md)
