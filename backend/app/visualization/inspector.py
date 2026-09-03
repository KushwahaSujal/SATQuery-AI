"""
SatQuery AI — Pixel Inspector & Histogram Statistics Engine
Inspects exact raw band digital numbers, geographic coordinates via CRS geotransforms,
derived index values, model probabilities, and computes 50-bin histograms with percentiles.
"""
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.geo.metadata import RasterMetadata
from backend.app.logging import logger


class InspectorEngine:
    """
    Provides exact pixel-level queries and distribution statistics.
    """

    @classmethod
    def pixel_to_geographic(
        cls,
        col: int,
        row: int,
        transform: Optional[List[float]],
        crs: Optional[str]
    ) -> Optional[Tuple[float, float]]:
        """
        Applies affine geotransform to convert pixel (col, row) to map coordinate (x, y).
        Affine: x = c + a*col + b*row, y = f + d*col + e*row
        GDAL 6-tuple transform: [c, a, b, f, d, e]
        """
        if not transform or len(transform) < 6:
            return None
        c, a, b, f, d, e = transform[:6]
        geo_x = c + a * float(col) + b * float(row)
        geo_y = f + d * float(col) + e * float(row)
        return round(geo_x, 6), round(geo_y, 6)

    @classmethod
    def inspect_pixel(
        cls,
        arr: np.ndarray,
        col: int,
        row: int,
        metadata: Optional[RasterMetadata] = None,
        prob_map: Optional[np.ndarray] = None,
        bin_mask: Optional[np.ndarray] = None,
        derived_indices: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Inspects precise values at (col, row).
        """
        if arr.ndim == 2:
            arr = arr[np.newaxis, ...]
        elif arr.ndim == 3 and arr.shape[2] in [1, 3, 4] and arr.shape[0] > arr.shape[2]:
            arr = np.transpose(arr, (2, 0, 1))

        c, h, w = arr.shape
        if col < 0 or col >= w or row < 0 or row >= h:
            raise ValueError(f"Pixel coordinates ({col}, {row}) out of bounds for image dimensions {w}x{h}.")

        band_values: Dict[str, float] = {}
        for b in range(c):
            b_name = metadata.band_descriptions[b] if (metadata and metadata.band_descriptions and b < len(metadata.band_descriptions)) else f"Band {b + 1}"
            val = float(arr[b, row, col])
            band_values[b_name] = round(val, 4)

        # Geographic coordinates if georeferenced
        geo_coords = None
        if metadata and metadata.is_georeferenced and metadata.transform:
            coords = cls.pixel_to_geographic(col, row, metadata.transform, metadata.crs)
            if coords:
                geo_coords = {"x_coord": coords[0], "y_coord": coords[1], "crs": metadata.crs}

        # Model outputs at this pixel if provided
        model_data: Dict[str, Any] = {}
        if prob_map is not None:
            p_arr = np.squeeze(prob_map)
            if row < p_arr.shape[0] and col < p_arr.shape[1]:
                model_data["probability"] = round(float(p_arr[row, col]), 4)

        if bin_mask is not None:
            m_arr = np.squeeze(bin_mask)
            if row < m_arr.shape[0] and col < m_arr.shape[1]:
                val = int(m_arr[row, col] > 0)
                model_data["prediction_class"] = val
                model_data["status"] = "Changed" if val == 1 else "Unchanged"

        # Standardized top-level contract fields
        raw_coords = [geo_coords["x_coord"], geo_coords["y_coord"]] if geo_coords else None
        crs_val = geo_coords["crs"] if geo_coords else (metadata.crs if metadata else None)
        prob_val = model_data.get("probability")
        pred_val = model_data.get("prediction_class")

        return {
            "row": row,
            "col": col,
            "coordinates": raw_coords,
            "CRS": crs_val,
            "crs": crs_val,
            "band_values": band_values,
            "indices": derived_indices or {},
            "prediction": pred_val,
            "probability": prob_val,
            "pixel": {"col": col, "row": row},
            "geographic_coordinates": geo_coords,
            "derived_indices": derived_indices or {},
            "model_prediction": model_data,
            "raw_values_preserved": True
        }

    @classmethod
    def compute_histogram(
        cls,
        data_2d: np.ndarray,
        num_bins: int = 50,
        units: str = "DN"
    ) -> Dict[str, Any]:
        """
        Computes 50-bin distribution histogram and summary statistics.
        """
        arr = np.squeeze(data_2d).astype(np.float32)
        valid = arr[np.isfinite(arr)]
        if valid.size == 0:
            return {"bins": [], "counts": [], "min": 0, "max": 0, "mean": 0, "std": 0}

        v_min = float(np.min(valid))
        v_max = float(np.max(valid))
        v_mean = float(np.mean(valid))
        v_median = float(np.median(valid))
        v_std = float(np.std(valid))

        p2, p25, p50, p75, p98 = np.percentile(valid, [2, 25, 50, 75, 98])

        counts, bin_edges = np.histogram(valid, bins=num_bins)

        bin_list = []
        for i in range(len(counts)):
            bin_list.append({
                "range_start": round(float(bin_edges[i]), 4),
                "range_end": round(float(bin_edges[i+1]), 4),
                "count": int(counts[i])
            })

        return {
            "total_pixels": int(valid.size),
            "units": units,
            "counts": [int(c) for c in counts],
            "min": round(v_min, 4),
            "max": round(v_max, 4),
            "mean": round(v_mean, 4),
            "median": round(v_median, 4),
            "std": round(v_std, 4),
            "p2": round(float(p2), 4),
            "p25": round(float(p25), 4),
            "p50": round(float(p50), 4),
            "p75": round(float(p75), 4),
            "p98": round(float(p98), 4),
            "percentiles": {
                "p2": round(float(p2), 4),
                "p25": round(float(p25), 4),
                "p50": round(float(p50), 4),
                "p75": round(float(p75), 4),
                "p98": round(float(p98), 4)
            },
            "bins": bin_list
        }
