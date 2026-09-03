from backend.app.geo.metadata import RasterMetadata


def test_metadata_schema():
    meta = RasterMetadata(
        filepath="/data/test.tif",
        filename="test.tif",
        format="GeoTIFF",
        width=512,
        height=512,
        bands=4,
        dtype="uint16",
        crs="EPSG:32632",
        bounds=[500000, 4000000, 505120, 4005120],
        resolution=[10.0, 10.0],
        is_georeferenced=True
    )
    d = meta.to_dict()
    assert d["crs"] == "EPSG:32632"
    assert d["width"] == 512
    assert d["is_georeferenced"] is True
