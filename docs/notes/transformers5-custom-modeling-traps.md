# Two silent-failure traps when loading HF models with custom modeling code on transformers 5.x

**Recorded 2026-09-20** while reclaiming disk. The disk reclamation and this rescue are recorded in
`project/handoff/ayushman-delivery-2026-09-20.md` §5 and `project/qna.md` Q-043 §4. This repo runs
**transformers 5.16.1**. Both traps below were hit for real, diagnosed, and fixed in this project —
and both fail *silently*, producing plausible-looking output rather than an error.

The evidence is `locate_anything_qwen2_transformers5.diff` in this directory: the diff between
upstream `modeling_qwen2.py` as shipped in the LocateAnything-3B repo and the patched copy that
actually worked here.

## Why this note exists rather than the code

LocateAnything-3B was removed from the pipeline (Q-023) and its 7.2 GB of weights were deleted on
2026-09-20. The patched `modeling_qwen2.py` lived only inside that gitignored checkpoint directory,
so deleting it would have destroyed the only record of the fix. The model is dead; the two findings
are not. Any future model whose HF repo ships its own `modeling_*.py` — which is common for
remote-sensing VLMs — can hit both.

At the time of writing, **no code in this repo reads `rope_theta` or `rope_parameters`**
(`grep -rn 'rope_theta\|rope_parameters' --include=*.py backend/ third_party/ training/ scripts/ tests/`
returns nothing), so nothing is currently broken. This is a trap list for the next time, not an open bug.

---

## Trap 1 — non-persistent buffers computed in `__init__` are materialised as zeros or NaN

Upstream `Qwen2RotaryEmbedding.__init__` precomputed the rotary cos/sin tables and stored them with
`register_buffer(..., persistent=False)`.

transformers 5.x **instantiates the model on the `meta` device and never re-runs `__init__`**. Any
buffer whose value was computed inside `__init__` is therefore never materialised with real numbers —
it comes back as zeros or NaN after the weights are loaded. `persistent=False` guarantees it is also
absent from the checkpoint, so nothing restores it.

Consequence: `cos`/`sin` become zero, which zeroes `q` and `k`, which makes attention **uniform**.
The model still runs. It still emits fluent text. The text is unconditioned on the image.

**Fix pattern:** build such tables **lazily on first use**, as plain attributes, and rebuild when the
device or dtype changes:

```python
self._cos_cached = None          # not register_buffer

def forward(self, x, seq_len=None):
    if (self._cos_cached is None
            or seq_len > self.max_seq_len_cached
            or self._cos_cached.device != x.device
            or self._cos_cached.dtype != x.dtype):
        self._set_cos_sin_cache(seq_len=max(seq_len, self._MIN_CACHE_LEN),
                                device=x.device, dtype=x.dtype)
```

Note the device/dtype checks: a lazily built cache is not enough on its own, because the first build
may happen on the wrong device.

**How to detect it:** a model that produces confident, grammatical output that ignores the image is
the signature. Check that attention weights are not uniform, and assert no buffer is all-zero or NaN
after load. A `strict=True` `load_state_dict` will **not** catch this — non-persistent buffers are
not in the state_dict at all.

---

## Trap 2 — `rope_theta` moved into `config.rope_parameters`, and the usual fallback is silently wrong

Upstream did:

```python
self.rope_theta = getattr(config, "rope_theta", 10000.0)   # DANGEROUS
```

transformers 5.x moved this field into `config.rope_parameters`, so `getattr(config, "rope_theta", ...)`
misses and the **default silently applies**. This checkpoint was trained with `rope_theta = 1e6`; the
fallback substituted `1e4`, a 100x error in the rotary base.

Consequence: positional encoding is wrong everywhere, and again the model does not crash — it
produces, in the patch author's words, "fluent-looking garbage".

**Fix pattern — read both locations and refuse to guess:**

```python
rope_parameters = getattr(config, "rope_parameters", None) or {}
self.rope_theta = rope_parameters.get("rope_theta", getattr(config, "rope_theta", None))
if self.rope_theta is None:
    raise ValueError("Qwen2 config has no rope_theta (checked rope_parameters and rope_theta).")
```

The important part is not the two-location lookup, it is the **absence of a default**. A wrong
`rope_theta` cannot be detected downstream, so crashing is strictly better than defaulting. This is
the same rule the rest of the codebase follows for checkpoints: refuse rather than fabricate.

---

## The general rule

When an HF repo ships its own `modeling_*.py`, that file was written against whatever transformers
version its authors used. Two classes of breakage follow from a version gap and **neither raises**:

1. anything computed in `__init__` and stored as a non-persistent buffer (meta-device init), and
2. any `getattr(config, "<field>", <default>)` where the field has been relocated in the config schema.

So when adopting such a model: grep its modeling code for `register_buffer(..., persistent=False)`
and for `getattr(config, ..., <default>)`, and verify the model numerically against a published
score before trusting it. The precedent for why this matters is
`backend/app/ml/adapters/changeformer/network.py`: a reimplementation there matched all 373
parameter names and loaded `strict=True`, yet measured IoU 0.019 against 0.726 because `num_heads`
differed. **A clean load is not evidence of correct computation.**
