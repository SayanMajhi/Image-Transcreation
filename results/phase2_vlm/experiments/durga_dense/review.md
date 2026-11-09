# Native dense-region diagnostic

Model: `microsoft/Florence-2-base-ft` at `f6c1a25888ffc1d945ee8a1a77ac833c7303d46e`

Input SHA-256: `c43e0c3f07b88a310d0e120e7aa32ea5a29cecba37747015bcdec75c284e5ab0`

Task: `<DENSE_REGION_CAPTION>`; dimensions: `[980, 692]`

Generated tokens: 28; ceiling: 512; EOS reached: True; suspected truncation: False

Inference: 2444.03 ms; peak CUDA allocated bytes: 639576064

[Inspect annotated boxes and descriptions](../../figures/durga_dense_annotated.png)

These are unreviewed model descriptions and bounding boxes, not pixel-level segmentation masks. No deity, festival or ritual identity is verified. Absence of a detection does not prove object absence.

| Region | Bounding box | Model description | Valid for drawing |
| --- | --- | --- | --- |
| 1 | [77.91000366210938, 366.4139709472656, 132.79000854492188, 438.3819885253906] | human face | True |
| 2 | [236.6699981689453, 396.8619689941406, 290.57000732421875, 463.2939758300781] | human face | True |
| 3 | [384.6499938964844, 414.1619873046875, 431.69000244140625, 481.97796630859375] | human face | True |
| 4 | [545.3699951171875, 399.6299743652344, 587.510009765625, 467.44598388671875] | human face | True |
| 5 | [616.9100341796875, 133.20999145507812, 662.9700317382812, 189.26199340820312] | human face | True |
| 6 | [178.85000610351562, 432.15399169921875, 217.07000732421875, 480.593994140625] | human face | True |

## Parsing, validation and completeness

No recorded parsing or validation errors; this does not establish accuracy.

Generated decoder token IDs excluding the initial decoder-start token and padding after the first EOS; includes EOS and any generated special tokens. This is not the tokenization length of the postprocessed caption.

One sequential execution, no warmup. Inference includes preprocessing, transfers, generation, decoding and official postprocessing. Excludes loading, file reading, box validation and visualization. CUDA peak allocated bytes include resident weights; CPU value is null. Nonfinite parser numbers are saved as strings and flagged invalid.

## Manual review

Leave labels blank until inspecting the original image and annotated boxes. Choose Correct, Partial, Missing, Incorrect or Uncertain. Record region IDs and visible evidence separately from cultural interpretation. Do not infer identity from stereotypes or the model label alone.

| Criterion | Manual label | Region IDs / visible evidence | Cultural interpretation / verification needed |
| --- | --- | --- | --- |
| Large religious idol/statue | | | |
| Foreground participants | | | |
| Raised smoking vessels | | | |
| Smoke | | | |
| Distinctive clothing | | | |
| Spatial relationships | | | |

Unsupported claims or incorrect cultural labels: __________

Reviewer: __________  Date: __________
