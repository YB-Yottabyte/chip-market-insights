import json
import pytest

from src.config import Settings
from src.fetch_sec import fetch_company


def test_sec_cache_works_without_network_or_user_agent(tmp_path, monkeypatch):
    settings = Settings(user_agent="", cache_days=7)
    monkeypatch.setattr(type(settings), "raw_sec", property(lambda self: tmp_path))
    payload = {"cik": 1097864, "facts": {}}
    (tmp_path / "CIK0001097864.json").write_text(json.dumps(payload))
    assert fetch_company("ON", settings) == payload


def test_live_sec_request_requires_contact(tmp_path, monkeypatch):
    settings = Settings(user_agent="")
    monkeypatch.setattr(type(settings), "raw_sec", property(lambda self: tmp_path))
    with pytest.raises(ValueError, match="SEC_USER_AGENT"):
        fetch_company("ON", settings)


def test_cached_sec_response_must_match_requested_company(tmp_path, monkeypatch):
    settings = Settings(user_agent="")
    monkeypatch.setattr(type(settings), "raw_sec", property(lambda self: tmp_path))
    wrong_company = {"cik": 1045810, "facts": {}}
    (tmp_path / "CIK0001097864.json").write_text(json.dumps(wrong_company))

    with pytest.raises(RuntimeError, match="CIK or facts mismatch"):
        fetch_company("ON", settings)
