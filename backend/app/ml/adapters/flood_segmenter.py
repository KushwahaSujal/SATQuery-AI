"""Sen1Floods11 flood segmenter (16-channel U-Net) — loads, but deliberately does NOT serve.

The checkpoint is real: `checkpoints/flood_seg/best.pt` loads into the reconstructed architecture in
`backend/app/ml/adapters/flood_unet.py` with `strict=True` across all 118 state_dict entries, at
epoch 9 (Sentinel-1 VV/VH + Sentinel-2 L1C 13 bands + Copernicus DEM, 512x512, Sentinel-2 at
10 m/px). What is missing is the training-time normalisation: the delivery documents the channel
order but never states how the values were scaled, and without that the weights cannot be driven.

Seventeen preprocessing/threshold combinations were swept over the real Sen1Floods11 official test
split (90 scenes) and validation split (89 scenes). None reproduced the delivered global flood IoU
of 0.6292. The closest raw-value scheme scored 0.5403. The scheme that won on validation (S1 clipped
to [-30, 0] dB -> [0, 1], S2/10000, DEM channel zeroed) scored 0.7034 argmax / 0.7273 at threshold
0.30 on test — higher than the delivered number, which is a red flag rather than a win: it only wins
with the DEM channel zeroed, and argmax and threshold 0.30 coincide for us while they diverge in the
delivered report. So the delivered 0.30 threshold provably does not transfer and the calibration
differs from the one the reported score was computed under.

Consequence, decided in project/qna.md Q-041 §5 (full record there and in
project/handoff/ayushman-delivery-2026-09-20.md; evidence in docs/models/flood/): `load_model` is
kept honest and working, and `predict` reports NOT_CONFIGURED instead of a mask. A flood extent
computed under an unknown normalisation would be a number nobody can defend, and flood extent is
exactly the kind of output that gets acted on. The adapter is registered so the situation is visible
in the model registry rather than silently absent.

It is also not routed: the pipeline supplies RGB, and this model needs all 16 co-registered bands,
which `validate_inputs` enforces.
"""
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from backend.app.exceptions import InferenceError, InvalidInputError
from backend.app.logging import logger
from backend.app.ml.adapters.flood_unet import (
    FLOOD_CHANNEL_NAMES,
    FLOOD_CLIP_PERCENTILE,
    FLOOD_INPUT_CHANNELS,
    build_flood_model,
    normalise_flood_input,
)
from backend.app.ml.base import BaseModelAdapter
from backend.app.ml.device import warn_if_cpu_for_heavy_model
from backend.app.schemas.models import ModelResult

#: Ground sampling distance of the Sen1Floods11 chips (Sentinel-1/Sentinel-2), metres/pixel.
FLOOD_GSD_M = 10.0

#: Global flood IoU claimed by the delivered evaluation report.
REPORTED_TEST_IOU = 0.6292

#: Best IoU recovered here on the official test split, argmax, under the preprocessing scheme that
#: won on validation — and only with the DEM channel zeroed. Not a reproduction of the above.
BEST_RECOVERED_IOU_ARGMAX = 0.7034

#: The same scheme at the delivered 0.30 threshold. argmax and 0.30 coincide for us but diverge in
#: the delivered report, which is what proves the threshold does not transfer.
BEST_RECOVERED_IOU_AT_0_30 = 0.7273

#: Best IoU from the closest scheme that feeds the raw delivered values with no rescaling.
CLOSEST_RAW_VALUE_SCHEME_IOU = 0.5403

#: Threshold the delivery reports its numbers at. NOT used: see the module docstring.
DELIVERED_THRESHOLD = 0.30

#: Size of the sweep and the splits it ran over.
PREPROCESSING_COMBINATIONS_SWEPT = 17
TEST_SPLIT_SCENES = 90
VALIDATION_SPLIT_SCENES = 89

_BLOCKER = (
    "The training-time normalisation was never documented, and none of "
    f"{PREPROCESSING_COMBINATIONS_SWEPT} swept preprocessing/threshold combinations reproduced the "
    f"delivered global flood IoU {REPORTED_TEST_IOU} over the Sen1Floods11 official test split "
    f"({TEST_SPLIT_SCENES} scenes) or validation split ({VALIDATION_SPLIT_SCENES} scenes)."
)


class FloodSegmenterAdapter(BaseModelAdapter):
    """`sen1floods11_unet16ch`: 16-channel U-Net on Sen1Floods11 — registered, NOT serving (Q-041).

    The weights load with `strict=True`, but the preprocessing they were trained under is unknown,
    so `predict` returns NOT_CONFIGURED and never a flood mask. Delivered test IoU 0.6292 was not
    reproduced by any of 17 swept schemes; closest raw-value scheme 0.5403, and the scheme that won
    on validation scored 0.7034 argmax on test only with the DEM channel zeroed. Sentinel-1 VV/VH +
    Sentinel-2 L1C + Copernicus DEM at 10 m/px.
    """

    def __init__(self) -> None:
        super().__init__("flood_segmenter")
        self._epoch: Optional[int] = None
        self._metrics: Optional[Dict[str, Any]] = None
        self._train_config: Optional[Dict[str, Any]] = None

    # ---- properties ----------------------------------------------------------------------------

    @property
    def channel_names(self) -> List[str]:
        """The 16 bands, in the order training fixed. Reordering them silently invalidates the model."""
        return list(FLOOD_CHANNEL_NAMES)

    @property
    def trained_gsd_m(self) -> float:
        """Metres/pixel the chips were captured at; config wins so a re-train can correct it."""
        configured = self.config.trained_gsd_m if self.config else None
        return float(configured) if configured is not None else FLOOD_GSD_M

    # ---- lifecycle -----------------------------------------------------------------------------

    def load(self) -> None:
        """Alias for load_model(), for parity with the other adapters."""
        self.load_model()

    def load_model(self) -> None:
        """Builds the 16-channel U-Net and loads the real weights with strict=True.

        This genuinely works and is kept working on purpose: strict=True over all 118 state_dict
        entries is the evidence that `flood_unet.UNetFromScratch` is an exact reconstruction of the
        delivered architecture, and a future fix for the preprocessing needs that to stay true. It
        is `predict` that refuses, not the loader.
        """
        if self._loaded and self._model is not None:
            return
        self.ensure_available()
        ckpt_file = self.checkpoint_path

        try:
            warn_if_cpu_for_heavy_model(self.name, self.device)
            ckpt = torch.load(str(ckpt_file), map_location="cpu", weights_only=False)
            if not isinstance(ckpt, dict) or "model_state_dict" not in ckpt:
                raise ValueError(
                    f"{self.name}: expected a checkpoint dict with a 'model_state_dict' key, "
                    f"got {type(ckpt).__name__} with keys "
                    f"{sorted(ckpt)[:8] if isinstance(ckpt, dict) else 'n/a'}."
                )

            model = build_flood_model(state_dict=ckpt["model_state_dict"])
            model.to(self.device).eval()

            self._model = model
            self._epoch = int(ckpt["epoch"]) if ckpt.get("epoch") is not None else None
            self._metrics = dict(ckpt["metrics"]) if isinstance(ckpt.get("metrics"), dict) else None
            self._train_config = dict(ckpt["config"]) if isinstance(ckpt.get("config"), dict) else None
            self._loaded = True
            served = self.preprocessing == self.RECOVERED_PREPROCESSING
            logger.info(
                f"{self.name}: 16-channel U-Net loaded (epoch {self._epoch}) from {ckpt_file}. "
                + (
                    "Serving with the preprocessing recovered from this checkpoint's own BatchNorm "
                    "statistics — recovered, not supplied by the author (Q-044)."
                    if served else
                    "Weights are real but NOT served: no preprocessing is configured (Q-041 §5, Q-044)."
                )
            )
        except Exception as e:
            self._model = None
            self._loaded = False
            if type(e).__name__ == "ModelUnavailableError":
                raise
            logger.error(f"{self.name} failed to load: {e}", exc_info=True)
            raise InferenceError(f"{self.name} failed to load: {e}", model_name=self.name)

    def unload(self) -> None:
        """Releases the weights and returns the CUDA cache to the driver."""
        if self._model is not None:
            del self._model
        self._model = None
        self._loaded = False
        self._epoch = None
        self._metrics = None
        self._train_config = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info(f"{self.name} unloaded from {self.device}.")

    # ---- inference -----------------------------------------------------------------------------

    def validate_inputs(self, context: Dict[str, Any]) -> None:
        """Requires a 16-channel stack under 'arr', 'image' or 'stack'. RGB can never satisfy it."""
        if not isinstance(context, dict):
            raise InvalidInputError(f"{self.name} requires a context dictionary.")
        arr = next((context[k] for k in ("arr", "image", "stack") if context.get(k) is not None), None)
        if arr is None:
            raise InvalidInputError(
                f"{self.name} requires a {FLOOD_INPUT_CHANNELS}-channel stack "
                f"('arr', 'image' or 'stack') in the order: {', '.join(FLOOD_CHANNEL_NAMES)}."
            )
        if isinstance(arr, torch.Tensor):
            arr = arr.detach().cpu().numpy()
        if not isinstance(arr, np.ndarray):
            raise InvalidInputError(
                f"{self.name} requires a numpy array or torch tensor, got "
                f"'{type(arr).__name__}'."
            )
        if arr.ndim == 4:
            arr = arr[0]
        if arr.ndim != 3:
            raise InvalidInputError(
                f"{self.name} requires a 3-D (C, H, W) or (H, W, C) stack, got shape {arr.shape}."
            )
        # Either layout is accepted; only the channel count is a hard requirement, and a 3-channel
        # RGB tile is the case that actually shows up from the pipeline. Look for the required count
        # on either axis rather than assuming the channel axis is the smaller one: a legitimate
        # (16, 8, 8) CHW stack has more channels than rows, and the old `min` heuristic rejected it
        # while reporting the wrong channel count in the message.
        if FLOOD_INPUT_CHANNELS in (arr.shape[0], arr.shape[-1]):
            channels = FLOOD_INPUT_CHANNELS
        else:
            channels = arr.shape[0] if arr.shape[0] <= arr.shape[-1] else arr.shape[-1]
        if int(channels) != FLOOD_INPUT_CHANNELS:
            raise InvalidInputError(
                f"{self.name} requires exactly {FLOOD_INPUT_CHANNELS} co-registered channels in the "
                f"order {', '.join(FLOOD_CHANNEL_NAMES)}; got {int(channels)} (shape {arr.shape}). "
                f"RGB imagery cannot satisfy this model: it needs Sentinel-1 VV/VH, all 13 "
                f"Sentinel-2 L1C bands and a Copernicus DEM band."
            )

    #: The one accepted value of `configs/models.yaml`'s `preprocessing` key. Anything else, including
    #: the default `None`, keeps the adapter refusing.
    RECOVERED_PREPROCESSING = "bn_recovered_p2p98"

    @property
    def preprocessing(self) -> Optional[str]:
        """Which preprocessing to serve with, or None to refuse. Default: refuse."""
        return self.config.preprocessing if self.config else None

    def predict(self, context: Optional[Dict[str, Any]] = None, **kwargs: Any) -> ModelResult:
        """Segments flood extent **only** when a preprocessing has been configured; otherwise refuses.

        By default `configs/models.yaml` leaves `preprocessing: null` and this refuses
        unconditionally — no input is validated and no weights are loaded, because the blocker is the
        undocumented normalisation rather than anything the caller did, and demanding a valid 16-band
        stack before refusing would imply the request is fixable.

        Setting `preprocessing: "bn_recovered_p2p98"` serves using the normalisation recovered from
        the checkpoint's own BatchNorm statistics (project/qna.md Q-044). That recovery reproduces the
        delivered scores — IoU 0.6244 against 0.6292, F1 0.7684 against 0.7724 — but it is an
        inference about what training did, not a statement from the author, so every result it
        produces carries `preprocessing_provenance: "recovered_not_supplied"` and the caveat in its
        answer text. Flipping that key is a deliberate act.
        """
        if self.preprocessing == self.RECOVERED_PREPROCESSING:
            return self._predict_with_recovered_preprocessing(context, kwargs)
        reason = (
            f"Flood segmentation is NOT_CONFIGURED on this deployment. The checkpoint at "
            f"{self.config.checkpoint_path if self.config else 'checkpoints/flood_seg/best.pt'} is "
            f"real and loads into the reconstructed 16-channel U-Net with strict=True, but "
            f"{_BLOCKER} The closest raw-value scheme reached {CLOSEST_RAW_VALUE_SCHEME_IOU}, and "
            f"the scheme that won on validation reached {BEST_RECOVERED_IOU_ARGMAX} argmax / "
            f"{BEST_RECOVERED_IOU_AT_0_30} at threshold {DELIVERED_THRESHOLD} on test only with the "
            f"DEM channel zeroed, so the delivered {DELIVERED_THRESHOLD} threshold does not "
            f"transfer and the calibration differs. No flood extent can be reported."
        )
        return ModelResult(
            model_name=self.name,
            task="segmentation",
            status="NOT_CONFIGURED",
            answer=f"Flood extent NOT_CONFIGURED: {reason}",
            confidence=None,
            masks=[],
            metadata={
                "status": "NOT_CONFIGURED",
                "code": "MODEL_NOT_CONFIGURED",
                "reason": reason,
                "blocker": _BLOCKER,
                "flood_mask": None,
                "preprocessing": "UNKNOWN",
                "reported_test_iou": REPORTED_TEST_IOU,
                "best_recovered_iou_argmax": BEST_RECOVERED_IOU_ARGMAX,
                "best_recovered_iou_at_delivered_threshold": BEST_RECOVERED_IOU_AT_0_30,
                "closest_raw_value_scheme_iou": CLOSEST_RAW_VALUE_SCHEME_IOU,
                "delivered_threshold": DELIVERED_THRESHOLD,
                "threshold_transferable": False,
                "preprocessing_combinations_swept": PREPROCESSING_COMBINATIONS_SWEPT,
                "test_split_scenes": TEST_SPLIT_SCENES,
                "validation_split_scenes": VALIDATION_SPLIT_SCENES,
                "required_channels": FLOOD_INPUT_CHANNELS,
                "channel_names": self.channel_names,
                "trained_gsd_m": self.trained_gsd_m,
                # Deliberately NOT reporting the checkpoint's epoch or metrics here. The refusal
                # never loads weights, so these would be None on a fresh adapter and populated only
                # if something else had already called load_model() — and the registry hands out
                # singletons, so one diagnostics call would silently change the shape of every
                # later refusal in the process. `checkpoint_epoch: null` also reads as "there is no
                # epoch" when in fact there is one. The delivered values are in docs/models/flood.md.
                "checkpoint_inspected": bool(self._loaded),
                "model_class": "UNetFromScratch",
                "device": str(self.device),
                "qna": "Q-041 §5",
            },
            warnings=[
                "Flood segmenter is NOT_CONFIGURED: training-time normalisation unknown, delivered "
                f"IoU {REPORTED_TEST_IOU} not reproduced by any of "
                f"{PREPROCESSING_COMBINATIONS_SWEPT} swept schemes (Q-041 §5).",
                f"The delivered {DELIVERED_THRESHOLD} decision threshold does not transfer.",
            ],
        )

    def _predict_with_recovered_preprocessing(
        self, context: Optional[Dict[str, Any]], kwargs: Dict[str, Any]
    ) -> ModelResult:
        """Serves a flood mask using the recovered normalisation. Only reachable when configured.

        Unlike the refusal path this does validate its input and does load the weights, because here
        the caller's 16-band stack genuinely determines the answer. The threshold defaults to argmax
        (0.50) rather than the delivered 0.30: under the recovered preprocessing 0.30 trades precision
        for recall at essentially unchanged IoU (0.6238 against 0.6244), so it is offered but not
        imposed — see project/qna.md Q-044 §4.
        """
        ctx: Dict[str, Any] = dict(context or {})
        ctx.update(kwargs)
        self.validate_inputs(ctx)
        self.load_model()

        arr = next(ctx[k] for k in ("arr", "image", "stack") if ctx.get(k) is not None)
        if isinstance(arr, torch.Tensor):
            arr = arr.detach().cpu().numpy()
        arr = np.asarray(arr, dtype=np.float32)
        if arr.ndim == 4:
            arr = arr[0]
        if arr.shape[0] != FLOOD_INPUT_CHANNELS:          # (H, W, C) -> (C, H, W)
            arr = np.transpose(arr, (2, 0, 1))

        threshold = ctx.get("threshold")
        thr = 0.5 if threshold is None else float(threshold)
        if not 0.0 < thr < 1.0:
            raise InvalidInputError(f"threshold must be in (0, 1), got {thr}.")

        try:
            x = normalise_flood_input(arr)
            with torch.no_grad():
                logits = self._model(torch.from_numpy(x[None]).to(self.device))
                prob = torch.softmax(logits.float(), dim=1)[0, 1].detach().cpu().numpy()
        except InvalidInputError:
            raise
        except Exception as e:
            logger.error(f"{self.name} inference failed: {e}", exc_info=True)
            raise InferenceError(f"{self.name} inference failed: {e}", model_name=self.name)

        mask = (prob >= thr).astype(np.uint8)
        flooded = int(mask.sum())
        total = int(mask.size)
        coverage = 100.0 * flooded / total if total else 0.0
        confidence = float(prob[mask > 0].mean()) if flooded else float(1.0 - prob.mean())
        h, w = mask.shape

        return ModelResult(
            model_name=self.name,
            task="segmentation",
            status="OK",
            answer=(
                f"Flood water covers {flooded:,} of {total:,} pixels ({coverage:.2f}% of the scene) "
                f"at threshold {thr:.2f}. The preprocessing this depends on was **recovered from the "
                f"checkpoint's own BatchNorm statistics, not supplied by the model's author**: it "
                f"reproduces the reported scores (IoU 0.6244 against 0.6292 on the official 90-scene "
                f"Sen1Floods11 test split, F1 0.7684 against 0.7724) but has not been confirmed by "
                f"them. Sentinel-1 + Sentinel-2 + DEM at 10 m/px."
            ),
            confidence=confidence,
            masks=[{
                "binary_mask": mask,
                "probability_map": prob.astype(np.float32),
                "label": "flood",
                "pixel_count": flooded,
                "shape": [h, w],
            }],
            metadata={
                "class_name": "flood",
                "threshold": thr,
                "threshold_source": "request" if threshold is not None else "argmax_default",
                "delivered_threshold": DELIVERED_THRESHOLD,
                "pixel_count": flooded,
                "total_pixel_count": total,
                "coverage_pct": round(coverage, 4),
                "preprocessing": self.RECOVERED_PREPROCESSING,
                "preprocessing_provenance": "recovered_not_supplied",
                "preprocessing_clip_percentile": FLOOD_CLIP_PERCENTILE,
                "recovered_test_iou": 0.6244,
                "recovered_test_f1": 0.7684,
                "reported_test_iou": REPORTED_TEST_IOU,
                "test_split": "official Sen1Floods11 flood_test_data, 90 scenes",
                "required_channels": FLOOD_INPUT_CHANNELS,
                "channel_names": self.channel_names,
                "trained_gsd_m": self.trained_gsd_m,
                "output_shape": [h, w],
                "device": str(self.device),
                "model_class": "UNetFromScratch",
                "qna": "Q-044",
            },
            warnings=[
                "Flood preprocessing was recovered from the checkpoint's BatchNorm statistics, not "
                "supplied by the author, and has not been confirmed by them (Q-044).",
            ],
        )
