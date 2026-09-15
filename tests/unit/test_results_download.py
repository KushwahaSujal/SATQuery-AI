"""Q-017: the results ZIP export must stay inside results/ and contain the job's outputs."""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.app.artifacts.manager import artifact_manager
from backend.app.exceptions import InvalidInputError
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("bad", [".", "..", "", "../..", "-leading-dash", "a" * 129, "job id", "job/.."])
def test_job_dir_rejects_ids_outside_results(bad):
    with pytest.raises(InvalidInputError):
        artifact_manager.get_job_dir(bad)


@pytest.mark.parametrize("good", ["3e35ea2b-1c7a-4d1e-9f00-5b2d6c1a9e11", "oom-mode", "test_geo_req", "showcase-3096b285"])
def test_job_dir_accepts_existing_id_styles(good):
    assert artifact_manager.get_job_dir(good).parent == artifact_manager.base_dir


@pytest.mark.parametrize("path", ["/api/results/%2E%2E/download", "/api/results/%2e/download",
                                  "/api/results/..%2F..%2Fetc/download", "/api/results/no-such-job-q017/download"])
def test_download_traversal_and_missing_job_are_404(client, path):
    assert client.get(path).status_code == 404


def test_download_zips_the_job_folder(client):
    job = "q017-download-test"
    dirs = artifact_manager.init_job_workspace(job)
    (dirs["masks"] / "grounding_mask.png").write_bytes(b"png")
    artifact_manager.save_result_json(job, {"answer": "ok"})
    try:
        r = client.get(f"/api/results/{job}/download")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        assert f"SatQuery_Results_{job}.zip" in r.headers["content-disposition"]
        names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
        assert "masks/grounding_mask.png" in names and "result.json" in names
    finally:
        import shutil
        shutil.rmtree(artifact_manager.get_job_dir(job), ignore_errors=True)
