import argparse
import json
from pathlib import Path

from app.services.gtfs_service import import_gtfs


parser = argparse.ArgumentParser(description="Validate and import static GTFS")
parser.add_argument("zip_path", type=Path)
parser.add_argument("--database", type=Path, default=Path("data/safarnama.db"))
parser.add_argument("--report", type=Path, default=Path("data/ingestion_report.json"))
args = parser.parse_args()
report = import_gtfs(args.zip_path, args.database, args.report)
print(json.dumps({name: {key: value for key, value in stats.items() if key in ("total", "imported", "rejected", "duplicates")} for name, stats in report["tables"].items()}, indent=2))
