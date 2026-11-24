
"""Audit matching coverage and prepare manual precision review.

Coverage is not matching accuracy.
Manual review labels must be supplied by a reviewer.
"""

from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "processed"
GTFS = BASE / "data" / "raw" / "gtfs"
OUT = BASE / "outputs"

OUT.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
SAMPLE_PER_STRATUM = 15


def save_json(name, content):
    (OUT / name).write_text(
        json.dumps(
            content,
            indent=2,
            allow_nan=False
        ),
        encoding="utf-8"
    )


def percentage(count, total):
    return round(
        100 * count / total, 4
    ) if total else None


def present(series):
    return (
        series.notna()
        & series.astype("string").str.strip()
        .ne("").fillna(False)
    )


def audit_coverage(df, version):

    total = len(df)

    start = present(df["start_stop_id"])
    end = present(df["end_stop_id"])

    both = start & end
    valid = df["valid_order"].eq(True).fillna(False)

    if (valid & ~both).any():
        raise ValueError(
            f"{version}: ordered journey has missing stop"
        )

    categories = {
        "both_stops_matched": int(both.sum()),
        "boarding_only_matched": int(
            (start & ~end).sum()
        ),
        "destination_only_matched": int(
            (~start & end).sum()
        ),
        "neither_stop_matched": int(
            (~start & ~end).sum()
        )
    }

    if sum(categories.values()) != total:
        raise ValueError(
            "Coverage accounting failed"
        )

    result = {
        "matching_version": version,
        "total_cleaned_ticket_records": total,
        "boarding_matched": int(start.sum()),
        "destination_matched": int(end.sum()),
        "boarding_coverage_pct": percentage(
            int(start.sum()), total
        ),
        "destination_coverage_pct": percentage(
            int(end.sum()), total
        ),
        "both_stop_coverage_pct": percentage(
            int(both.sum()), total
        ),
        "records_with_unmatched_stops": int(
            (~both).sum()
        ),
        "both_matched_but_invalid_order": int(
            (both & ~valid).sum()
        ),
        "gtfs_ordered_journeys": int(valid.sum()),
        "gtfs_ordered_coverage_pct": percentage(
            int(valid.sum()), total
        ),
        "categories": categories,
        "geographic_accuracy_verified": False
    }

    return result


def build_endpoint_table(df):

    frames = []

    for side, label in [
        ("start", "boarding"),
        ("end", "destination")
    ]:

        part = df[
            [
                "route",
                f"{side}_stop_name",
                f"{side}_stop_id",
                f"{side}_method"
            ]
        ].copy()

        part.columns = [
            "route",
            "etm_stop_name",
            "gtfs_stop_id",
            "matching_method"
        ]

        part["endpoint_type"] = label

        part["matched"] = present(
            part["gtfs_stop_id"]
        )

        part["matching_method"] = (
            part["matching_method"]
            .astype("string")
            .fillna("unknown")
        )

        frames.append(part)

    return pd.concat(
        frames,
        ignore_index=True
    )


def main():

    print("Loading V2 and V3 matching datasets...")

    v2 = pd.read_parquet(
        DATA / "validated_ticket_stops.parquet"
    )

    v3 = pd.read_parquet(
        DATA / "validated_ticket_stops_v3.parquet"
    )

    if len(v2) != len(v3):
        raise ValueError(
            "V2 and V3 record counts differ"
        )

    coverage = [
        audit_coverage(v2, "V2"),
        audit_coverage(v3, "V3")
    ]

    save_json(
        "matching_coverage_audit.json",
        {
            "denominator": "cleaned_ETM_ticket_records",
            "results": coverage,
            "coverage_is_not_accuracy": True
        }
    )

    print("\nCOVERAGE AUDIT")

    for result in coverage:
        print(json.dumps(result, indent=2))

    print("\nBuilding endpoint audit table...")

    endpoints = build_endpoint_table(v3)

    methods = (
        endpoints.groupby(
            [
                "endpoint_type",
                "matching_method",
                "matched"
            ],
            dropna=False
        )
        .size()
        .reset_index(name="endpoint_occurrences")
    )

    methods.to_csv(
        OUT / "matching_method_statistics.csv",
        index=False
    )

    print("\nMATCHING METHOD STATISTICS")
    print(methods.to_string(index=False))

    unmatched = endpoints[
        ~endpoints["matched"]
    ]

    unmatched_summary = (
        unmatched.groupby(
            [
                "route",
                "etm_stop_name",
                "endpoint_type"
            ],
            dropna=False
        )
        .size()
        .reset_index(name="occurrences")
        .sort_values(
            "occurrences",
            ascending=False
        )
    )

    unmatched_summary.to_csv(
        OUT / "unmatched_endpoints_audit_v3.csv",
        index=False
    )

    print("\nTOP 20 UNMATCHED ENDPOINTS")

    print(
        unmatched_summary.head(20)
        .to_string(index=False)
    )

    matched = endpoints[
        endpoints["matched"]
    ].copy()

    mapping_keys = [
        "route",
        "etm_stop_name",
        "gtfs_stop_id",
        "matching_method"
    ]

    # Sample unique mappings rather than repeatedly
    # reviewing identical ticket endpoint records.

    unique_mappings = (
        matched.groupby(
            mapping_keys,
            dropna=False
        )
        .size()
        .reset_index(name="endpoint_occurrences")
    )

    stops = pd.read_csv(
        GTFS / "stops.txt",
        dtype=str,
        usecols=[
            "stop_id",
            "stop_name",
            "stop_lat",
            "stop_lon"
        ]
    )

    if stops["stop_id"].duplicated().any():
        raise ValueError("Duplicate GTFS stop IDs")

    unique_mappings["gtfs_stop_id"] = (
        unique_mappings["gtfs_stop_id"].astype(str)
    )

    unique_mappings = unique_mappings.merge(
        stops,
        left_on="gtfs_stop_id",
        right_on="stop_id",
        how="left",
        validate="many_to_one",
        indicator=True
    )

    if not unique_mappings["_merge"].eq("both").all():
        raise ValueError(
            "Matched GTFS stop reference missing"
        )

    unique_mappings = unique_mappings.drop(
        columns=["stop_id", "_merge"]
    )

    samples = []
    strata = []

    for method, group in unique_mappings.groupby(
        "matching_method",
        sort=True
    ):

        group = group.sort_values(
            mapping_keys
        ).reset_index(drop=True)

        n = min(
            SAMPLE_PER_STRATUM,
            len(group)
        )

        sample = group.sample(
            n=n,
            random_state=RANDOM_SEED
        ).copy()

        sample["stratum_population"] = len(group)
        sample["stratum_sample_size"] = n

        samples.append(sample)

        strata.append({
            "matching_method": str(method),
            "population_unique_mappings": int(
                len(group)
            ),
            "sample_size": int(n)
        })

    if not samples:
        raise ValueError("No matched mappings")

    review = pd.concat(
        samples,
        ignore_index=True
    )

    review.insert(
        0,
        "review_id",
        [
            f"MR-{i:04d}"
            for i in range(1, len(review) + 1)
        ]
    )

    review["review_label"] = ""
    review["evidence_type"] = ""
    review["evidence_reference"] = ""
    review["review_notes"] = ""
    review["reviewer"] = ""

    template = OUT / "manual_matching_review_template.csv"

    review.to_csv(
        template,
        index=False,
        encoding="utf-8-sig"
    )

    metadata = {
        "matching_version": "V3",
        "random_seed": RANDOM_SEED,
        "sampling_unit": "unique_route_stop_mapping",
        "sampling_design": "stratified_by_matching_method",
        "sample_size": int(len(review)),
        "strata": strata,
        "manual_review_completed": False,
        "matching_precision": None,
        "geographic_accuracy": None
    }

    save_json(
        "manual_matching_sample_metadata.json",
        metadata
    )

    print("\nMANUAL REVIEW SAMPLE")
    print("=" * 60)

    print("Unique matched mappings:",
          len(unique_mappings))

    print("Review sample size:", len(review))

    print(
        review.groupby("matching_method")
        .size().to_string()
    )

    print("\nCoverage accounting: PASSED")
    print("GTFS reference integrity: PASSED")
    print("Manual review: PENDING")
    print("Matching precision: NOT YET MEASURED")

    print("\nSaved:", template)


if __name__ == "__main__":
    main()
