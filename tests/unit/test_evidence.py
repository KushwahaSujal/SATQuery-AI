import numpy as np
from backend.app.geo.statistics import calculate_area_statistics
from backend.app.geo.metadata import RasterMetadata
from backend.app.evidence.confidence import ConfidenceEvaluator


def test_metric_area_statistics():
    meta = RasterMetadata(
        filepath="test.tif",
        filename="test.tif",
        format="GeoTIFF",
        width=100,
        height=100,
        bands=1,
        dtype="uint8",
        crs="EPSG:32632",  # Projected UTM (meters)
        resolution=[10.0, 10.0],
        is_georeferenced=True
    )
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:40, 20:40] = 1  # 400 pixels = 40,000 m^2 = 0.04 km^2

    stats = calculate_area_statistics(mask, meta)
    assert stats.changed_pixels == 400
    assert stats.estimated_area_sq_m == 40000.0
    assert stats.estimated_area_sq_km == 0.04


def test_confidence_evaluator_empty():
    conf = ConfidenceEvaluator.evaluate([None, None])
    assert conf is None
