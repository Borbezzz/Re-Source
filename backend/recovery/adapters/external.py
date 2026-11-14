"""External discovery adapters: Linkup web search (sponsor search integration) and UK Companies House
(legal-entity verification for GB suppliers). Both are bounded, timed out and optional; outputs are
labelled `public_source` and never establish technical eligibility on their own."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from ..config import settings

log = logging.getLogger("recovery.external")


class LinkupClient:
    URL = "https://api.linkup.so/v1/search"

    def __init__(self) -> None:
        self.stats = {"calls": 0, "failures": 0, "last_latency_ms": None}
        self.last_error: Optional[str] = None
        self._cache: dict[str, dict] = {}

    @property
    def available(self) -> bool:
        return settings.linkup_enabled and bool(settings.linkup_api_key)

    def search(self, query: str, *, depth: str = "standard", max_results: int = 5, timeout: float = 25.0) -> dict[str, Any]:
        if not self.available:
            return {"ok": False, "results": [], "detail": "Linkup not configured"}
        if query in self._cache:
            return {**self._cache[query], "cached": True}
        started = time.time()
        try:
            r = httpx.post(self.URL, timeout=timeout, headers={"Authorization": f"Bearer {settings.linkup_api_key}"},
                           json={"q": query, "depth": depth, "outputType": "searchResults"})
            r.raise_for_status()
            data = r.json()
            results = [{"title": x.get("name") or x.get("title"), "url": x.get("url"), "snippet": (x.get("content") or "")[:500]}
                       for x in (data.get("results") or [])[:max_results]]
            self.stats["calls"] += 1
            self.stats["last_latency_ms"] = int((time.time() - started) * 1000)
            out = {"ok": True, "results": results, "query": query, "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "latency_ms": self.stats["last_latency_ms"], "provider": "linkup"}
            self._cache[query] = out
            return out
        except Exception as exc:  # noqa: BLE001
            self.stats["failures"] += 1
            self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            log.warning("Linkup search failed: %s", self.last_error)
            return {"ok": False, "results": [], "detail": self.last_error, "query": query}


class CompaniesHouseClient:
    BASE = "https://api.company-information.service.gov.uk"

    def __init__(self) -> None:
        self.stats = {"calls": 0, "failures": 0}
        self.last_error: Optional[str] = None

    @property
    def available(self) -> bool:
        return settings.companies_house_enabled and bool(settings.companies_house_api_key)

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        r = httpx.get(self.BASE + path, params=params, auth=(settings.companies_house_api_key, ""), timeout=15.0)
        r.raise_for_status()
        self.stats["calls"] += 1
        return r.json()

    def search(self, name: str, limit: int = 5) -> dict[str, Any]:
        if not self.available:
            return {"ok": False, "items": [], "detail": "Companies House not configured"}
        try:
            data = self._get("/search/companies", {"q": name, "items_per_page": limit})
            items = [{"company_number": i.get("company_number"), "title": i.get("title"), "status": i.get("company_status"),
                      "address": i.get("address_snippet"), "date_of_creation": i.get("date_of_creation")} for i in data.get("items", [])]
            return {"ok": True, "items": items, "provider": "companies_house"}
        except Exception as exc:  # noqa: BLE001
            self.stats["failures"] += 1
            self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            return {"ok": False, "items": [], "detail": self.last_error}

    def profile(self, company_number: str) -> dict[str, Any]:
        if not self.available:
            return {"ok": False, "detail": "Companies House not configured"}
        try:
            d = self._get(f"/company/{company_number}")
            return {"ok": True, "company_number": d.get("company_number"), "name": d.get("company_name"), "status": d.get("company_status"),
                    "registered_office": d.get("registered_office_address"), "sic_codes": d.get("sic_codes", []),
                    "date_of_creation": d.get("date_of_creation"), "provider": "companies_house",
                    "source_url": f"https://find-and-update.company-information.service.gov.uk/company/{company_number}"}
        except Exception as exc:  # noqa: BLE001
            self.stats["failures"] += 1
            self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            return {"ok": False, "detail": self.last_error}


linkup = LinkupClient()
companies_house = CompaniesHouseClient()
