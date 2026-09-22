"""Download and cache official SEC Company Facts responses."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import COMPANIES, Settings


LOG = logging.getLogger(__name__)


class SecCompanyFactsClient:
    """Fetch Company Facts for the configured filers with one HTTP session."""

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.session = session or self._make_session()
        self._owns_session = session is None
        self.sleep = sleep

    def __enter__(self) -> SecCompanyFactsClient:
        return self

    def __exit__(self, *_: object) -> None:
        if self._owns_session:
            self.session.close()

    def _make_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self.settings.sec_retry_attempts,
            backoff_factor=self.settings.sec_retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        return session

    def _cache_path(self, ticker: str) -> Path:
        cik = COMPANIES[ticker][0]
        return self.settings.raw_sec / f"CIK{cik:010d}.json"

    @staticmethod
    def _validate_payload(ticker: str, payload: object) -> dict:
        expected_cik = COMPANIES[ticker][0]
        if not isinstance(payload, dict):
            raise ValueError(
                f"Unexpected SEC response for {ticker}: expected JSON object"
            )
        if payload.get("cik") != expected_cik or not isinstance(
            payload.get("facts"), dict
        ):
            raise ValueError(
                f"Unexpected SEC response for {ticker}: CIK or facts mismatch"
            )
        return payload

    def _read_cache(self, path: Path, ticker: str) -> dict:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return self._validate_payload(ticker, payload)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise RuntimeError(f"Cannot read SEC cache file {path}: {error}") from error

    def _cache_is_fresh(self, path: Path) -> bool:
        age_seconds = time.time() - path.stat().st_mtime
        return age_seconds <= self.settings.cache_days * 86400

    def _request(self, ticker: str) -> dict:
        cik = COMPANIES[ticker][0]
        url = f"{self.settings.sec_base_url}/CIK{cik:010d}.json"
        response = self.session.get(
            url,
            headers={
                "User-Agent": self.settings.user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=self.settings.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return self._validate_payload(ticker, payload)

    def fetch_company(self, ticker: str, refresh: bool = False) -> dict:
        """Return a fresh cache entry or fetch one validated SEC response."""
        if ticker not in COMPANIES:
            raise ValueError(f"Unknown company ticker: {ticker}")

        path = self._cache_path(ticker)
        if path.exists() and not refresh and self._cache_is_fresh(path):
            LOG.info("Using cached SEC response: %s", path.name)
            return self._read_cache(path, ticker)

        if not self.settings.user_agent or "@" not in self.settings.user_agent:
            raise ValueError(
                "Set SEC_USER_AGENT in .env to your name and email before live SEC requests"
            )

        try:
            payload = self._request(ticker)
        except (requests.RequestException, ValueError) as error:
            if not path.exists():
                raise RuntimeError(
                    f"Cannot fetch SEC Company Facts for {ticker}: {error}"
                ) from error
            LOG.warning(
                "SEC request failed; using stale cache for %s: %s", ticker, error
            )
            return self._read_cache(path, ticker)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        LOG.info("Downloaded SEC Company Facts for %s", ticker)
        return payload

    def fetch_all(self, refresh: bool = False) -> dict[str, dict]:
        """Fetch configured companies at a conservative request rate."""
        result = {}
        for index, ticker in enumerate(COMPANIES):
            if index:
                self.sleep(self.settings.sec_request_interval_seconds)
            result[ticker] = self.fetch_company(ticker, refresh=refresh)
        return result


def fetch_company(ticker: str, settings: Settings, refresh: bool = False) -> dict:
    """Compatibility entry point for fetching one SEC company."""
    with SecCompanyFactsClient(settings) as client:
        return client.fetch_company(ticker, refresh=refresh)


def fetch_all(settings: Settings, refresh: bool = False) -> dict[str, dict]:
    """Compatibility entry point for fetching all configured companies."""
    with SecCompanyFactsClient(settings) as client:
        return client.fetch_all(refresh=refresh)
