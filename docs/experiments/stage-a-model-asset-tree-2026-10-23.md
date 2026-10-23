# Stage A local model asset inventory

Date: 2026-10-23. Model: `mlx-community/SmolVLM2-2.2B-Instruct-mlx` at
conversion revision `844516024a1c4400d34489b89ee067d794e432ed`.
The existing T7 model directory was read only; no download or model load ran.

`scripts/check_stage_a_model_assets.py` compared the fourteen top-level
asset names and byte sizes to the directory's cached Hugging Face revision
inventory. For ordinary files it recomputed Git blob SHA-1; for the LFS
weight it recomputed SHA-256. The weight also matched the repository's
`model-manifests/manifest.toml` size and SHA-256. No top-level asset was a
symlink. The script exited zero with 14 files and a deterministic
name/size/SHA-256 tree digest of
`8687695ba624849d316f6f76f42d6cac07fce5e082610b9e280cd0ea38f93a9c`.

This proves consistency with the locally cached revision inventory and the
repository weight manifest. The cached inventory was not independently
authenticated against a fresh remote listing in this check. Tokenizer,
processor and model runtime compatibility remain unverified; no inference
was attempted.
