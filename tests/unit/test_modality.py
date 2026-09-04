from backend.app.geo.metadata import RasterMetadata
from backend.app.geo.modality import ModalityDetector


def test_modality_detection_sar():
    meta = RasterMetadata(
        filepath="S1A_IW_GRDH_1SDV_test.tif",
        filename="S1A_IW_GRDH_1SDV_test.tif",
        format="GeoTIFF",
        width=512,
        height=512,
        bands=2,
        dtype="float32",
        sensor="Sentinel-1"
    )
    mod, conf, reason = ModalityDetector.detect(meta)
    assert mod == "sar"
    assert conf > 0.8


def test_modality_detection_optical():
    meta = RasterMetadata(
        filepath="S2A_MSIL2A_test.tif",
        filename="S2A_MSIL2A_test.tif",
        format="GeoTIFF",
        width=512,
        height=512,
        bands=4,
        dtype="uint16",
        sensor="Sentinel-2",
        band_descriptions=["Blue", "Green", "Red", "NIR"]
    )
    mod, conf, reason = ModalityDetector.detect(meta)
    assert mod in ["optical", "multispectral"]
    assert conf > 0.8


def test_modality_detection_unknown():
    meta = RasterMetadata(
        filepath="data_raw.tif",
        filename="data_raw.tif",
        format="TIFF",
        width=256,
        height=256,
        bands=1,
        dtype="uint8"
    )
    mod, conf, reason = ModalityDetector.detect(meta)
    assert mod == "unknown"
    assert conf == 0.0
