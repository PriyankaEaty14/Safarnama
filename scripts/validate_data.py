"""Check the static archive and the demand manifest served by SAFARNAMA."""

import argparse
from hashlib import file_digest, sha256
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"agency.txt", "routes.txt", "trips.txt", "stops.txt", "stop_times.txt"}


def validate_static(archive_path: Path) -> dict:
    with archive_path.open("rb") as stream:
        digest = file_digest(stream, "sha256").hexdigest()
    with ZipFile(archive_path) as archive:
        members = [Path(entry.filename).name for entry in archive.infolist() if not entry.is_dir()]
        if REQUIRED.difference(members) or any(members.count(name) != 1 for name in REQUIRED):
            raise ValueError("Required GTFS files are missing or ambiguous")
        if not {"calendar.txt", "calendar_dates.txt"}.intersection(members):
            raise ValueError("No GTFS service calendar found")
        if archive.testzip() is not None:
            raise ValueError("GTFS ZIP failed its member checksum")
    expected = json.loads((ROOT / "backend/data/ingestion_report.json").read_text())
    return {"archive": archive_path.name, "sha256": digest, "members": len(members),
            "matches_recorded_import": digest == expected["sha256"]}


def read_api(origin: str, endpoint: str) -> dict:
    with urlopen(origin.rstrip("/") + endpoint, timeout=15) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gtfs", type=Path)
    parser.add_argument("--origin", help="Optional running SAFARNAMA server")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "ml/outputs")
    args = parser.parse_args()
    result = {"gtfs": validate_static(args.gtfs)}
    manifest = json.loads((args.artifacts / "safarnama_prediction_manifest.json").read_text())
    artifact = (args.artifacts / manifest["dataset"]).resolve()
    if artifact.parent != args.artifacts.resolve():
        raise ValueError("Prediction export must remain in the artifact directory")
    data = artifact.read_bytes()
    checksum = sha256(data).hexdigest()
    alternate = b"\r" not in data and sha256(data.replace(b"\n", b"\r\n")).hexdigest() == manifest["sha256"]
    if checksum != manifest["sha256"] and not alternate:
        raise ValueError("Prediction manifest checksum differs from the export")
    result["artifact"] = {"file": artifact.name, "sha256": checksum,
                          "manifest_matches_after_crlf_conversion": checksum != manifest["sha256"] and alternate}
    if args.origin:
        result["readiness"] = read_api(args.origin, "/ready")
        coverage = read_api(args.origin, "/api/v1/demand/coverage?limit=1")
        if coverage["artifact_sha256"] != checksum or coverage["export_rows"] != manifest["prediction_rows"]:
            raise ValueError("Backend coverage differs from the supplied prediction export")
        coverage.pop("routes")
        result["coverage"] = coverage
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
