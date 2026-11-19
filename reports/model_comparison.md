# VLM comparison insights

## Decision

Commit to **SmolVLM-500M-Instruct** as the application's only VLM. BLIP and Florence-2 adapters, model configuration, experiment commands and experiment-only tests have been removed from the application. Their saved results remain in [experiment_results.md](experiment_results.md), with exact raw evidence archived locally.

This is a product direction, not a measured claim that SmolVLM won on accuracy, speed or memory. The saved human-review score sheets are blank. No inference was rerun for this consolidation.

## What the saved outputs show

| Experiment | Observation | Implication |
| --- | --- | --- |
| BLIP, original image | Caption: "a woman dressed as deity performs during festival" | A short baseline; cultural identity and activity claims remain unverified. BLIP was not evaluated across all eleven inputs. |
| Florence global caption | Described participants, vessels and smoke; did not identify a statue/idol | More detailed text did not resolve the central subject in this example. |
| Florence manual crop | Generated the label `lord Ganesha` | Cropping changed recognition, but the generated identity is unverified. |
| Florence grid views | Four independent crop captions | Additional views alone do not establish correct coverage or cultural recognition. |
| Florence dense task | Six validated boxes, all labeled `human face` | Valid coordinates and successful parsing do not establish semantic accuracy. |
| SmolVLM, original image | Mentioned a central figure absent from Florence's global description | Potentially useful coverage, accompanied by unverified identity, cultural and relationship claims. |
| Two-cat sanity image | SmolVLM added an unsupported contact relationship and omitted remotes | Grounding and relationships still require review, even on ordinary scenes. |

## Completion and prompt experiments

| SmolVLM experiment | Inputs | EOS-complete outputs | Conclusion |
| --- | ---: | ---: | --- |
| Original instruction, 128 tokens | 11 | 6/11 | Five captions reached the token ceiling without EOS. |
| Selective extension to 256 tokens | 5 previously truncated inputs | 0/5 | Raising the ceiling did not resolve these truncations. |
| Concise grounded instruction, 128 tokens | 11 | 6/11 | Overall completion remained 54.5%. |

The concise instruction gained EOS on scene_08 and scene_09, and lost EOS on scene_03 and scene_11. It is retained as an explicit option; the original instruction remains the application default. Neither shorter output nor EOS completion proves factual or cultural correctness. Preserve completion flags when consuming captions downstream.

## Resource observations

| Original paired run | Median inference ms | Mean inference ms | Maximum peak CUDA MiB |
| --- | ---: | ---: | ---: |
| Florence-2 | 663.77 | 737.90 | 609.95 |
| SmolVLM-500M | 5617.28 | 5127.57 | 1124.13 |

The concise SmolVLM run recorded median 4926.70 ms and peak 1124.16 MiB. SmolVLM used more time and peak allocated CUDA memory in these saved runs. Its parameter count does not imply a lower measured runtime cost here.

These are single observations on eleven convenience-sampled inputs, with different prompts, tokenizers, preprocessing, beam counts, attention and cache settings. The original paired run used one sanity/warmup image per model; extension and concise runs had no warmup. Inference excludes model loading and file reading, but includes preprocessing, transfers, generation and decoding. CUDA allocated peaks include resident weights and exclude total driver memory. These measurements do not isolate architecture or establish a general hardware benchmark.

## Evidence limits and next work

The collection contains ten photographs and one market illustration, grouped as five cultural and six ordinary inputs. Group labels and source titles are provenance metadata, not verified correctness labels. Possible training-data overlap is unknown. The original user-provided photograph has unspecified public provenance and license.

Use SmolVLM's visible-object coverage as a starting point for downstream work while treating identities and relationships as claims needing review. Remaining priorities are grounded human evaluation, handling incomplete captions and measuring the selected application settings on representative inputs. No quality winner or cultural accuracy score has been established.

All required saved captions and diagnostic outputs are consolidated in [experiment_results.md](experiment_results.md). Exact original JSON, visualizations, blank worksheets, previous cleanup records and retired experiment code are in [.local_archive/smolvlm_commitment_20261108/](../.local_archive/smolvlm_commitment_20261108/), indexed by a manifest with verified SHA-256 checksums. The raw archive is local and ignored by Git; the two consolidated reports preserve the results and interpretation for version control.
