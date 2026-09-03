import pytest
import numpy as np
from PIL import Image
from backend.app.geo.raster import RasterInspector
from backend.app.exceptions import UnsupportedFormatError


def test_inspect_png_image(tmp_path):
    img_path = tmp_path / "test_optical.png"
    img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
    img.save(img_path)

    meta = RasterInspector.inspect(img_path)
    assert meta.width == 100
    assert meta.height == 100
    assert meta.bands == 3
    assert meta.format == "PNG"


def test_unsupported_format(tmp_path):
    bad_file = tmp_path / "test.txt"
    bad_file.write_text("not a raster")

    with pytest.raises(UnsupportedFormatError):
        RasterInspector.inspect(bad_file)
