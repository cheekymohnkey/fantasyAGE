import os

import pytest

from backend import fsutils, jsonutils


def test_safe_dumps_and_loads():
    obj = {"a": 1, "b": 2}
    s = jsonutils.safe_dumps(obj)
    assert s == "{\"a\":1,\"b\":2}"
    loaded = jsonutils.safe_loads(s)
    assert loaded == obj


def test_safe_loads_invalid_raises():
    with pytest.raises(Exception):
        jsonutils.safe_loads("not-json")


def test_ensure_dir_creates_path(tmp_path):
    d = tmp_path / "x" / "y"
    assert not d.exists()
    fsutils.ensure_dir(str(d))
    assert d.exists() and d.is_dir()
