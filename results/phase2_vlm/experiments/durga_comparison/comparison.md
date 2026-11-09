# Florence caption task comparison

Source image: data\durga.jpg

Input SHA-256: `c43e0c3f07b88a310d0e120e7aa32ea5a29cecba37747015bcdec75c284e5ab0`

Model: `microsoft/Florence-2-base-ft` at `f6c1a25888ffc1d945ee8a1a77ac833c7303d46e`

| Task | Generated tokens | Words | Characters | Inference ms | Peak GPU MiB | Ceiling reached |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| &lt;CAPTION&gt; | 13 | 9 | 52 | 2366.15 | 609.94 | False |
| &lt;DETAILED_CAPTION&gt; | 35 | 28 | 135 | 643.17 | 609.95 | False |
| &lt;MORE_DETAILED_CAPTION&gt; | 71 | 59 | 320 | 1172.93 | 609.95 | False |

## &lt;CAPTION&gt;

A group of women dressed in traditional Indian garb.

## &lt;DETAILED_CAPTION&gt;

In this image we can see a few people, among them some are holding objects, there is a tree, there are some wires, also we can the sky.

## &lt;MORE_DETAILED_CAPTION&gt;

A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

Generated decoder token IDs excluding the initial decoder-start token and padding after the first EOS; includes EOS and any generated special tokens. This is not the tokenization length of the postprocessed caption.

One sequential observation per task; no warmup. Inference includes preprocessing, transfers, generation, decoding and postprocessing; excludes model loading and image file reading. CUDA peak allocated bytes include resident weights, exclude loading transients and are not total driver memory. CPU peak GPU allocation is null.

Each caption JSON records the common seed, decoding settings, device, precision, library versions, loading time and per-task measurements. Loading time is separate and is paid once; repeated metadata values must not be summed.

## Human-review worksheet

All ratings are blank and unreviewed. For each task and criterion, enter one of: Correct, Partial, Missing, Incorrect, Uncertain. Use source-image evidence; a model mention alone is not evidence of correctness. Do not assume that a named object is present.

Keep directly visible facts separate from cultural interpretations. Do not infer the festival, deity or nationality from stereotypes, clothing, or the source filename. Mark interpretations Uncertain without supporting evidence or verified context. For unsupported claims, record the claim and why it is unsupported; an incorrect claim should receive Incorrect. No cultural score or best caption is assigned automatically.

| Criterion | Standard | Detailed | More detailed | Visible evidence / claim | Cultural interpretation / verification needed |
| --- | --- | --- | --- | --- | --- |
| Goddess idol recognition | | | | | |
| Women/participants recognition | | | | | |
| Incense burners or dhunuchi recognition | | | | | |
| Smoke recognition | | | | | |
| Main activity recognition | | | | | |
| Spatial relationships | | | | | |
| Unsupported claims or hallucinations | | | | | |

Reviewer: __________  Date: __________

Manual assessment of omissions and hallucinations: __________

Length alone does not establish caption quality or cultural accuracy.
