"""Exercise the package guards in an isolated temporary copy; never alter the deliverable."""
from pathlib import Path
import tempfile, shutil, subprocess, json, hashlib

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="resource-package-check-") as temporary:
    test = Path(temporary)
    shutil.copytree(root / "tools", test / "tools", ignore=shutil.ignore_patterns("node_modules"))
    (test / "tools/node_modules").symlink_to(root / "tools/node_modules", target_is_directory=True)
    shutil.copytree(root / "input-package", test / "input-package")
    shutil.copytree(root / "verification", test / "verification")
    manifest_path = test / "input-package/manifest.json"
    original = json.loads(manifest_path.read_text())
    # Re-export the frozen build. Same-version file guards prove bytes did not drift.
    result = subprocess.run(["node", "tools/export-package.ts"], cwd=test, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    after = json.loads(manifest_path.read_text())
    assert original["files"] == after["files"]
    # A modified geometry source under the old version must fail before touching the model.
    adapter = test / "tools/vendor/prepared-turbofan.ts"
    adapter.write_text(adapter.read_text() + "\n// deliberate guard test\n")
    result = subprocess.run(["node", "tools/export-package.ts"], cwd=test, capture_output=True, text=True)
    assert result.returncode != 0 and "increment packageVersion" in result.stderr, result.stderr
    # An internally rehashed but contradictory CSV must fail semantic consistency too.
    csv_path = test / "input-package/components.csv"
    csv_path.write_text(csv_path.read_text().replace("RS-DEMO-FB-001", "WRONG-DEMO-PART"))
    for entry in after["files"]:
        if entry["path"] == "components.csv":
            entry["sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(after))
    result = subprocess.run(["node", "tools/validate-package.mjs"], cwd=test, capture_output=True, text=True)
    assert result.returncode != 0 and "CSV/manifest inconsistency" in result.stderr, result.stderr

report = {"status": "pass", "checks": ["Frozen build re-export keeps exact file hashes", "Changed geometry under same version rejected", "Rehashed contradictory component CSV rejected"], "isolation": "Temporary copy removed; deliverable unchanged"}
(root / "verification/regression-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
