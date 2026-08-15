# SmolVLM2 2.2B pairwise reaction-gain gate — 2026-08-15

Status: Rejected; both cases abstained

## Question

Can the installed offline SmolVLM2 2.2B MLX BF16 model reproduce one accepted
reaction-view promotion and one held-out abstention under one closed protocol?

## Protocol

Each case used four silent 1024x324 side-by-side images. CURRENT was labeled on
the left and PROPOSED on the right. Samples came from the exact owner-reviewed
event and camera geometry. The shared prompt required a substantial visible
improvement in audience reaction while preserving event context; equal, merely
reframed, obstructed or ambiguous comparisons must abstain. A grammar allowed
only `{"decision":"promote"}` or `{"decision":"abstain"}`.

The runner was offline, temperature zero, bounded to four frames, and verified
the 4,493,651,795-byte model weight SHA-256
`ed6c59250704f09f921dce1a25e0d4eff611b6c9c53e382a7eb04ce9113f2773`.
Gain v2 binds model ID/SHA and contains no source path, pixels, free text,
identity or names. Temporary pixels were deleted after hashing.

Gaudeamus input SHA-256 values at 110, 113, 116 and 118.5 seconds:

- `242ecfb30653fffeb858ddd964ff30657665ae394b392a979ccee53544439be3`
- `51052b4891234045904516ed252c2301db38b4aa2923e1a736a369f4bb60df09`
- `c3f3126bc9219b4bea42a1b1455a4d859ccca0fe9735c36b3d5cd3686e2f76a8`
- `32244617f002461fdac62ebe814690e86a8a3a872a8295d5156fc4e258c48b87`

Hundra input SHA-256 values at 218, 220.5, 223 and 225.5 seconds:

- `64d59d0df7793af60b07ce84f4ec543c354e776913f2b2c7b7e1df39896a3682`
- `797611e4146c4934d431873de314b1a9dc35d8557879df3c33a113f98d037523`
- `6852d97e04abd0bc110b675634c25a2e84f01ded2952db56d99f240afa91061a`
- `e8c67800bf8cb00f2e65a2d499502957abd63ba2195dbbeac020328e49207a82`

## Result

Gaudeamus should promote but returned abstain. It took 18.22 seconds model
elapsed, used 9 generation tokens, reached 6.21 GB MLX peak, 831,537,152-byte
maximum RSS and zero swap. Hundra correctly abstained in 16.17 seconds with the
same token/MLX peak, 1,613,250,560-byte maximum RSS and zero swap.

The combined `abstain/abstain` result cannot reject an always-abstain strategy.
The positive failure is sufficient to reject this adapter. Do not integrate it
or prompt-tune these two labels into the model. The model remains accepted only
for the previously bounded group-vs-not-group capability.

Historical external outputs (gain v1, before mandatory model provenance was
versioned as v2):

- `outputs/reaction-view-gain/gaudeamus-smolvlm2-2p2b-pairwise-v1/gain.json`
- `outputs/reaction-view-gain/hundra-smolvlm2-2p2b-pairwise-v1/gain.json`
