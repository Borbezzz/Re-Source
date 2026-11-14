"""Builds the versioned seeded scenario fixture `seed-v1` (PRD §10).

Run:  cd backend && uv run python ../data/fixtures/build_seed.py

Everything produced here is SYNTHETIC demo data (`data_origin: synthetic_demo`). Supplier names,
part numbers, approval references and documents are fictional and must never be presented as real
companies or measured performance. Regulatory template references point at real UK CAA sources and
are recorded in templates/registry.

The expected D1/D2 outcomes are NOT computed here; tests/evaluations recompute them independently.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "seed-v1"
START = datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc)  # scenario clock origin
RETRIEVED = "2026-11-14T12:00:00Z"
SYN = "synthetic_demo"


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def at(days: float = 0, hours: float = 0) -> str:
    return iso(START + timedelta(days=days, hours=hours))


def sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def money(amount: str, currency: str = "GBP") -> dict:
    return {"amount": amount, "currency": currency}


# ------------------------------------------------------------------------------------------------
# Suppliers and sites
# ------------------------------------------------------------------------------------------------

SUPPLIERS = [
    ("SUP-NVA", "Northvale Aero Spares B.V.", "NL", ["distributor", "seller"]),
    ("SUP-CAL", "Calderbrook Aerospace Supply Ltd", "GB", ["distributor", "seller", "part145_repair"]),
    ("SUP-PEN", "Pennine Precision Components Ltd", "GB", ["manufacturer"]),
    ("SUP-LOW", "Lowmarsh Trading Ltd", "GB", ["broker", "seller"]),
    ("SUP-ESK", "Esker Component Exchange Ltd", "GB", ["distributor", "seller"]),
    ("SUP-HAR", "Harbourline Aero Components Ltd", "GB", ["distributor", "seller", "part145_repair"]),
    ("SUP-MER", "Meridane Turbine Parts GmbH", "DE", ["oem_distributor", "seller"]),
    ("SUP-CST", "Coastreach Surplus Ltd", "IE", ["broker", "seller"]),
    ("SUP-KES", "Kestrelmoor Fabrication Ltd", "GB", ["manufacturer"]),
]

SITES = [
    # site_id, supplier, name, address, country, geo_id, lat, lon, roles, capabilities
    ("SITE-NVA-RTM", "SUP-NVA", "Northvale Rotterdam distribution centre", "Waalhaven Z.z. (synthetic), Rotterdam", "NL", "GEO-CITY-NLRTM", 51.885, 4.43, ["warehouse", "shipping"], ["stock_holding"]),
    ("SITE-CAL-MAN", "SUP-CAL", "Calderbrook Manchester repair & stores", "Airport Logistics Park (synthetic), Manchester", "GB", "GEO-CITY-GBMAN", 53.36, -2.27, ["warehouse", "repair_station"], ["stock_holding", "fuel_nozzle_flow_test"]),
    ("SITE-CAL-GLA", "SUP-CAL", "Calderbrook Glasgow stores", "Abbotsinch Road (synthetic), Paisley", "GB", "GEO-CITY-GBGLA", 55.87, -4.43, ["warehouse"], ["stock_holding"]),
    ("SITE-PEN-SHF", "SUP-PEN", "Pennine Precision Sheffield works", "Advanced Manufacturing Park (synthetic), Sheffield", "GB", "GEO-CITY-GBSHF", 53.39, -1.38, ["manufacturing"], ["5_axis_machining", "vacuum_brazing", "heat_treatment", "fpi_ndt"]),
    ("SITE-PEN-ROT", "SUP-PEN", "Pennine Precision Rotherham annexe", "Templeborough (synthetic), Rotherham", "GB", "GEO-CITY-GBROT", 53.42, -1.38, ["manufacturing"], ["sheet_metal_forming", "tig_welding"]),
    ("SITE-LOW-LTN", "SUP-LOW", "Lowmarsh Luton unit", "Airport Way (synthetic), Luton", "GB", "GEO-CITY-GBLTN", 51.88, -0.37, ["warehouse"], ["stock_holding"]),
    ("SITE-ESK-BHX", "SUP-ESK", "Esker Birmingham stores", "Elmdon Trading Estate (synthetic), Birmingham", "GB", "GEO-CITY-GBBHX", 52.45, -1.73, ["warehouse"], ["stock_holding"]),
    ("SITE-HAR-SOU", "SUP-HAR", "Harbourline Southampton workshop", "Eastleigh Business Park (synthetic), Southampton", "GB", "GEO-CITY-GBSOU", 50.95, -1.36, ["warehouse", "repair_station"], ["stock_holding", "ngv_inspection"]),
    ("SITE-MER-HAM", "SUP-MER", "Meridane Hamburg logistics hub", "Finkenwerder (synthetic), Hamburg", "DE", "GEO-CITY-DEHAM", 53.54, 9.84, ["warehouse", "shipping"], ["stock_holding", "export_documentation"]),
    ("SITE-CST-DUB", "SUP-CST", "Coastreach Dublin store", "Swords Business Campus (synthetic), Dublin", "IE", "GEO-CITY-IEDUB", 53.45, -6.22, ["warehouse"], ["stock_holding"]),
    ("SITE-KES-BRS", "SUP-KES", "Kestrelmoor Bristol fabrication shop", "Filton Enterprise Zone (synthetic), Bristol", "GB", "GEO-CITY-GBBRS", 51.52, -2.57, ["manufacturing"], ["sheet_metal_forming", "tig_welding", "heat_treatment", "fpi_ndt"]),
]

# Logistics routes to the (synthetic) operator MRO base at East Midlands.
ROUTES = [
    # route_id, from site, mode, label, base transport days, freight GBP, baseline exposure, geos passed
    ("R-RTM-HWC", "SITE-NVA-RTM", "ro-ro ferry + road", "Rotterdam → Harwich ro-ro → East Midlands", 2.0, "1800.00", 0.10, ["GEO-PORT-NLRTM", "GEO-PORT-GBHRW"]),
    ("R-MAN-EMA", "SITE-CAL-MAN", "road", "Manchester → East Midlands by road", 1.0, "600.00", 0.05, []),
    ("R-GLA-EMA", "SITE-CAL-GLA", "road", "Glasgow → East Midlands by road", 1.0, "750.00", 0.05, []),
    ("R-SHF-EMA", "SITE-PEN-SHF", "dedicated courier", "Sheffield → East Midlands courier", 1.0, "500.00", 0.10, []),
    ("R-ROT-EMA", "SITE-PEN-ROT", "dedicated courier", "Rotherham → East Midlands courier", 1.0, "500.00", 0.10, []),
    ("R-LTN-EMA", "SITE-LOW-LTN", "road", "Luton → East Midlands by road", 0.5, "400.00", 0.05, []),
    ("R-BHX-EMA", "SITE-ESK-BHX", "road", "Birmingham → East Midlands by road", 0.5, "400.00", 0.05, []),
    ("R-SOU-EMA", "SITE-HAR-SOU", "road", "Southampton → East Midlands by road", 1.0, "650.00", 0.05, []),
    ("R-HAM-IMM", "SITE-MER-HAM", "short-sea + road", "Hamburg → Immingham short-sea → East Midlands", 3.0, "1400.00", 0.05, ["GEO-PORT-DEHAM", "GEO-PORT-GBIMM"]),
    ("R-DUB-HLY", "SITE-CST-DUB", "ferry + road", "Dublin → Holyhead ferry → East Midlands", 2.0, "900.00", 0.15, ["GEO-PORT-IEDUB", "GEO-PORT-GBHLY"]),
    ("R-BRS-EMA", "SITE-KES-BRS", "road", "Bristol → East Midlands by road", 0.5, "450.00", 0.05, []),
]

GEOS = {
    "GEO-PORT-NLRTM": ("Port of Rotterdam (NLRTM)", "port", 51.95, 4.14),
    "GEO-PORT-GBHRW": ("Harwich International Port (GBHRW)", "port", 51.95, 1.26),
    "GEO-PORT-DEHAM": ("Port of Hamburg (DEHAM)", "port", 53.53, 9.97),
    "GEO-PORT-GBIMM": ("Port of Immingham (GBIMM)", "port", 53.63, -0.19),
    "GEO-PORT-IEDUB": ("Dublin Port (IEDUB)", "port", 53.35, -6.20),
    "GEO-PORT-GBHLY": ("Holyhead Port (GBHLY)", "port", 53.31, -4.63),
    "GEO-PORT-TWKHH": ("Port of Kaohsiung (TWKHH)", "port", 22.61, 120.28),
}

METRICS = [
    # supplier/site, on-time delivery numerator/denominator, quality escapes ppm
    ("SUP-NVA", "SITE-NVA-RTM", 194, 200, 120),
    ("SUP-CAL", "SITE-CAL-MAN", 147, 150, 80),
    ("SUP-CAL", "SITE-CAL-GLA", 88, 92, 150),
    ("SUP-PEN", "SITE-PEN-SHF", 57, 60, 210),
    ("SUP-PEN", "SITE-PEN-ROT", 38, 40, 260),
    ("SUP-LOW", "SITE-LOW-LTN", 45, 50, 900),
    ("SUP-ESK", "SITE-ESK-BHX", 93, 100, 300),
    ("SUP-HAR", "SITE-HAR-SOU", 120, 125, 95),
    ("SUP-MER", "SITE-MER-HAM", 291, 300, 60),
    ("SUP-CST", "SITE-CST-DUB", 44, 50, 1100),
    ("SUP-KES", "SITE-KES-BRS", 76, 80, 180),
]

# ------------------------------------------------------------------------------------------------
# Parts / requirement anchors
# ------------------------------------------------------------------------------------------------

PARTS = {
    "component-primary": {"part": "RS-FN-1001", "rev": "D", "family": "fuel_nozzle", "desc": "Combustor fuel nozzle assembly", "set": "RS-REQ-FN-1001"},
    "component-secondary-a": {"part": "RS-NGV-2040", "rev": "B", "family": "turbine_nozzle_guide_vane", "desc": "HP turbine stage-1 nozzle guide vane segment", "set": "RS-REQ-NGV-2040"},
    "component-secondary-b": {"part": "RS-BD-3110", "rev": "A", "family": "bleed_air_duct", "desc": "HP compressor bleed air duct", "set": "RS-REQ-BD-3110"},
}

CASE_OF = {"component-primary": "case-primary", "component-secondary-a": "case-secondary-a", "component-secondary-b": "case-secondary-b"}

# ------------------------------------------------------------------------------------------------
# Evidence documents (synthetic). Content uses a structured "FIELD: value" body so both Databricks
# ai_extract and the deterministic structured-form parser can read it.
# ------------------------------------------------------------------------------------------------

EVIDENCE: list[dict] = []


def doc(version_id: str, document_id: str, title: str, doc_type: str, authority: str, rank: int, issuer: str,
        subjects: list[str], body: dict, *, site_id: str | None = None, revision: str | None = None,
        effective: str | None = None, expiry: str | None = None, source_url: str | None = None,
        supersedes: str | None = None, header: str = "", include: bool = True) -> dict:
    lines = [header or title.upper(), "Record type: SYNTHETIC DEMONSTRATION RECORD — not a real document", ""]
    for k, v in body.items():
        if isinstance(v, list):
            v = "; ".join(str(x) for x in v)
        lines.append(f"{k}: {v}")
    text = "\n".join(lines)
    ev = {
        "version_id": version_id,
        "document_id": document_id,
        "title": title,
        "doc_type": doc_type,
        "hash": sha(text),
        "source_url": source_url,
        "storage_uri": f"/Volumes/workspace/resource/evidence/{version_id}.txt",
        "authority": authority,
        "authority_rank": rank,
        "issuer": issuer,
        "subject_ids": subjects,
        "site_id": site_id,
        "revision": revision,
        "effective_at": effective,
        "expiry_at": expiry,
        "retrieved_at": RETRIEVED,
        "data_origin": SYN,
        "validation_state": "unvalidated",
        "supersedes_version_id": supersedes,
        "content_text": text,
        "expected_facts": {k.lower().replace(" ", "_"): v for k, v in body.items()},
    }
    if include:
        EVIDENCE.append(ev)
    return ev


def form1(vid, offer, supplier_org, approval, part, rev, serial, status, remarks, site, date="2026-11-10"):
    return doc(vid, f"doc-{vid}", f"CAA Form 1 MO — {part} S/N {serial}", "release_certificate", "release_certificate", 80,
               supplier_org, [offer, part], {
                   "FORM TYPE": "CAA Form 1 MO",
                   "TRACKING NUMBER": f"F1-{serial}",
                   "APPROVING AUTHORITY": "CAA / UNITED KINGDOM",
                   "ORGANISATION": supplier_org,
                   "APPROVAL REFERENCE": approval,
                   "PART NUMBER": part,
                   "REVISION": rev,
                   "SERIAL NUMBER": serial,
                   "QUANTITY": 1,
                   "STATUS WORK": status,
                   "REMARKS": remarks,
                   "RELEASE DATE": date,
               }, site_id=site, revision=rev, effective=f"{date}T00:00:00Z",
               header="CAA FORM 1 MO — AUTHORISED RELEASE CERTIFICATE")


def quote(vid, offer, supplier, part, rev, qty, price, currency, lead, condition, site, valid="2026-12-15"):
    return doc(vid, f"doc-{vid}", f"Quotation {vid.upper()} — {part}", "quote", "supplier_quote", 40, supplier, [offer, part], {
        "PART NUMBER": part, "REVISION": rev, "QUANTITY": qty, "UNIT PRICE": price, "CURRENCY": currency,
        "LEAD TIME DAYS": lead, "CONDITION": condition, "QUOTE VALID UNTIL": valid, "SHIP FROM SITE": site,
    }, site_id=site, revision=rev, expiry=f"{valid}T23:59:59Z")


def trace(vid, offer, supplier, part, serial, b2b, last_op, nis, site):
    return doc(vid, f"doc-{vid}", f"Traceability pack — {part} S/N {serial}", "trace_pack", "supplier_record", 50, supplier, [offer, part], {
        "PART NUMBER": part, "SERIAL NUMBER": serial, "BACK TO BIRTH": b2b, "LAST OPERATOR": last_op,
        "NON INCIDENT STATEMENT": nis,
    }, site_id=site)


def qcert(vid, supplier_id, site_id, standard, number, site_name, expiry, body="Synthetic Certification Body Ltd"):
    return doc(vid, f"doc-{vid}", f"{standard} certificate {number} — {site_name}", "quality_certificate", "certification_body", 70, body,
               [supplier_id, site_id], {
                   "STANDARD": standard, "CERTIFICATE NUMBER": number, "CERTIFIED SITE": site_id,
                   "SITE NAME": site_name, "EXPIRY DATE": expiry, "CERTIFICATION BODY": body,
               }, site_id=site_id, expiry=f"{expiry}T23:59:59Z")


def registry(vid, supplier_id, name, number, status, jurisdiction):
    return doc(vid, f"doc-{vid}", f"Company registry extract — {name}", "registry_extract", "company_registry", 90, f"{jurisdiction} company registry (synthetic extract)",
               [supplier_id], {"LEGAL ENTITY NAME": name, "COMPANY NUMBER": number, "STATUS": status, "JURISDICTION": jurisdiction})


# Primary part technical basis
IPC_FN = doc("ev-ipc-fn-1001-v1", "doc-ipc-fn-1001", "Illustrated parts catalogue extract — fuel nozzle (72-00-10 fig. 4)", "ipc_extract",
             "design_holder", 100, "Representative engine design holder (synthetic)", ["RS-FN-1001", "component-primary"], {
                 "PART NUMBER": "RS-FN-1001", "DESCRIPTION": "Fuel nozzle assembly, combustor position 1-20",
                 "INTERCHANGEABLE REVISIONS": ["D", "D1"], "NON INTERCHANGEABLE REVISIONS": ["C"],
                 "EFFECTIVITY": ["RS-TF2-CFG-A"], "FIGURE": "72-00-10 fig. 4 item 30",
             }, revision="IPC rev 41", effective="2026-06-01T00:00:00Z")
SB_FN_A = doc("ev-sb-fn-0042-a", "doc-sb-fn-0042", "Service bulletin RS-SB-73-0042 Rev A — fuel nozzle tip", "service_bulletin",
              "design_holder", 100, "Representative engine design holder (synthetic)", ["RS-FN-1001"], {
                  "SB NUMBER": "RS-SB-73-0042", "REVISION": "A", "APPLICABLE PART NUMBER": "RS-FN-1001",
                  "MIN DRAWING REVISION": "E", "EFFECTIVE DATE": "2026-09-01",
                  "INSTRUCTION": "Newly manufactured nozzles shall conform to drawing revision E or later.",
              }, revision="A", effective="2026-09-01T00:00:00Z")

IPC_NGV = doc("ev-ipc-ngv-2040-v1", "doc-ipc-ngv-2040", "Illustrated parts catalogue extract — HPT NGV segment (72-50-20 fig. 2)", "ipc_extract",
              "design_holder", 100, "Representative engine design holder (synthetic)", ["RS-NGV-2040", "component-secondary-a"], {
                  "PART NUMBER": "RS-NGV-2040", "DESCRIPTION": "Nozzle guide vane segment, HPT stage 1",
                  "INTERCHANGEABLE REVISIONS": ["B", "C"], "NON INTERCHANGEABLE REVISIONS": ["A"],
                  "EFFECTIVITY": ["RS-TF2-CFG-A"], "FIGURE": "72-50-20 fig. 2 item 10",
              }, revision="IPC rev 41", effective="2026-06-01T00:00:00Z")

IPC_BD = doc("ev-ipc-bd-3110-v1", "doc-ipc-bd-3110", "Illustrated parts catalogue extract — HP bleed duct (36-10-00 fig. 1)", "ipc_extract",
             "design_holder", 100, "Representative engine design holder (synthetic)", ["RS-BD-3110", "component-secondary-b"], {
                 "PART NUMBER": "RS-BD-3110", "DESCRIPTION": "Duct assembly, HP compressor bleed air",
                 "INTERCHANGEABLE REVISIONS": ["A"], "NON INTERCHANGEABLE REVISIONS": [],
                 "EFFECTIVITY": ["RS-TF2-CFG-A"], "FIGURE": "36-10-00 fig. 1 item 5",
             }, revision="IPC rev 41", effective="2026-06-01T00:00:00Z")

# Supplier-level / site-level evidence
registry("ev-reg-nva", "SUP-NVA", "Northvale Aero Spares B.V.", "NL-90000001 (synthetic)", "active", "NL")
registry("ev-reg-cal", "SUP-CAL", "Calderbrook Aerospace Supply Ltd", "GB-90000002 (synthetic)", "active", "GB")
registry("ev-reg-pen", "SUP-PEN", "Pennine Precision Components Ltd", "GB-90000003 (synthetic)", "active", "GB")
registry("ev-reg-low", "SUP-LOW", "Lowmarsh Trading Ltd", "GB-90000004 (synthetic)", "active", "GB")
registry("ev-reg-esk", "SUP-ESK", "Esker Component Exchange Ltd", "GB-90000005 (synthetic)", "active", "GB")
registry("ev-reg-har", "SUP-HAR", "Harbourline Aero Components Ltd", "GB-90000006 (synthetic)", "active", "GB")
registry("ev-reg-mer", "SUP-MER", "Meridane Turbine Parts GmbH", "DE-HRB-90000007 (synthetic)", "active", "DE")
registry("ev-reg-cst", "SUP-CST", "Coastreach Surplus Ltd", "IE-90000008 (synthetic)", "active", "IE")
registry("ev-reg-kes", "SUP-KES", "Kestrelmoor Fabrication Ltd", "GB-90000009 (synthetic)", "active", "GB")

qcert("ev-qc-nva-rtm", "SUP-NVA", "SITE-NVA-RTM", "AS9120B", "Q-90101", "Northvale Rotterdam distribution centre", "2027-08-31")
qcert("ev-qc-cal-man", "SUP-CAL", "SITE-CAL-MAN", "AS9120B", "Q-90102", "Calderbrook Manchester repair & stores", "2027-05-31")
qcert("ev-qc-pen-shf", "SUP-PEN", "SITE-PEN-SHF", "AS9100D", "Q-90103", "Pennine Precision Sheffield works", "2027-03-31")
qcert("ev-qc-low-ltn", "SUP-LOW", "SITE-LOW-LTN", "AS9120B", "Q-90104", "Lowmarsh Luton unit", "2027-01-31")
qcert("ev-qc-esk-bhx", "SUP-ESK", "SITE-ESK-BHX", "AS9120B", "Q-90105", "Esker Birmingham stores", "2027-04-30")
qcert("ev-qc-har-sou", "SUP-HAR", "SITE-HAR-SOU", "AS9120B", "Q-90106", "Harbourline Southampton workshop", "2027-06-30")
# Meridane's certificate expires 5 days into the scenario: used by the clock/expiry verification (AC-21).
qcert("ev-qc-mer-ham", "SUP-MER", "SITE-MER-HAM", "AS9120B", "Q-90107", "Meridane Hamburg logistics hub", (START + timedelta(days=5)).strftime("%Y-%m-%d"))
# Coastreach certificate already expired (AC-07 expired evidence).
qcert("ev-qc-cst-dub", "SUP-CST", "SITE-CST-DUB", "AS9120B", "Q-90108", "Coastreach Dublin store", "2026-10-31")
qcert("ev-qc-kes-brs", "SUP-KES", "SITE-KES-BRS", "AS9100D", "Q-90109", "Kestrelmoor Bristol fabrication shop", "2027-09-30")
# Pennine holds AS9100 for Sheffield only; Rotherham relies on it wrongly (AC-07 wrong-site evidence).

doc("ev-poa-pen", "doc-poa-pen", "UK Part 21 Subpart G production organisation approval — Pennine Precision", "poa_certificate", "competent_authority_record", 95,
    "UK CAA approval record (synthetic)", ["SUP-PEN", "SITE-PEN-SHF"], {
        "APPROVAL REFERENCE": "UK.21G.99001 (synthetic)", "ORGANISATION": "Pennine Precision Components Ltd",
        "SCOPE": ["fuel_nozzle", "bleed_air_duct"], "APPROVED SITES": ["SITE-PEN-SHF"],
    }, site_id="SITE-PEN-SHF")
doc("ev-poa-kes", "doc-poa-kes", "UK Part 21 Subpart G production organisation approval — Kestrelmoor Fabrication", "poa_certificate", "competent_authority_record", 95,
    "UK CAA approval record (synthetic)", ["SUP-KES", "SITE-KES-BRS"], {
        "APPROVAL REFERENCE": "UK.21G.99002 (synthetic)", "ORGANISATION": "Kestrelmoor Fabrication Ltd",
        "SCOPE": ["bleed_air_duct"], "APPROVED SITES": ["SITE-KES-BRS"],
    }, site_id="SITE-KES-BRS")
doc("ev-nadcap-pen-shf", "doc-nadcap-pen-shf", "Nadcap accreditation summary — Pennine Sheffield", "special_process_accreditation", "accreditation_body", 70,
    "Synthetic accreditation summary", ["SUP-PEN", "SITE-PEN-SHF"], {
        "SITE": "SITE-PEN-SHF", "PROCESSES": ["vacuum_brazing", "heat_treatment", "fpi_ndt"], "EXPIRY DATE": "2027-02-28",
    }, site_id="SITE-PEN-SHF", expiry="2027-02-28T23:59:59Z")
doc("ev-nadcap-kes-brs", "doc-nadcap-kes-brs", "Nadcap accreditation summary — Kestrelmoor Bristol", "special_process_accreditation", "accreditation_body", 70,
    "Synthetic accreditation summary", ["SUP-KES", "SITE-KES-BRS"], {
        "SITE": "SITE-KES-BRS", "PROCESSES": ["tig_welding", "heat_treatment", "fpi_ndt"], "EXPIRY DATE": "2027-05-31",
    }, site_id="SITE-KES-BRS", expiry="2027-05-31T23:59:59Z")
doc("ev-nadcap-pen-rot", "doc-nadcap-pen-rot", "Process capability statement — Pennine Rotherham", "special_process_accreditation", "supplier_record", 40,
    "Pennine Precision Components Ltd", ["SUP-PEN", "SITE-PEN-ROT"], {
        "SITE": "SITE-PEN-ROT", "PROCESSES": ["tig_welding", "heat_treatment", "fpi_ndt"], "EXPIRY DATE": "2027-02-28",
    }, site_id="SITE-PEN-ROT", expiry="2027-02-28T23:59:59Z")

for sup, site, num, den, ppm in METRICS:
    doc(f"ev-metrics-{site.lower()}", f"doc-metrics-{site.lower()}", f"Supplier performance summary — {site} (scenario fixture)", "metrics_report",
        "scenario_fixture", 30, "Re-Source demo fixture", [sup, site], {
            "SITE": site, "ON TIME DELIVERIES": num, "DELIVERIES": den, "ON TIME DELIVERY RATE": round(num / den, 4),
            "QUALITY ESCAPES PPM": ppm, "WINDOW": "12 months to 2026-10-31",
        }, site_id=site)

# ------------------------------------------------------------------------------------------------
# Offers (PRD §10 primary ranking fixture; secondary cases per §2.1)
# ------------------------------------------------------------------------------------------------

OFFERS: list[dict] = []
PLANS: dict[str, dict] = {}


def offer(cid, case, route, label, part, rev, sup, site, route_id, price, currency, evidence, *, condition=None, stock=None,
          capacity=None, manufacturer=None, seller=None, route_specific=None):
    OFFERS.append({
        "candidate_id": cid, "case_id": case, "route": route, "label": label, "part_id": part, "revision": rev,
        "supplier_id": sup, "site_id": site, "manufacturer_id": manufacturer, "seller_id": seller or sup,
        "quantity": 1, "condition": condition, "quote_version": f"q-{cid.lower()}-v1", "price": money(price, currency),
        "stock": stock, "capacity": capacity, "logistics_route_id": route_id, "plan_id": f"plan-{cid.lower()}",
        "evidence_ids": evidence, "route_specific": route_specific or {}, "source_adapter": "seeded_offers", "data_origin": SYN,
    })


def plan(cid, steps, extra_costs, slots=None):
    PLANS[cid] = {"plan_id": f"plan-{cid.lower()}", "candidate_id": cid, "steps": steps, "extra_costs": extra_costs,
                  "capacity_slots": slots, "data_origin": SYN, "source": "scenario fixture (synthetic durations)"}


def step(sid, name, kind, days, deps=(), rng=None, assumption=None):
    return {"step_id": sid, "name": name, "kind": kind, "duration": {"value": days, "unit": "days"}, "depends_on": list(deps),
            "duration_range": rng, "assumption": assumption, "source": "scenario fixture"}


# --- Primary: fuel nozzle RS-FN-1001 rev D ---
P = "case-primary"
quote("ev-q-pa", "OFF-PA", "Northvale Aero Spares B.V.", "RS-FN-1001", "D", 1, "46200.00", "GBP", 1, "OVERHAULED", "SITE-NVA-RTM")
form1("ev-f1-pa", "OFF-PA", "Northvale Aero Services (UK Part 145)", "UK.145.90011 (synthetic)", "RS-FN-1001", "D", "FN7731", "OVERHAULED",
      "Overhauled per CMM 73-10-05 rev 12; SB RS-SB-73-0042 embodied", "SITE-NVA-RTM")
trace("ev-tr-pa", "OFF-PA", "Northvale Aero Spares B.V.", "RS-FN-1001", "FN7731", "yes", "Synthetic Air Lines plc", "yes", "SITE-NVA-RTM")
offer("OFF-PA", P, "BUY", "Offer A — overhauled spare, Rotterdam stock", "RS-FN-1001", "D", "SUP-NVA", "SITE-NVA-RTM", "R-RTM-HWC", "46200.00", "GBP",
      ["ev-q-pa", "ev-f1-pa", "ev-tr-pa", "ev-qc-nva-rtm", "ev-reg-nva", "ev-metrics-site-nva-rtm", "ev-ipc-fn-1001-v1", "ev-sb-fn-0042-a"],
      condition="OVERHAULED", stock=2)
plan("OFF-PA", [
    step("alloc", "Stock allocation and packing", "procurement", 1.0),
    step("docs", "Release certificate and trace review", "documentation", 0.5),
    step("ship", "Transport via Rotterdam → Harwich ro-ro", "transport", 2.0, ["alloc", "docs"], [1.5, 3.0], "Daily ro-ro sailing"),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [])

quote("ev-q-pb", "OFF-PB", "Calderbrook Aerospace Supply Ltd", "RS-FN-1001", "D", 1, "55400.00", "GBP", 1, "INSPECTED/TESTED", "SITE-CAL-MAN")
form1("ev-f1-pb", "OFF-PB", "Calderbrook Aerospace Supply Ltd (UK Part 145)", "UK.145.90012 (synthetic)", "RS-FN-1001", "D", "FN8102", "INSPECTED/TESTED",
      "Flow-tested to CMM 73-10-05 rev 12 after receipt; SB RS-SB-73-0042 embodied", "SITE-CAL-MAN")
trace("ev-tr-pb", "OFF-PB", "Calderbrook Aerospace Supply Ltd", "RS-FN-1001", "FN8102", "yes", "Synthetic Regional Airways Ltd", "yes", "SITE-CAL-MAN")
offer("OFF-PB", P, "BUY", "Offer B — inspected/tested spare, Manchester", "RS-FN-1001", "D", "SUP-CAL", "SITE-CAL-MAN", "R-MAN-EMA", "55400.00", "GBP",
      ["ev-q-pb", "ev-f1-pb", "ev-tr-pb", "ev-qc-cal-man", "ev-reg-cal", "ev-metrics-site-cal-man", "ev-ipc-fn-1001-v1", "ev-sb-fn-0042-a"],
      condition="INSPECTED/TESTED", stock=1)
plan("OFF-PB", [
    step("alloc", "Stock allocation", "procurement", 1.0),
    step("test", "Flow bench functional test", "inspection", 3.0, ["alloc"], [2.0, 4.0], "Test rig slot confirmed in quote"),
    step("ship", "Road transport Manchester → East Midlands", "transport", 1.0, ["test"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [])

quote("ev-q-pc", "OFF-PC", "Pennine Precision Components Ltd", "RS-FN-1001", "D", 1, "66500.00", "GBP", 21, "NEW", "SITE-PEN-SHF")
doc("ev-dl-pc", "doc-dl-pc", "Design data licence — RS-FN-1001 drawing", "design_licence", "design_holder", 90, "Representative engine design holder (synthetic)",
    ["OFF-PC", "RS-FN-1001", "SUP-PEN"], {
        "DESIGN HOLDER": "Representative engine design holder (synthetic)", "PART NUMBER": "RS-FN-1001", "DRAWING NUMBER": "DWG-FN-1001",
        "DRAWING REVISION": "E", "LICENCE REFERENCE": "DDL-90031 (synthetic)", "LICENSEE": "Pennine Precision Components Ltd",
    }, site_id="SITE-PEN-SHF", revision="E")
doc("ev-fai-pc", "doc-fai-pc", "AS9102 first article inspection report — RS-FN-1001 (Sheffield)", "fai_report", "supplier_quality_record", 60,
    "Pennine Precision Components Ltd", ["OFF-PC", "RS-FN-1001", "SITE-PEN-SHF"], {
        "PART NUMBER": "RS-FN-1001", "REVISION": "D", "DRAWING REVISION": "E", "SITE": "SITE-PEN-SHF", "REPORT NUMBER": "FAI-90041", "RESULT": "complete",
    }, site_id="SITE-PEN-SHF")
offer("OFF-PC", P, "MAKE", "Offer C — commissioned manufacture, Sheffield", "RS-FN-1001", "D", "SUP-PEN", "SITE-PEN-SHF", "R-SHF-EMA", "66500.00", "GBP",
      ["ev-q-pc", "ev-dl-pc", "ev-fai-pc", "ev-poa-pen", "ev-nadcap-pen-shf", "ev-qc-pen-shf", "ev-reg-pen", "ev-metrics-site-pen-shf", "ev-ipc-fn-1001-v1", "ev-sb-fn-0042-a"],
      condition="NEW", capacity={"machining_slots": [[5, 13], [16, 30]]}, manufacturer="SUP-PEN",
      route_specific={"design_basis": "Licensed design data DWG-FN-1001 rev E", "special_processes": ["vacuum_brazing", "heat_treatment", "fpi_ndt"],
                      "qualification": "AS9102 FAI complete at Sheffield", "tooling": "Existing fixture set"})
plan("OFF-PC", [
    step("licence", "Design data licence confirmation", "documentation", 2.0),
    step("material", "Material procurement (Ni alloy bar)", "procurement", 5.0, [], [4.0, 7.0]),
    step("machine", "5-axis machining and vacuum brazing", "manufacture", 8.0, ["licence", "material"], [7.0, 10.0], "Requires machining slot"),
    step("heat", "Heat treatment", "manufacture", 2.0, ["machine"]),
    step("fai", "Conformity inspection against FAI baseline", "qualification", 3.0, ["heat"]),
    step("release", "CAA Form 1-21 release by POA holder", "documentation", 1.0, ["fai"]),
    step("ship", "Courier Sheffield → East Midlands", "transport", 1.0, ["release"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [{"label": "Tooling set-up", "amount": "4000.00", "currency": "GBP"}, {"label": "First article / conformity inspection", "amount": "3000.00", "currency": "GBP"}],
    slots={"step_id": "machine", "windows": [[5, 13], [16, 30]]})

quote("ev-q-pd", "OFF-PD", "Lowmarsh Trading Ltd", "RS-FN-1001", "D", 1, "29000.00", "GBP", 1, "AS REMOVED", "SITE-LOW-LTN")
trace("ev-tr-pd", "OFF-PD", "Lowmarsh Trading Ltd", "RS-FN-1001", "FN6610", "unknown", "unknown", "not provided", "SITE-LOW-LTN")
offer("OFF-PD", P, "BUY", "Offer D — low-price broker stock, Luton", "RS-FN-1001", "D", "SUP-LOW", "SITE-LOW-LTN", "R-LTN-EMA", "29000.00", "GBP",
      ["ev-q-pd", "ev-tr-pd", "ev-qc-low-ltn", "ev-reg-low", "ev-metrics-site-low-ltn", "ev-ipc-fn-1001-v1", "ev-sb-fn-0042-a"], condition="AS REMOVED", stock=1)
plan("OFF-PD", [
    step("alloc", "Stock allocation", "procurement", 0.5),
    step("ship", "Road transport Luton → East Midlands", "transport", 0.5, ["alloc"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [])

quote("ev-q-pe", "OFF-PE", "Esker Component Exchange Ltd", "RS-FN-1001-C", "C", 1, "38000.00", "GBP", 1, "OVERHAULED", "SITE-ESK-BHX")
form1("ev-f1-pe", "OFF-PE", "Esker Component Exchange Ltd (UK Part 145)", "UK.145.90015 (synthetic)", "RS-FN-1001", "C", "FN5520", "OVERHAULED",
      "Pre-SB configuration", "SITE-ESK-BHX")
trace("ev-tr-pe", "OFF-PE", "Esker Component Exchange Ltd", "RS-FN-1001", "FN5520", "yes", "Synthetic Charter Ltd", "yes", "SITE-ESK-BHX")
offer("OFF-PE", P, "BUY", "Offer E — near-match revision C, Birmingham", "RS-FN-1001", "C", "SUP-ESK", "SITE-ESK-BHX", "R-BHX-EMA", "38000.00", "GBP",
      ["ev-q-pe", "ev-f1-pe", "ev-tr-pe", "ev-qc-esk-bhx", "ev-reg-esk", "ev-metrics-site-esk-bhx", "ev-ipc-fn-1001-v1", "ev-sb-fn-0042-a"], condition="OVERHAULED", stock=1)
plan("OFF-PE", [
    step("alloc", "Stock allocation", "procurement", 0.5),
    step("ship", "Road transport Birmingham → East Midlands", "transport", 0.5, ["alloc"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [])

# --- Secondary A: NGV segment RS-NGV-2040 rev B ---
A = "case-secondary-a"
quote("ev-q-sa1", "OFF-SA1", "Harbourline Aero Components Ltd", "RS-NGV-2040", "B", 1, "31500.00", "GBP", 1, "SERVICEABLE", "SITE-HAR-SOU")
form1("ev-f1-sa1", "OFF-SA1", "Harbourline Aero Components Ltd (UK Part 145)", "UK.145.90016 (synthetic)", "RS-NGV-2040", "B", "NG4410", "INSPECTED/TESTED",
      "Inspected per CMM 72-50-20 rev 8", "SITE-HAR-SOU")
offer("OFF-SA1", A, "BUY", "Offer SA-1 — serviceable segment, Southampton", "RS-NGV-2040", "B", "SUP-HAR", "SITE-HAR-SOU", "R-SOU-EMA", "31500.00", "GBP",
      ["ev-q-sa1", "ev-f1-sa1", "ev-qc-har-sou", "ev-reg-har", "ev-metrics-site-har-sou", "ev-ipc-ngv-2040-v1"], condition="SERVICEABLE", stock=1)
plan("OFF-SA1", [
    step("alloc", "Stock allocation", "procurement", 1.0),
    step("docs", "Release certificate and trace review", "documentation", 0.5),
    step("insp", "Borescope-grade visual and dimensional inspection", "inspection", 2.0, ["alloc"]),
    step("ship", "Road transport Southampton → East Midlands", "transport", 1.0, ["insp", "docs"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [])
# Trace pack for SA-1 is NOT supplied with the offer; it is retrievable through the supplier-reply connector (gap follow-up, AC-08).
FOLLOWUP_SA1 = trace("ev-tr-sa1", "OFF-SA1", "Harbourline Aero Components Ltd", "RS-NGV-2040", "NG4410", "yes", "Synthetic Island Airways Ltd", "yes", "SITE-HAR-SOU")
EVIDENCE.remove(FOLLOWUP_SA1)

quote("ev-q-sa2", "OFF-SA2", "Meridane Turbine Parts GmbH", "RS-NGV-2040", "C", 1, "50575.00", "EUR", 2, "NEW", "SITE-MER-HAM")
form1("ev-f1-sa2", "OFF-SA2", "Representative engine design holder production (UK Part 21G)", "UK.21G.99010 (synthetic)", "RS-NGV-2040", "C", "NG9001", "NEW",
      "New manufacture; release by POA holder", "SITE-MER-HAM")
trace("ev-tr-sa2", "OFF-SA2", "Meridane Turbine Parts GmbH", "RS-NGV-2040", "NG9001", "yes", "new part — no operator history", "yes", "SITE-MER-HAM")
offer("OFF-SA2", A, "BUY", "Offer SA-2 — new segment, Hamburg OEM distributor", "RS-NGV-2040", "C", "SUP-MER", "SITE-MER-HAM", "R-HAM-IMM", "50575.00", "EUR",
      ["ev-q-sa2", "ev-f1-sa2", "ev-tr-sa2", "ev-qc-mer-ham", "ev-reg-mer", "ev-metrics-site-mer-ham", "ev-ipc-ngv-2040-v1"], condition="NEW", stock=3)
plan("OFF-SA2", [
    step("alloc", "Stock allocation", "procurement", 2.0),
    step("export", "Export documentation", "documentation", 2.0, ["alloc"]),
    step("ship", "Short-sea Hamburg → Immingham + road", "transport", 3.0, ["export"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [])

quote("ev-q-sa3", "OFF-SA3", "Coastreach Surplus Ltd", "RS-NGV-2040", "B", 1, "22000.00", "GBP", 1, "AS REMOVED", "SITE-CST-DUB")
offer("OFF-SA3", A, "BUY", "Offer SA-3 — surplus segment, Dublin", "RS-NGV-2040", "B", "SUP-CST", "SITE-CST-DUB", "R-DUB-HLY", "22000.00", "GBP",
      ["ev-q-sa3", "ev-qc-cst-dub", "ev-reg-cst", "ev-metrics-site-cst-dub", "ev-ipc-ngv-2040-v1"], condition="AS REMOVED", stock=1)
plan("OFF-SA3", [
    step("alloc", "Stock allocation", "procurement", 0.5),
    step("ship", "Ferry Dublin → Holyhead + road", "transport", 2.0, ["alloc"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
], [])

# --- Secondary B: bleed duct RS-BD-3110 rev A ---
B = "case-secondary-b"
quote("ev-q-sb1", "OFF-SB1", "Meridane Turbine Parts GmbH", "RS-BD-3110", "A", 1, "12800.00", "GBP", 14, "NEW", "SITE-MER-HAM")
form1("ev-f1-sb1", "OFF-SB1", "Representative engine design holder production (UK Part 21G)", "UK.21G.99010 (synthetic)", "RS-BD-3110", "A", "BD3301", "NEW",
      "New manufacture; release by POA holder on dispatch", "SITE-MER-HAM")
trace("ev-tr-sb1", "OFF-SB1", "Meridane Turbine Parts GmbH", "RS-BD-3110", "BD3301", "yes", "new part — no operator history", "yes", "SITE-MER-HAM")
offer("OFF-SB1", B, "BUY", "Offer SB-1 — new duct, Hamburg (backorder)", "RS-BD-3110", "A", "SUP-MER", "SITE-MER-HAM", "R-HAM-IMM", "12800.00", "GBP",
      ["ev-q-sb1", "ev-f1-sb1", "ev-tr-sb1", "ev-qc-mer-ham", "ev-reg-mer", "ev-metrics-site-mer-ham", "ev-ipc-bd-3110-v1"], condition="NEW", stock=0)
plan("OFF-SB1", [
    step("alloc", "Backorder allocation from OEM", "procurement", 12.0, [], [10.0, 16.0], "OEM backorder estimate"),
    step("export", "OEM release and export documentation", "documentation", 2.0, ["alloc"]),
    step("ship", "Short-sea Hamburg → Immingham + road", "transport", 3.0, ["export"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [])

quote("ev-q-sb2", "OFF-SB2", "Pennine Precision Components Ltd", "RS-BD-3110", "A", 1, "11900.00", "GBP", 14, "NEW", "SITE-PEN-ROT")
doc("ev-dl-sb2", "doc-dl-sb2", "Design data licence — RS-BD-3110 drawing (Pennine)", "design_licence", "design_holder", 90, "Representative engine design holder (synthetic)",
    ["OFF-SB2", "RS-BD-3110", "SUP-PEN"], {
        "DESIGN HOLDER": "Representative engine design holder (synthetic)", "PART NUMBER": "RS-BD-3110", "DRAWING NUMBER": "DWG-BD-3110",
        "DRAWING REVISION": "A", "LICENCE REFERENCE": "DDL-90032 (synthetic)", "LICENSEE": "Pennine Precision Components Ltd",
    }, site_id="SITE-PEN-ROT", revision="A")
offer("OFF-SB2", B, "MAKE", "Offer SB-2 — commissioned manufacture, Rotherham", "RS-BD-3110", "A", "SUP-PEN", "SITE-PEN-ROT", "R-ROT-EMA", "11900.00", "GBP",
      ["ev-q-sb2", "ev-dl-sb2", "ev-poa-pen", "ev-qc-pen-shf", "ev-nadcap-pen-rot", "ev-reg-pen", "ev-metrics-site-pen-rot", "ev-ipc-bd-3110-v1"],
      condition="NEW", manufacturer="SUP-PEN", capacity={"forming_slots": [[2, 30]]},
      route_specific={"design_basis": "Licensed design data DWG-BD-3110 rev A", "special_processes": ["tig_welding", "heat_treatment", "fpi_ndt"],
                      "qualification": "No FAI yet for this part at Rotherham", "tooling": "New forming tool required"})
plan("OFF-SB2", [
    step("tool", "Forming tool manufacture", "manufacture", 4.0),
    step("material", "Sheet material procurement", "procurement", 3.0),
    step("form", "Forming and TIG welding", "manufacture", 4.0, ["tool", "material"]),
    step("fai", "AS9102 first article inspection", "qualification", 3.0, ["form"]),
    step("release", "Production release", "documentation", 1.0, ["fai"]),
    step("ship", "Courier Rotherham → East Midlands", "transport", 1.0, ["release"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [{"label": "Forming tool", "amount": "2600.00", "currency": "GBP"}, {"label": "First article inspection", "amount": "1800.00", "currency": "GBP"}])

quote("ev-q-sb3", "OFF-SB3", "Kestrelmoor Fabrication Ltd", "RS-BD-3110", "A", 1, "13900.00", "GBP", 12, "NEW", "SITE-KES-BRS")
doc("ev-dl-sb3", "doc-dl-sb3", "Design data licence — RS-BD-3110 drawing (Kestrelmoor)", "design_licence", "design_holder", 90, "Representative engine design holder (synthetic)",
    ["OFF-SB3", "RS-BD-3110", "SUP-KES"], {
        "DESIGN HOLDER": "Representative engine design holder (synthetic)", "PART NUMBER": "RS-BD-3110", "DRAWING NUMBER": "DWG-BD-3110",
        "DRAWING REVISION": "A", "LICENCE REFERENCE": "DDL-90033 (synthetic)", "LICENSEE": "Kestrelmoor Fabrication Ltd",
    }, site_id="SITE-KES-BRS", revision="A")
doc("ev-fai-sb3", "doc-fai-sb3", "AS9102 first article inspection report — RS-BD-3110 (Bristol)", "fai_report", "supplier_quality_record", 60,
    "Kestrelmoor Fabrication Ltd", ["OFF-SB3", "RS-BD-3110", "SITE-KES-BRS"], {
        "PART NUMBER": "RS-BD-3110", "REVISION": "A", "DRAWING REVISION": "A", "SITE": "SITE-KES-BRS", "REPORT NUMBER": "FAI-90043", "RESULT": "complete",
    }, site_id="SITE-KES-BRS")
offer("OFF-SB3", B, "MAKE", "Offer SB-3 — commissioned manufacture, Bristol", "RS-BD-3110", "A", "SUP-KES", "SITE-KES-BRS", "R-BRS-EMA", "13900.00", "GBP",
      ["ev-q-sb3", "ev-dl-sb3", "ev-fai-sb3", "ev-poa-kes", "ev-nadcap-kes-brs", "ev-qc-kes-brs", "ev-reg-kes", "ev-metrics-site-kes-brs", "ev-ipc-bd-3110-v1"],
      condition="NEW", manufacturer="SUP-KES", capacity={"forming_slots": [[3, 30]]},
      route_specific={"design_basis": "Licensed design data DWG-BD-3110 rev A", "special_processes": ["tig_welding", "heat_treatment", "fpi_ndt"],
                      "qualification": "AS9102 FAI complete at Bristol", "tooling": "Existing forming tool"})
plan("OFF-SB3", [
    step("licence", "Design data licence confirmation", "documentation", 1.0),
    step("material", "Sheet material procurement", "procurement", 3.0),
    step("form", "Forming and TIG welding", "manufacture", 4.0, ["licence", "material"], None, "Requires forming slot"),
    step("ndt", "Heat treatment and FPI", "manufacture", 2.0, ["form"]),
    step("conf", "Conformity inspection against FAI baseline", "qualification", 1.0, ["ndt"]),
    step("release", "CAA Form 1-21 release by POA holder", "documentation", 0.5, ["conf"]),
    step("ship", "Road transport Bristol → East Midlands", "transport", 0.5, ["release"]),
    step("recv", "Receiving inspection (145.A.42)", "inspection", 0.5, ["ship"]),
    step("ready", "Installation readiness", "installation", 0.5, ["recv"]),
], [{"label": "Conformity inspection", "amount": "1050.00", "currency": "GBP"}], slots={"step_id": "form", "windows": [[3, 30]]})

# ------------------------------------------------------------------------------------------------
# Signals (PRD FR-10) and evidence changes
# ------------------------------------------------------------------------------------------------

SIGNALS = [
    {"fixture_id": "SIG-RTM-CLOSURE", "signal_id": "sig-rtm-closure-v1", "source": "scenario-port-feed", "source_event_id": "PORT-NLRTM-2026-1116-01",
     "version": 1, "category": "port_facility", "title": "Port of Rotterdam ro-ro terminals closed (scenario)",
     "scope": {"geo_ids": ["GEO-PORT-NLRTM"], "entity_ids": [], "site_ids": [], "route_ids": [], "materials": []},
     "assertion": {"type": "port_closure", "severity": 0.8, "transport_delay_days": 7.0, "surcharge": money("2500.00"),
                   "description": "Ro-ro and container terminals closed after industrial action; rerouting via Zeebrugge adds about 7 days (scenario)."},
     "published_at": at(0), "observed_at": at(0), "effective_from": at(0), "expiry_at": at(10),
     "provenance": {"feed": "Scenario signal", "note": "Presenter-injected scripted scenario signal"}, "confidence": 0.9, "status": "active",
     "data_origin": SYN, "label": "Scenario signal"},
    {"fixture_id": "SIG-RTM-CLOSURE-CORRECTION", "signal_id": "sig-rtm-closure-v2", "source": "scenario-port-feed", "source_event_id": "PORT-NLRTM-2026-1116-01",
     "version": 2, "category": "port_facility", "title": "Port of Rotterdam closure revised: partial reopening (scenario)",
     "scope": {"geo_ids": ["GEO-PORT-NLRTM"], "entity_ids": [], "site_ids": [], "route_ids": [], "materials": []},
     "assertion": {"type": "port_closure", "severity": 0.5, "transport_delay_days": 3.0, "surcharge": money("1000.00"),
                   "description": "Partial reopening; backlog adds about 3 days (scenario)."},
     "published_at": at(0), "observed_at": at(0), "effective_from": at(0), "expiry_at": at(6),
     "provenance": {"feed": "Scenario signal", "corrects": "sig-rtm-closure-v1"}, "confidence": 0.9, "status": "corrected", "data_origin": SYN, "label": "Scenario signal"},
    {"fixture_id": "SIG-RTM-CLOSURE-RETRACTION", "signal_id": "sig-rtm-closure-v3", "source": "scenario-port-feed", "source_event_id": "PORT-NLRTM-2026-1116-01",
     "version": 3, "category": "port_facility", "title": "Port of Rotterdam closure retracted (scenario)",
     "scope": {"geo_ids": ["GEO-PORT-NLRTM"], "entity_ids": [], "site_ids": [], "route_ids": [], "materials": []},
     "assertion": {"type": "port_closure", "severity": 0.0, "transport_delay_days": 0.0, "surcharge": money("0.00"), "description": "Earlier closure report retracted."},
     "published_at": at(0), "observed_at": at(0), "effective_from": at(0), "expiry_at": None,
     "provenance": {"feed": "Scenario signal", "retracts": "sig-rtm-closure-v1"}, "confidence": 0.95, "status": "retracted", "data_origin": SYN, "label": "Scenario signal"},
    {"fixture_id": "SIG-KHH-TYPHOON", "signal_id": "sig-khh-typhoon-v1", "source": "scenario-weather-feed", "source_event_id": "WX-TWKHH-2026-1116",
     "version": 1, "category": "climate", "title": "Typhoon suspends operations at Port of Kaohsiung (scenario, unrelated)",
     "scope": {"geo_ids": ["GEO-PORT-TWKHH"], "entity_ids": [], "site_ids": [], "route_ids": [], "materials": []},
     "assertion": {"type": "port_closure", "severity": 0.7, "transport_delay_days": 4.0, "surcharge": money("0.00"), "description": "Unrelated to any active case route."},
     "published_at": at(0), "observed_at": at(0), "effective_from": at(0), "expiry_at": at(4),
     "provenance": {"feed": "Scenario signal"}, "confidence": 0.8, "status": "active", "data_origin": SYN, "label": "Scenario signal"},
    {"fixture_id": "SIG-HAM-STRIKE", "signal_id": "sig-ham-strike-v1", "source": "scenario-port-feed", "source_event_id": "PORT-DEHAM-2026-1118-01",
     "version": 1, "category": "logistics", "title": "Announced 48-hour dock strike at Port of Hamburg from day 2 (scenario)",
     "scope": {"geo_ids": ["GEO-PORT-DEHAM"], "entity_ids": [], "site_ids": [], "route_ids": [], "materials": []},
     "assertion": {"type": "port_strike", "severity": 0.6, "transport_delay_days": 2.0, "surcharge": money("300.00"), "description": "Future-effective strike; shared Meridane site affects two cases."},
     "published_at": at(0, 2), "observed_at": at(0, 2), "effective_from": at(2), "expiry_at": at(4),
     "provenance": {"feed": "Scenario signal"}, "confidence": 0.85, "status": "active", "data_origin": SYN, "label": "Scenario signal"},
    {"fixture_id": "SIG-TARIFF-EU-AERO", "signal_id": "sig-tariff-eu-aero-v1", "source": "scenario-trade-feed", "source_event_id": "TARIFF-GB-EU-AERO-2026-11",
     "version": 1, "category": "geopolitical_tariff", "title": "Proposed customs inspection uplift for EU-origin aero parts (scenario, low severity)",
     "scope": {"geo_ids": [], "entity_ids": [], "site_ids": [], "route_ids": [], "materials": [], "origin_countries": ["NL", "DE"]},
     "assertion": {"type": "customs_inspection", "severity": 0.2, "transport_delay_days": 0.5, "surcharge": money("0.00"), "description": "Adds half a day of customs handling for EU-origin consignments."},
     "published_at": at(0, 3), "observed_at": at(0, 3), "effective_from": at(30), "expiry_at": None,
     "provenance": {"feed": "Scenario signal"}, "confidence": 0.6, "status": "active", "data_origin": SYN, "label": "Scenario signal"},
]

SB_FN_B = doc("ev-sb-fn-0042-b", "doc-sb-fn-0042", "Service bulletin RS-SB-73-0042 Rev B — fuel nozzle tip", "service_bulletin",
              "design_holder", 100, "Representative engine design holder (synthetic)", ["RS-FN-1001"], {
                  "SB NUMBER": "RS-SB-73-0042", "REVISION": "B", "APPLICABLE PART NUMBER": "RS-FN-1001",
                  "MIN DRAWING REVISION": "F", "EFFECTIVE DATE": "2026-11-16",
                  "INSTRUCTION": "Newly manufactured nozzles shall conform to drawing revision F; revision E drawings withdrawn for new manufacture.",
              }, revision="B", effective=at(0), supersedes="ev-sb-fn-0042-a", include=False)

EVIDENCE_CHANGES = [
    {"fixture_id": "EVC-SB-0042-REVB", "title": "Design holder issues SB RS-SB-73-0042 Rev B (scenario evidence change)",
     "new_evidence": SB_FN_B, "supersedes_version_id": "ev-sb-fn-0042-a",
     "relationships": [{"from_id": "ev-sb-fn-0042-b", "from_type": "evidence", "to_id": "RS-FN-1001", "to_type": "part", "relation_type": "applies_to"}],
     "note": "MAKE builds to drawing rev E no longer meet the minimum drawing revision; affects Offer C and every primary interchangeability check."},
]

SUPPLIER_REPLIES = [
    {"reply_id": "reply-sa1-trace", "candidate_id": "OFF-SA1", "requirement_id": "REQ-NGV-TRC-01", "attempt": 1, "evidence": FOLLOWUP_SA1,
     "message": "Harbourline: back-to-birth trace pack attached for S/N NG4410 (synthetic supplier reply)."},
    {"reply_id": "reply-sa3-none-1", "candidate_id": "OFF-SA3", "requirement_id": "REQ-NGV-TRC-01", "attempt": 1, "evidence": None,
     "message": "Coastreach: trace records being located, no date yet (synthetic supplier reply)."},
    {"reply_id": "reply-sa3-none-2", "candidate_id": "OFF-SA3", "requirement_id": "REQ-NGV-TRC-01", "attempt": 2, "evidence": None,
     "message": "Coastreach: no response received within the follow-up window (synthetic)."},
    {"reply_id": "reply-pd-none-1", "candidate_id": "OFF-PD", "requirement_id": "REQ-FN-REL-01", "attempt": 1, "evidence": None,
     "message": "Lowmarsh: unit sold 'as removed' without release certificate (synthetic supplier reply)."},
    {"reply_id": "reply-pd-none-2", "candidate_id": "OFF-PD", "requirement_id": "REQ-FN-REL-01", "attempt": 2, "evidence": None,
     "message": "Lowmarsh: no certificate available (synthetic)."},
]

# ------------------------------------------------------------------------------------------------
# Relationship rows (FR-11): explicit dependency edges used by impact propagation.
# ------------------------------------------------------------------------------------------------

RELS: list[dict] = []


def rel(f, ft, t, tt, rt, ev=None):
    RELS.append({"relationship_id": f"rel-{len(RELS) + 1:04d}", "from_id": f, "from_type": ft, "to_id": t, "to_type": tt, "relation_type": rt,
                 "evidence_ids": ev or [], "effective_from": "2026-01-01T00:00:00Z", "effective_to": None, "recorded_at": RETRIEVED,
                 "revision": 1, "data_origin": SYN})


rel("engine-demo-001", "engine", "RS-TF2-CFG-A", "engine_configuration", "has_configuration")
for comp, p in PARTS.items():
    rel("RS-TF2-CFG-A", "engine_configuration", comp, "component", "contains")
    rel(comp, "component", p["set"], "requirement_set", "governed_by")
    rel(comp, "component", p["part"], "part", "installed_part")
    rel(comp, "component", CASE_OF[comp], "case", "tracked_by")
for o in OFFERS:
    rel(o["candidate_id"], "offer", o["case_id"], "case", "candidate_for")
    rel(o["candidate_id"], "offer", o["part_id"].split("-C")[0] if o["part_id"].endswith("-C") else o["part_id"], "part", "offers_part")
    rel(o["candidate_id"], "offer", o["site_id"], "site", "supplied_from")
    rel(o["candidate_id"], "offer", o["supplier_id"], "supplier", "sold_by")
    rel(o["candidate_id"], "offer", o["logistics_route_id"], "route", "ships_via")
    for e in o["evidence_ids"]:
        rel(e, "evidence", o["candidate_id"], "offer", "supports")
for s in SITES:
    rel(s[0], "site", s[1], "supplier", "operated_by")
    rel(s[0], "site", s[5], "geo", "located_in")
    rel(s[0], "site", f"GEO-COUNTRY-{s[4]}", "geo", "located_in")
for r in ROUTES:
    rel(r[0], "route", r[1], "site", "departs_from")
    for g in r[7]:
        rel(r[0], "route", g, "geo", "passes_through")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    suppliers = [{"supplier_id": s, "legal_entity_name": n, "registry": {"jurisdiction": c, "company_number": None, "check": "synthetic entity — not looked up"},
                  "roles": r, "data_origin": SYN} for s, n, c, r in SUPPLIERS]
    sites = [{"site_id": s, "supplier_id": sup, "name": n, "address": a,
              "geography": {"country": c, "geo_id": g, "lat": lat, "lon": lon}, "roles": roles, "capabilities": caps,
              "qualified_scope_refs": [], "metric_refs": [f"metric-otd-{s.lower()}", f"metric-ppm-{s.lower()}"], "data_origin": SYN}
             for s, sup, n, a, c, g, lat, lon, roles, caps in SITES]
    routes = [{"route_id": r, "from_site_id": f, "mode": m, "label": label, "base_transport_days": d, "freight": money(fr),
               "baseline_exposure": ex, "passes_through": geos, "destination": "Operator MRO base, East Midlands (synthetic)", "data_origin": SYN}
              for r, f, m, label, d, fr, ex, geos in ROUTES]
    geos = [{"geo_id": g, "name": n, "kind": k, "lat": lat, "lon": lon} for g, (n, k, lat, lon) in GEOS.items()]
    metrics = []
    for sup, site, num, den, ppm in METRICS:
        metrics.append({"metric_id": f"metric-otd-{site.lower()}", "subject_id": sup, "site_id": site, "metric_name": "on_time_delivery_rate",
                        "label": "On-time delivery (share of deliveries within the promised date)", "value": round(num / den, 4), "unit": "ratio",
                        "numerator": num, "denominator": den, "window": "12 months to 2026-10-31", "source_evidence_id": f"ev-metrics-{site.lower()}",
                        "data_origin": SYN, "fixture_note": "Favourable scenario fixture value — not measured real-world performance"})
        metrics.append({"metric_id": f"metric-ppm-{site.lower()}", "subject_id": sup, "site_id": site, "metric_name": "quality_escapes_ppm",
                        "label": "Quality escapes (defective parts per million delivered)", "value": ppm, "unit": "ppm", "numerator": None,
                        "denominator": None, "window": "12 months to 2026-10-31", "source_evidence_id": f"ev-metrics-{site.lower()}",
                        "data_origin": SYN, "fixture_note": "Scenario fixture value — not measured real-world performance"})
    fx = {"fx_version": "fx-2026-11-14-scenario", "base": "GBP", "rates": {"EUR": "0.8700", "USD": "0.7900", "GBP": "1.0000"},
          "source": "Scenario fixture FX table (not a market quote)", "as_of": "2026-11-14"}
    files = {
        "suppliers.json": suppliers, "sites.json": sites, "routes.json": routes, "geos.json": geos, "metrics.json": metrics,
        "offers.json": OFFERS, "plans.json": PLANS, "evidence.json": EVIDENCE, "signals.json": SIGNALS,
        "evidence_changes.json": EVIDENCE_CHANGES, "supplier_replies.json": SUPPLIER_REPLIES, "relationships.json": RELS, "fx.json": fx,
        "scenario.json": {"fixture_version": "seed-v1", "scenario_clock_start": iso(START), "seed": 20261116,
                          "operator": {"name": "Demo operator MRO (synthetic)", "role": "UK Part 145 maintenance organisation with CAMO support",
                                       "approval_reference": "UK.145.90000 (synthetic)", "base": "East Midlands"},
                          "primary_signal_fixture_id": "SIG-RTM-CLOSURE", "data_origin": SYN},
    }
    for name, data in files.items():
        (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    print(f"wrote {len(files)} files to {OUT} — {len(OFFERS)} offers, {len(EVIDENCE)} evidence versions, {len(RELS)} relationships")


if __name__ == "__main__":
    main()
