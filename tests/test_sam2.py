import pytest
import numpy as np
from PIL import Image
from backend.app.models.sam2 import SAM2Adapter
from backend.app.exceptions import InvalidInputError


def test_sam2_adapter_initialization():
    adapter = SAM2Adapter()
    assert adapter.name.lower() == "sam2"
    assert adapter.model_id == "facebook/sam2.1-hiera-small"
    assert adapter.is_available() is True


def test_sam2_adapter_input_validation():
    adapter = SAM2Adapter()
    with pytest.raises(InvalidInputError):
        adapter.predict(image_or_context=None, box=[10, 10, 50, 50])

    img = Image.new("RGB", (100, 100))
    with pytest.raises(InvalidInputError):
        adapter.predict(image_or_context=img, box=None)

    with pytest.raises(InvalidInputError):
        adapter.predict(image_or_context=img, box=[10, 10])  # Invalid box length


def test_sam2_box_parsing():
    adapter = SAM2Adapter()
    parsed = adapter._parse_box([10, 20, 50, 60], (100, 100))
    assert np.allclose(parsed, [10.0, 20.0, 50.0, 60.0])

    # Normalized box dict
    parsed_dict = adapter._parse_box({"box_2d": [0.2, 0.1, 0.6, 0.5]}, (100, 100))
    # [ymin, xmin, ymax, xmax] = [0.2, 0.1, 0.6, 0.5] -> [x1, y1, x2, y2] = [10, 20, 50, 60]
    assert np.allclose(parsed_dict, [10.0, 20.0, 50.0, 60.0])
