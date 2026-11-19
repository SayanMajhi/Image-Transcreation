# Global and grid-region caption diagnostic

Source: data\durga.jpg

Source SHA-256: `c43e0c3f07b88a310d0e120e7aa32ea5a29cecba37747015bcdec75c284e5ab0`

Model: `microsoft/Florence-2-base-ft` at `f6c1a25888ffc1d945ee8a1a77ac833c7303d46e`

Device: `cuda`; precision: `float16`

All captions below are unreviewed model claims. No view is assumed to contain a particular object. Captions are not combined, and identities are not verified.

| View | Bounds (x1, y1, x2, y2) | Tokens | Inference ms | Peak CUDA MiB | Ceiling reached |
| --- | --- | ---: | ---: | ---: | --- |
| full | (0, 0, 980, 692) | 71 | 2584.80 | 609.95 | False |
| top_left | (0, 0, 490, 346) | 74 | 1152.05 | 609.95 | False |
| top_right | (490, 0, 980, 346) | 75 | 1213.46 | 609.95 | False |
| bottom_left | (0, 346, 490, 692) | 83 | 1195.44 | 609.95 | False |
| bottom_right | (490, 346, 980, 692) | 46 | 766.45 | 609.95 | False |

## full

[Inspect saved view](../../figures/durga_regions_full.png)

A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

## top_left

[Inspect saved view](../../figures/durga_regions_top_left.png)

This is an image of a city. The city has tall buildings. The buildings are gray. The sky is white. There are black wires in the sky. The wires are long and thin. There is smoke coming out of the wires. The smoke is gray and white. The people are holding brown pots in their hands. The pots are large and brown.

## top_right

[Inspect saved view](../../figures/durga_regions_top_right.png)

This is an image of a woman. The woman has a large headdress on. The headdress is red and gold. There is a tree to the right of the woman with green leaves. The tree is tall and green. There are brown pots on the ground in front of the women. The women has long black hair. The sky is white and cloudy.

## bottom_left

[Inspect saved view](../../figures/durga_regions_bottom_left.png)

There are three women standing together. They are all wearing red sarees. The woman on the left is wearing a white saree with a gold embroidery on it. She is also wearing a gold necklace and gold earrings. The two women on the right are holding up a bowl. The bowl is brown in color. One of the women is smiling. There is a man in the background.

## bottom_right

[Inspect saved view](../../figures/durga_regions_bottom_right.png)

A woman is wearing a red and white saree. She has a gold necklace around her neck. There is a woman standing behind her wearing a white and red saree with a white cloth draped over her shoulders.

Generated decoder token IDs excluding the initial decoder-start token and padding after the first EOS; includes EOS and any generated special tokens. This is not the tokenization length of the postprocessed caption.

Single sequential observation per view, full first, without warmup. Inference includes adapter preprocessing, transfers, generation and decoding; excludes model loading, source decoding, crop creation and PNG saving. CUDA peak allocated bytes include resident weights, exclude loading transients; not total driver memory. CPU memory values are null. Repeated loading-time metadata refers to one model load and must not be summed.

## Manual review

Leave ratings blank until you inspect the saved views and source. Enter one label per cell: Correct, Partial, Missing, Incorrect, Uncertain. Use the source and view to judge omissions; do not require an object in every region. For incorrect labels or unsupported claims, record the specific claim and supporting or missing evidence.

Separate visible evidence from cultural interpretation. Do not infer a deity, ritual, festival or nationality from stereotypes, the filename, or model predictions alone. Region crops can remove context or split objects. Native pixels are retained, but a fixed grid does not guarantee that a small object is recognizable. Length and added detail do not establish accuracy. No confidence or automatic quality score is assigned.

| Criterion | Full | Top left | Top right | Bottom left | Bottom right | Visible evidence / claims | Cultural interpretation / verification needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Foreground participants | | | | | | | |
| Religious idol/statue | | | | | | | |
| Ritual objects | | | | | | | |
| Smoke | | | | | | | |
| Clothing | | | | | | | |
| Spatial relationships | | | | | | | |
| Incorrect cultural labels | | | | | | | |
| Unsupported claims | | | | | | | |

Reviewer: __________  Date: __________
