# GTFS validation report

This document records an earlier project milestone. See the [current verification and status](docs/FINAL_TEST_REPORT.md) for the latest evidence.

This archive records the pre-update state. See the [current testing report](docs/TESTING_REPORT.md).

The imported source was `delhi_buses_static_gtfs_v1.zip` (SHA-256
`8eb05d9c21e7a6b42d7b49de45cb095b70ddee5b8f7716859330c9784c322f05`).
The full machine-readable report is `backend/data/ingestion_report.json`.

| GTFS table | Imported | Rejected | Duplicates |
| --- | ---: | ---: | ---: |
| agency.txt | 2 | 0 | 0 |
| stops.txt | 6,862 | 0 | 0 |
| routes.txt | 2,574 | 0 | 0 |
| calendar.txt | 1 | 0 | 0 |
| calendar_dates.txt | absent | 0 | 0 |
| trips.txt | 80,357 | 0 | 0 |
| stop_times.txt | 2,737,136 | 0 | 0 |
| shapes.txt | 965,607 | 0 | 0 |

Both `feed_info.txt` records validated. The consistency pass found zero
out-of-order stop times and zero trips referencing missing shapes. The report
records optional blank values, including absent direction IDs on all trips.
Missing optional `calendar_dates.txt` is handled as absent, not an error.

The importer validates columns, types, coordinates, GTFS times including
`24:00+`, foreign keys, stop sequence, duplicates and feed metadata. It builds
a temporary SQLite database and replaces the target only after validation.
The repeated-import and failed-import preservation cases are tested with a
small synthetic fixture. That fixture is separate from the Delhi feed.

The generated SQLite database was about 330 MB and is excluded from the
download ZIP. The original GTFS ZIP is also excluded to keep the download
small. Obtain the same source feed and run
`python -m scripts.import_gtfs /path/to/delhi_buses_static_gtfs_v1.zip`
from `backend/` to reproduce it. The source hash above identifies the feed
used for these results.
