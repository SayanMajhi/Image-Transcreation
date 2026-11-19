# SmolVLM pre-comparison sanity inspection

Image: data/vlm_collection/sanity_cats.png (two cats on pink upholstery, with two remotes).
Caption record: outputs/smolvlm_sanity.json.

The adapter loaded successfully, used the native chat template, and returned only
newly generated text. Visual inspection supports two cats resting on a pink surface.
The claimed relationship that one cat has its head on the other cat's back is
unsupported: the cats are lying separately. The model also omitted the remotes.
Calling the surface a blanket is not established by the image alone.

This is a structural sanity check with observed semantic errors, not a declaration
of accuracy or a model-selection result. This inspection happened before the
11-image paired comparison. Human scores in the comparison worksheet remain blank.
