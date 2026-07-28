# Model and weight index

This directory is the canonical index for external model assets. Model files
never belong in Git. Before downloading or converting a model, inspect
`manifest.toml` and verify the configured external data root:

```sh
python3 scripts/verify_model_manifest.py \
  model-manifests/manifest.toml "$AEGIS_DATA_DIR"
```

A passing result means the exact model is already present and must not be
downloaded again. A missing or mismatched result is an acquisition problem,
not permission to fetch implicitly. Network acquisition always requires an
explicit user action.

The manifest path is relative to `AEGIS_DATA_DIR`, so forks may use `.env` or
their local configuration without changing committed records.
