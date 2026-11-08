# Vision-Language Model Selection and Experimental Findings

## 1. Purpose and Model Candidates

A **Vision-Language Model (VLM)** describes an image in words. Its caption summarizes visible content but may omit important details.

**Research question:** Which lightweight VLM gives useful scene descriptions for cultural planning on our limited hardware?

| Model | Reason for testing | Role in the project now |
| --- | --- | --- |
| **BLIP base** | Establish a simple image-captioning baseline. | Retired research baseline; the one-image result is preserved. |
| **Florence-2 base-ft** | Test efficient captioning and specialized caption/region tasks. | Retired research baseline; comparison results are preserved. |
| **SmolVLM-500M-Instruct** | Test an instruction-following model on scenes with cultural objects and relationships. | **The only active VLM selected for the application.** |

We compared **three research candidates**, but the intended application uses **only SmolVLM**. This simplifies runtime, dependencies, and caption handling; BLIP and Florence-2 results remain as research evidence.

## 2. Experiment 1 — Understanding a Durga Puja Photograph

### 2.1 Input and Purpose

We used a **980 × 692-pixel, user-provided photograph** of a multi-armed goddess idol behind people in red-and-white traditional clothing, with smoke and handheld *dhunuchi* incense burners.

Identifying only people, smoke, and vessels misses **the scene’s cultural meaning**.

### 2.2 Recorded Observations

| Model | Recorded description (shortened) | Observation |
| --- | --- | --- |
| **BLIP** | “a woman dressed as deity performs during festival” | Short and vague; appeared to mistake the idol for a human performer. |
| **Florence-2** | Described women dancing, traditional clothing, brown bowls, and smoke. | Identified foreground details but **missed the multi-armed idol** in its full-image caption. |
| **SmolVLM** | Described a large, ornate deity, likely a Hindu goddess, with multiple arms and surrounding people. | Captured the central idol more clearly, but made unverified claims and **did not finish within 128 tokens**. |

### 2.3 Interpretation

**Simply put:** Florence saw the people and smoke but missed the idol. SmolVLM noticed the idol but added some unverified details.

**Technical meaning:** **Semantic coverage** concerns whether a caption includes key objects and relationships. A fluent caption can miss a central object; recognizing it does not validate every identity, relationship, or location claim.

This is **one diagnostic example**, not proof of general model superiority.

## 3. Experiment 2 — Testing Florence-2 with Different Views and Tasks

### 3.1 Research Question

Did Florence-2 miss the idol because of caption length or how it processed the full image?

### 3.2 Tests and Results

| Test | What we changed | Recorded result | What it tells us |
| --- | --- | --- | --- |
| `<CAPTION>` | Requested a short caption. | Mostly described people in traditional clothing. | Short captions can omit key context. |
| `<DETAILED_CAPTION>` | Requested more detail. | Added environmental details but did not reliably identify the idol. | More detail does not guarantee better understanding. |
| `<MORE_DETAILED_CAPTION>` | Used the most detailed caption task. | Mentioned women, vessels, smoke, and wires, but still missed the idol. | Longer captions may add details without covering the central cultural object. |
| **Manual crop** | Cropped the image to `[300,100,700,600]`. | Produced “large statue of lord Ganesha.” | The crop made the statue more noticeable, but the deity was **misidentified**. |
| **2 × 2 grid views** | Captioned four image quadrants separately. | Identified local faces, vessels, and smoke; the top-right view called the idol a woman wearing a headdress. | Local views may reveal details while losing the overall scene context. |
| **Dense region captioning** | Requested region-based labels and boxes. | Produced six valid bounding boxes, all labeled `human face`, including one over the idol's face. | **A geometrically valid box is not necessarily a correct object label.** |

### 3.3 Interpretation

A box may correctly answer **“Where?”** without correctly answering **“What?”** This is the difference between **geometric validity** and **semantic correctness**.

This distinction will matter for **Grounding DINO** and **SAM**: valid detection boxes or masks must still match the intended object.

## 4. Experiment 3 — Florence-2 vs. SmolVLM on 11 Images

### 4.1 Experimental Setup

We tested **Florence-2-base-ft** and **SmolVLM-500M-Instruct** on the same 11 images.

| Item | Recorded setup |
| --- | --- |
| Dataset | **11 convenience-sampled images:** 5 cultural scenes and 6 ordinary scenes; **10 photographs and 1 illustration/painting**. |
| Models | Florence-2-base-ft and SmolVLM-500M-Instruct. |
| Measurements | Captions, number of generated tokens, EOS/completion status, inference time, and peak allocated CUDA memory. |
| Environment | CUDA, FP16, random seed **42**, PyTorch `2.15.0+cu132`, Transformers `4.57.6`. |
| Timing boundaries | Included preprocessing, transfers, generation, and decoding; excluded model loading and reading image files. |
| Warmup | One sanity/warmup image per model before the paired run. |

**EOS (end-of-sequence)** signals a finished response. Hitting the token limit without EOS means the caption may be incomplete.

### 4.2 Speed, Memory, and Completion

| Measurement | Florence-2 | SmolVLM-500M |
| --- | ---: | ---: |
| Images tested | 11 | 11 |
| **Median inference time** | **663.77 ms** (≈0.66 s) | **5,617.28 ms** (≈5.62 s) |
| Mean inference time | 737.90 ms | 5,127.57 ms |
| Maximum peak allocated CUDA memory | 609.95 MiB | 1,124.13 MiB |
| Captions reaching the configured token ceiling | 0 | 5 |

**Simply put:** Florence-2 was faster and used less measured GPU memory; SmolVLM sometimes ran out of output tokens.

**Technical caution:** Florence-2 had lower latency and peak **allocated CUDA memory** in these runs, but the models differed in tasks, prompts, image processing, beam counts, cache settings, and output lengths. With **one timed observation per image**, this is not a general performance benchmark; allocated CUDA memory excludes other GPU/driver usage.

### 4.3 Image-by-Image Observations

| Image | SmolVLM result | Florence-2 comparison / key risk |
| --- | --- | --- |
| **01 — Durga Puja** | Recognized a multi-armed goddess-like figure; long, incomplete caption. | Florence described people and smoke but missed the idol. |
| **02 — Diwali lamps** | Used the culturally specific label **diyas**. | Florence used the more generic word **candles**. |
| **03 — Chinese lion dance** | Described a **lion costume** with useful visual detail. | Florence described a generic large costume. |
| **04 — Japanese tea scene** | Mentioned tea equipment but incorrectly claimed the woman was **kneeling on a table**. | Florence gave a simpler, more limited description. |
| **05 — Day of the Dead altar** | Mentioned a framed photograph and fruit but was truncated and did not reliably explain the cultural context. | Florence described generic table decoration. |
| **06 — Parked bicycle** | Included the bicycle, doors, graffiti, and additional details. | Florence was shorter but covered the main elements. |
| **07 — Person cooking by a fire** | Focused on the room and fire but **omitted the person and activity** before truncation. | Florence mentioned a person and fire but may have misidentified the person. |
| **08 — Street football** | Described the activity but became repetitive and was truncated. | Florence gave a more compact description. |
| **09 — Market painting** | Called it a **kitchen/cooking area**, failed to identify it as a painting, and was truncated. | Florence identified a **painting** of people near a table. |
| **10 — Aerial coastal image** | Invented detailed Netherlands/IJsselmeer claims for an image from the California coast. | Florence remained more generic; SmolVLM's output is a strong hallucination example. |
| **11 — Snowy railway station** | Described trains and station details; some details still require checking. | Florence was shorter and broadly described the trains. |

### 4.4 Main Finding

SmolVLM sometimes identified **culturally specific objects**—including *diyas*, a *lion costume*, and the central idol—which matters when the later planner decides what can be edited.

However, SmolVLM also repeated, omitted activities, invented details, and produced incomplete captions. The evidence supports **better coverage of some cultural details in this sample**, **not general accuracy superiority**. **No human-verified quality scores were completed.**

## 5. Experiment 4 — Increasing the Output Token Limit

### 5.1 Problem and Change

In the initial run, **5/11 SmolVLM captions** hit the **128-token limit without EOS**. We reran just those five with `max_new_tokens` increased from **128 to 256**, keeping the images, model revision, prompt, and other decoding settings unchanged.

### 5.2 Results and Interpretation

| Measurement | Result |
| --- | ---: |
| Previously incomplete captions rerun | 5 |
| New token limit | 256 |
| Captions reaching EOS | **0/5** |
| Captions still reaching the token ceiling | **5/5** |

The football caption repeated descriptions of players extending their arms. Other captions added low-value or unsupported details; the Durga caption suggested a temple or sacred site without sufficient visual evidence.

**Simply put:** Doubling the output allowance did not make the model finish; it gave it more room to repeat or guess.

**Technical lesson:** Raising `max_new_tokens` increases the generation budget but does not fix repetition, hallucination, weak visual grounding, or poor prioritization.

## 6. Experiment 5 — Testing a Concise Prompt

### 6.1 What Changed

We kept the **11 images**, SmolVLM model, **greedy decoding**, and **128-token limit** unchanged. Only the instruction changed: up to four short sentences covering the main subject, activity, objects, and relationships, without repetition or speculation.

### 6.2 Results and Interpretation

| Measurement | Original prompt | Concise prompt |
| --- | ---: | ---: |
| Images | 11 | 11 |
| EOS-complete captions | **6/11** | **6/11** |
| Captions reaching token ceiling | 5 | 5 |
| Completion rate | **54.5%** | **54.5%** |

The outcome changed for some individual images:

- **Became complete:** `scene_08` (football) and `scene_09` (painting).
- **Became incomplete:** `scene_03` (lion costume) and `scene_11` (railway station).
- **Still incomplete:** `scene_01`, `scene_05`, and `scene_07`.
- **Lost useful cultural detail:** The Diwali description changed from **“diyas”** to the generic **“small lights.”**
- **Still hallucinated:** The coastal image again led to fabricated geographic details.

**Interpretation:** The concise prompt helped some images but hurt others, with **no overall completion gain** or proven factual improvement. We retained the **original evidence-aware prompt** as the default and saved the concise variant for comparison.

**Timing caveat:** `../.local_archive/experiment_results.md` and `../.local_archive/model_comparison.md` report a concise-run median of **4,926.70 ms**; an earlier `concise_comparison.json` reports **4,376.50 ms** for another result set. Their relationship is **unreconciled**. Do not merge or publish a definitive median until raw run IDs and timestamps are checked. Both report **6/11** completions.

## 7. Final VLM Selection and Reasoning

### 7.1 Selected Model

**`HuggingFaceTB/SmolVLM-500M-Instruct`** is the **only selected application VLM**. BLIP and Florence-2 remain research baselines, not runtime dependencies.

### 7.2 Why We Chose It

1. **Cultural scene understanding matters more than a generic caption alone.** If the caption misses a central deity or a culturally specific object, the planner may choose an inappropriate edit.
2. **SmolVLM captured useful details in several cases.** The multi-armed idol, *diyas*, and lion costume are examples from our tests.
3. **Its measured allocation fit our experimental setup.** Peak allocated CUDA memory was approximately **1.1 GiB** in the recorded run, although total GPU requirements can be higher.
4. **We know its limitations.** SmolVLM was slower than Florence-2 in our experiment, used more allocated CUDA memory, sometimes hallucinated, and hit the token limit on five inputs.
5. **One active VLM keeps the application simpler.** Running all three for every image would use more computation and could produce conflicting descriptions. A single captioner is easier to maintain, debug, and evaluate.

**Decision boundary:** This is a **provisional engineering choice**, not a validated accuracy ranking. We may reconsider it if human evaluation on a representative dataset reveals serious omissions or unsupported claims; we must not overfit to one Durga Puja image.

## 8. Findings and Limitations

### 8.1 Supported Findings

- We ran pretrained captioning models and retained their outputs.
- We compared Florence-2 and SmolVLM on **11 images**.
- Florence-2 had lower **recorded median inference time** and lower **peak allocated CUDA memory** in the measured configurations.
- SmolVLM recognized some culturally useful scene details that Florence-2 missed.
- **5/11** original SmolVLM outputs reached the 128-token ceiling without EOS.
- Increasing the output limit to **256** resulted in **0/5** of those reruns reaching EOS.
- The concise prompt changed individual captions, but the EOS-complete count remained **6/11 (54.5%)**.
- Hallucination, semantic omission, repetition, and truncation remain important risks.

### 8.2 Claims Not Yet Established

- That SmolVLM is the most accurate VLM overall or more culturally accurate on representative images.
- That the complete **planning → grounding → segmentation → inpainting** pipeline is working.
- That our proposed local editing method outperforms the research paper's baselines.
- That our final images preserve culture, emotion, meaning, or visual quality after editing.
- That every post-cleanup command-line test and CLI run passes; those logs were **not included** in the uploaded reports.

### 8.3 Dataset and Responsible-Use Limitations

The **11 convenience-sampled images** are not a validated benchmark. Cultural titles served as **provenance**, not ground-truth labels supplied to the models. Public images may overlap pretraining data; human review scores remain blank; and the original user-provided photo has unspecified public license/provenance.

Cultural assumptions and possible stereotypes also need review before claiming that an edit is culturally appropriate.

## 9. Conclusion

These experiments show why **caption quality matters for culture-aware transcreation**: fluent captions can miss central cultural objects, while longer captions can introduce more errors.

We selected **SmolVLM-500M** as a practical starting point for its cultural-object coverage in some test images, while acknowledging trade-offs in speed, memory, completion, and reliability. The next stage must handle these uncertainties before captions drive image edits.
