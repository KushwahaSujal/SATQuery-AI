# LocateAnything-3B — pinned upstream and local patches

The model code for LocateAnything ships inside the Hugging Face repo and runs via
`trust_remote_code=True`. The weights directory `checkpoints/locate_anything_3b/` is
gitignored, so the patches we apply to that code live here instead.

Install or repair with:

```bash
python scripts/setup_locate_anything.py            # download (if needed) + patch + verify
python scripts/setup_locate_anything.py --check    # verify only, writes nothing
```

## Upstream

| | |
|---|---|
| Repo | [`nvidia/LocateAnything-3B`](https://huggingface.co/nvidia/LocateAnything-3B) |
| Revision | `c32291ca5e996f5a7a485845b4f57a233936bba0` |
| Reference code | https://github.com/NVlabs/Eagle/tree/main/Embodied |
| Licence | NVIDIA research, non-commercial — fetch from the canonical repo, do not re-host |
| Written for | `transformers 4.51.0` (`generation_config.json`) |
| Patched for | `transformers 5.16.1` (the version in `.venv` on 2026-09-16) |

Weight shards (sha256 = the Hub's LFS etag):

| File | Bytes | sha256 |
|---|---|---|
| `model-00001-of-00002.safetensors` | 4 959 632 160 | `923cfc10fed19808067da6df85a9a4220ddc1f9eb91ceee94c0fecd05d0f2d58` |
| `model-00002-of-00002.safetensors` | 2 701 795 216 | `3459ba101f40594f3f62d3312014f1f8378b4ba3da3b1d562480045938fc7d47` |

## Patches

Written by Sandipan on 2026-09-13; recovered into version control on 2026-09-16 by diffing the
local copy against the pinned revision. Two more fixes to `modeling_qwen2.py` were added later on
2026-09-16 (rotary tables, `rope_theta` source) and the patch regenerated. Hashes are git blob
hashes (`git hash-object`).

| File | Upstream blob | Patched blob |
|---|---|---|
| `modeling_locateanything.py` | `8e61b1d898197e7ad844cb1bfbe56ffff251e4c2` | `c035c3b21d8d58aa700a0e44a355f7c742fa5821` |
| `modeling_qwen2.py` | `e42a31e8620d122ea15dc1c9fef314f77fe05bb0` | `5a95084c322b9204c6558b5c27db459a49fc97d9` |

`modeling_vit.py` and `processing_locateanything.py` are unmodified.

(The first recorded `modeling_qwen2.py` patch, without the two fixes below, hashed to
`0250e78ee0bd9fa778cf6601e8d0eaed5682640e`.)

All changes are transformers 4.x → 5.x compatibility. None change model maths relative to upstream
running on 4.x; the two rotary/`rope_theta` fixes restore it on 5.x, where it was silently broken.

- **`_check_and_adjust_attn_implementation(..., allow_all_kernels=False)`** (both files) — 5.x
  passes the new keyword; the upstream override's signature rejects it.
- **`_tied_weights_keys` list → `{}`** (both files) — 5.x expects a dict. Emptying it is safe:
  `language_model.lm_head.weight` is stored explicitly in `model.safetensors.index.json`, so the
  head is loaded from disk rather than tied to the embeddings.
- **`self.post_init()` at the end of `LocateAnythingForConditionalGeneration.__init__`** — 5.x
  relies on it to finalise weight bookkeeping before loading.
- **`DynamicCache` handling in `Qwen2Model.forward`** — 5.x removed the legacy tuple cache path;
  always use a `Cache` object, and only convert legacy tuples when the helper still exists.
- **`Qwen2RotaryEmbedding`: lazy cos/sin tables instead of buffers** (`modeling_qwen2.py`) —
  upstream registers `inv_freq`, `cos_cached` and `sin_cached` as non-persistent buffers in
  `__init__`. 5.x builds the model on the meta device and those buffers are never recomputed: after
  load, cos/sin were zeros and `inv_freq` NaN/random in every layer, so q and k were zeroed,
  attention went uniform, and generation emitted `<|im_end|>` at once or endless `<null>`. The
  tables are now plain attributes, built on first use (at least 4096 positions) and rebuilt when the
  input's device or dtype changes. Verified by inspecting the buffers after load, and by the output
  becoming correct after the fix.
- **`rope_theta` from `config.rope_parameters["rope_theta"]`** (`modeling_qwen2.py`) — 5.x moved it
  there; `config.rope_theta` no longer exists. Falls back to `config.rope_theta`, and raises
  `ValueError` if neither is present. This replaces the earlier
  `getattr(config, "rope_theta", 10000.0)`.
  **Correction:** this file previously said that fallback "is never hit with these weights". That
  was wrong. The shipped `config.json` does set `rope_theta: 1000000.0`, but under 5.x the value is
  moved into `rope_parameters`, so the `getattr` fallback was hit on every load and the model ran
  with 10 000 instead of the trained 1 000 000.

If `transformers` is upgraded again, re-run `--check`, then re-derive the patches against the
pinned revision rather than editing files under `checkpoints/` by hand.

## Runtime dependencies

The vendor code needs these beyond the backend's base stack just to import or load (versions as
installed on 2026-09-16; listed in `backend/requirements.txt`):

| Package | Version | Why |
|---|---|---|
| `bitsandbytes` | 0.50.2 | 4-/8-bit loading |
| `peft` | 0.21.0 | hard top-level import in `modeling_locateanything.py` |
| `accelerate` | 1.15.0 | `device_map` loading |
| `decord` | 0.6.0 | hard top-level import in `processing_locateanything.py` (training-data loaders only) |
| `lmdb` | 2.3.0 | same |
| `requests` | 2.34.2 | same |

`flash_attn` and `magi_attention` are optional: their imports are guarded and the code falls back
to SDPA.

## Generation note

NVIDIA's sampler (`generate_utils.py`, unpatched) never reads `do_sample`. It samples if and only
if `temperature > 0` (default 0 = greedy). Pass `temperature=0` for deterministic output;
`do_sample=False` on its own does nothing.
