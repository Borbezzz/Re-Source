"""Sync the exported demo package, backend fixture, and extra map sites. No live suppliers."""
from pathlib import Path
import copy
import json
import hashlib
import shutil
import zipfile

root = Path(__file__).resolve().parents[2]
package = root / "blueprint input/input-package"
manifest = json.loads((package / "manifest.json").read_text())
profile_path = root / "data/demo-products/turbofan.json"
profile = json.loads(profile_path.read_text())
old_ids = {"rs-tf-fan-blade", "rs-tf-fuel-injector", "rs-tf-core-nozzle"}
original_offers = [o for o in profile["sample_offers"] if o["part_id"] in old_ids and int(o["candidate_id"].rsplit("-", 1)[1]) < 13]
template = copy.deepcopy(profile["parts"][0])
parts, offers, sites = [], original_offers, {}
document_lines = ["SYNTHETIC DEMO REQUIREMENTS — prepared Mechanica package " + manifest["packageVersion"] + ". All identities, supplier names and offers are fictional. Not engineering approval."]

# Approximate city centres are map anchors for fictional supplying sites.
locations = [
    (1, "Northline Aero Components", "Derby", "United Kingdom", "GB", 52.9225, -1.4746, "Stockist warehouse", 2, 1, 4, 1.0, "Airfoil stock and rapid dispatch"),
    (2, "Garonne Precision Engineering", "Toulouse", "France", "FR", 43.6045, 1.444, "Production & dispatch", 5, 3, 2, .94, "Precision component manufacturing"),
    (3, "Hanseatic Aviation Supply", "Hamburg", "Germany", "DE", 53.5511, 9.9937, "Distribution centre", 3, 3, 3, 1.08, "European inventory and traceability records"),
    (4, "Clyde Turbine Services", "Glasgow", "United Kingdom", "GB", 55.8642, -4.2518, "Machining site", 8, 1, None, .87, "Small-batch machining; stock awaiting confirmation"),
    (5, "Nordic Rotor Engineering", "Kongsberg", "Norway", "NO", 59.6689, 9.6502, "Production site", 7, 4, 2, 1.15, "Rotor component production"),
    (13, "St Lawrence Turbine Supply", "Montréal", "Canada", "CA", 45.5019, -73.5674, "Aerospace stockist", 4, 5, 6, .91, "North American inventory; export paperwork pending"),
    (14, "Straits Aero Components", "Singapore", "Singapore", "SG", 1.3521, 103.8198, "Regional distribution hub", 5, 6, 5, .84, "Asia-Pacific inventory and consolidated freight"),
    (15, "Vistula Precision Metals", "Rzeszów", "Poland", "PL", 50.0412, 21.9991, "Precision manufacturing site", 6, 4, 2, .89, "Short-run machining; applicability evidence requested"),
]

for c in manifest["components"]:
    pid = c["componentId"].lower()
    part = copy.deepcopy(template)
    part.update(part_id=pid, name=c["name"], part_number=c["partNumber"], node_names=c["nodeIds"], quantity=1, explode=[0, 1.4, 0])
    for req in part["requirements"]:
        if req["key"] == "part_number": req["value"] = c["partNumber"]
        if req["key"] == "revision": req["value"] = c["revision"]
        quote = f"{c['name']}: {req['label']} = {req['value']}"
        req["source"] = {"document_id": "turbofan-requirements", "quote": quote}
        document_lines.append(quote)
    part["identity_source"] = part["part_number_source"] = part["requirements"][0]["source"]
    parts.append(part)
    base_price = {"fan": 6850, "compressor": 1800, "turbine": 3400, "combustor": 1250, "nozzle": 18700, "casing": 14500, "shaft": 9200}[c["parentAssemblyId"]]
    for number, name, city, country, code, lat, lon, activity, lead, transit, stock, multiplier, capability in locations:
        if pid in old_ids and number < 13: continue
        candidate_id = f"{pid}-site-{number:02}"
        offers.append(dict(candidate_id=candidate_id, part_id=pid, supplier_name=name + " (sample)", route="buy", country=country,
                           price=round(base_price * multiplier / 10) * 10, currency="GBP", lead_time_days=lead,
                           summary=f"Fictional {city} supplier. {capability}. Price, availability and evidence are demonstration data, not a real quotation.", evidence=[]))
        sites[candidate_id] = dict(city=city, countryCode=code, lat=lat, lon=lon, siteType=activity, stock=stock, transitDays=transit,
                                   applicability="missing" if number == 15 else "provided", traceability="missing" if number == 13 else "provided",
                                   siteEvidence="missing" if number == 4 else "provided", sourceLabel="Prepared supplier dossier (demo)")

profile.update(description="Prepared Mechanica turbofan with 35 demo sourcing families across seven sections and individual compressor/turbine stages.", parts=parts, sample_offers=offers)
profile["documents"][0]["text"] = "\n".join(document_lines)
profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n")
(root / "frontend/src/studio/data/extra-sites.json").write_text(json.dumps(sites, indent=2, ensure_ascii=False) + "\n")
archive = root / "blueprint input/mechanica-input-package.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(package.iterdir()):
        if path.is_file():
            info = zipfile.ZipInfo(path.name, date_time=(2026, 11, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
shutil.copy2(archive, root / "frontend/public/packages/mechanica-input-package.zip")
shutil.copy2(package / "assembly.glb", root / "frontend/public/models/mechanica-turbofan.glb")
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for entry in manifest["files"]:
        assert hashlib.sha256(z.read(entry["path"])).hexdigest() == entry["sha256"]
    report = dict(status="pass", packageVersion=manifest["packageVersion"], uploadArchive=archive.name,
                  uploadSha256=hashlib.sha256(archive.read_bytes()).hexdigest(), rootMembers=z.namelist(),
                  crc="pass", fileHashes="match manifest", publicCopy="identical", sourceFamilies=len(parts))
(root / "blueprint input/verification/archive-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(dict(parts=len(parts), offers=len(offers), extra_sites=len(sites), packageVersion=manifest["packageVersion"])))
