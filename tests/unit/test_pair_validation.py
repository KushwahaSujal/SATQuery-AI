import pytest
from backend.app.geo.metadata import RasterMetadata
from backend.app.geo.validation import validate_temporal_pair, validate_optical_sar_pair
from backend.app.exceptions import PairValidationError


def test_reject_optical_sar_as_temporal():
    meta1 = RasterMetadata(filepath="opt.tif", filename="opt.tif", format="TIFF", width=100, height=100, bands=3, dtype="uint8")
    meta2 = RasterMetadata(filepath="sar.tif", filename="sar.tif", format="TIFF", width=100, height=100, bands=2, dtype="float32")

    with pytest.raises(PairValidationError):
        validate_temporal_pair(meta1, meta2, modality1="optical", modality2="sar")


def test_accept_optical_sar_pair():
    meta1 = RasterMetadata(filepath="opt.tif", filename="opt.tif", format="TIFF", width=100, height=100, bands=3, dtype="uint8")
    meta2 = RasterMetadata(filepath="sar.tif", filename="sar.tif", format="TIFF", width=100, height=100, bands=2, dtype="float32")

    opt, sar, align = validate_optical_sar_pair(meta1, meta2, modality1="optical", modality2="sar")
    assert opt.filename == "opt.tif"
    assert sar.filename == "sar.tif"
