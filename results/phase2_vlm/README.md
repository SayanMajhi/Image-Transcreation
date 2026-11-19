# Phase 2: Image captioning

## Objective
Choose a lightweight captioner that describes useful scene details for later cultural planning on a 4 GB GPU.

## Models and tools
BLIP base was an initial diagnostic baseline. Florence-2-base-ft and SmolVLM-500M-Instruct were compared on 11 images. Only `HuggingFaceTB/SmolVLM-500M-Instruct` remains active, pinned to `a7da5b986cb59b408707209984f360a5f4ad7e47`.

## Implementation summary
`stages/caption.py` loads the selected model and produces caption text, completion flags, settings and timing/memory metadata. `config.py` reads `configs/models.yaml`; the caption CLI uses the existing pipeline entry point. Captions never become verified object records automatically.

## Experimental setup
The paired convenience sample contained five cultural and six ordinary scenes: ten photographs and one illustration/painting. Recorded environment: CUDA, FP16, seed 42, PyTorch 2.15.0+cu132 and Transformers 4.57.6. Timings included preprocessing, transfer, generation and decoding, excluding model loading and image-file reading. There was one timed observation per image after a warmup.

## Important experiments and measured results
| Experiment | Recorded result |
| --- | --- |
| 11-image comparison | Florence median 663.77 ms, mean 737.90 ms; SmolVLM median 5,617.28 ms, mean 5,127.57 ms |
| Maximum allocated CUDA memory | Florence 609.95 MiB; SmolVLM 1,124.13 MiB |
| Initial token ceiling | SmolVLM hit 128 tokens without EOS on 5/11 images; Florence hit its configured ceiling on 0/11 |
| Increase SmolVLM ceiling to 256 on the five failures | All five still hit the ceiling; 0/5 reached EOS |
| Concise prompt on the same 11 images | 6/11 completed, unchanged overall; individual successes/failures shifted |

These measurements compare the recorded configurations, not equalized tasks or a general speed/accuracy benchmark. Allocated CUDA memory excludes driver and other process memory.

## Important findings
Qualitative inspection found that SmolVLM mentioned the central multi-armed idol, diyas and lion costume in some scenes where Florence used generic or incomplete descriptions. This motivated selection, with explicit uncertainty handling. No completed human-verified quality scores establish general superiority.

Florence crop and grid diagnostics did not solve cultural identity: one crop called the idol Ganesha; dense-region output supplied six valid boxes all labeled human face. Geometry and semantic correctness are separate.

## Failure cases and limitations
SmolVLM invented Netherlands/IJsselmeer geography for a California coastal image, omitted a person/activity in a cooking scene, misread a painting as a kitchen and generated repetitions. Longer output did not cure these errors. The concise prompt lost the specific word diyas in one caption. These are recorded model claims and qualitative assessments, not verified cultural labels.

## Final implementation status
SmolVLM remains the only production captioner. BLIP and Florence are retired comparison evidence. Model prompts, preprocessing and generation defaults were not changed by repository cleanup.

## Essential artifacts
- [Raw VLM evidence and provenance](summary.md)
- [Experimental evidence summary](summary.md)
- [Active configuration](../../configs/models.yaml)
- [Caption regression tests](../../tests/test_smolvlm.py)

The experiments directory contains the selected raw outputs; original historical text is preserved separately in the nonignored provenance ZIP. It is a second copy on the same disk; an independent external backup remains unverified. Some original input-image rights/provenance need checking before redistribution.
