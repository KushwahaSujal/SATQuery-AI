"""Task 6b: purge job result folders older than SATQUERY_RESULTS_RETENTION_DAYS at startup."""
import os
import time

import pytest

from backend.app.artifacts.manager import purge_old_results, retention_days_from_env


DAY = 86400


def _age(path, days_old):
    """Set both atime and mtime of `path` to `days_old` days in the past."""
    ts = time.time() - days_old * DAY
    os.utime(path, (ts, ts))


def test_purge_removes_only_dirs_older_than_cutoff(tmp_path):
    old_job = tmp_path / "old-job"
    new_job = tmp_path / "new-job"
    old_job.mkdir()
    new_job.mkdir()
    (old_job / "result.json").write_text("{}")
    notes = tmp_path / "notes.txt"
    notes.write_text("hello")

    _age(old_job, 8)
    _age(new_job, 6)
    _age(notes, 8)

    removed = purge_old_results(tmp_path, 7)

    assert removed == ["old-job"]
    assert not old_job.exists()
    assert new_job.exists()
    assert notes.exists()


def test_purge_skips_symlinked_directories(tmp_path):
    real_target = tmp_path / "real-target"
    real_target.mkdir()
    (real_target / "keep.txt").write_text("keep me")

    link = tmp_path / "symlinked-job"
    link.symlink_to(real_target, target_is_directory=True)
    os.utime(link, (time.time() - 8 * DAY, time.time() - 8 * DAY), follow_symlinks=False)

    removed = purge_old_results(tmp_path, 7)

    assert removed == []
    assert link.is_symlink()
    assert real_target.exists()
    assert (real_target / "keep.txt").exists()


def test_purge_missing_directory_returns_empty_list(tmp_path):
    missing = tmp_path / "does-not-exist"
    assert purge_old_results(missing, 7) == []


def test_retention_days_from_env_unset(monkeypatch):
    monkeypatch.delenv("SATQUERY_RESULTS_RETENTION_DAYS", raising=False)
    assert retention_days_from_env() is None


def test_retention_days_from_env_valid(monkeypatch):
    monkeypatch.setenv("SATQUERY_RESULTS_RETENTION_DAYS", "7")
    assert retention_days_from_env() == 7.0


def test_retention_days_from_env_non_numeric(monkeypatch):
    monkeypatch.setenv("SATQUERY_RESULTS_RETENTION_DAYS", "abc")
    assert retention_days_from_env() is None


def test_retention_days_from_env_zero(monkeypatch):
    monkeypatch.setenv("SATQUERY_RESULTS_RETENTION_DAYS", "0")
    assert retention_days_from_env() is None
