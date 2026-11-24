
"""Record manual name-consistency review findings.

This is not independent geographic validation.
"""

from pathlib import Path
import json
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"

df = pd.read_csv(
    OUT / "manual_matching_review_template.csv",
    dtype={"gtfs_stop_id": str}
)

# Manually identified substantive name conflicts.
conflicts = {
    "MR-0032": (
        "WEST PATEL NAGAR",
        "East Patel Nagar",
        "Directional qualifier conflict: West versus East."
    ),
    "MR-0033": (
        "WEST PATEL NAGAR",
        "East Patel Nagar",
        "Directional qualifier conflict: West versus East."
    ),
    "MR-0043": (
        "K BLOCK JAHANGIR PURI",
        "C Block Jahangir Puri",
        "Block identifier conflict: K versus C."
    )
}

expected_ids = {
    f"MR-{i:04d}" for i in range(1, 46)
}

assert len(df) == 45
assert set(df["review_id"]) == expected_ids
assert df["review_id"].is_unique

expected_methods = {
    "component_exact": 15,
    "exact": 15,
    "fuzzy": 15
}

assert df.groupby(
    "matching_method"
).size().to_dict() == expected_methods

# Preserve geographic uncertainty separately.
df["review_label"] = "uncertain"
df["geographic_review_label"] = "unverified"
df["name_review_label"] = "consistent"
df["evidence_type"] = "name_comparison_only"

df["evidence_reference"] = (
    "ETM stop name and supplied GTFS stop name"
)

df["reviewer"] = "AI-assisted manual-style name review"
df["review_notes"] = ""

for index, row in df.iterrows():

    review_id = row["review_id"]
    method = row["matching_method"]

    if review_id in conflicts:

        expected_etm, expected_gtfs, reason = (
            conflicts[review_id]
        )

        assert row["etm_stop_name"] == expected_etm
        assert row["stop_name"] == expected_gtfs

        df.at[index, "name_review_label"] = "conflict"
        df.at[index, "review_notes"] = reason

    elif method == "exact":

        assert (
            row["etm_stop_name"].strip().casefold()
            == row["stop_name"].strip().casefold()
        )

        df.at[index, "review_notes"] = (
            "Exact name agreement; physical stop "
            "identity and direction remain unverified."
        )

    elif method == "component_exact":

        components = [
            name.strip().casefold()
            for name in row["stop_name"].split("/")
        ]

        assert (
            row["etm_stop_name"].strip().casefold()
            in components
        )

        df.at[index, "review_notes"] = (
            "ETM name appears as a literal GTFS "
            "name component; geography unverified."
        )

    elif method == "fuzzy":

        df.at[index, "review_notes"] = (
            "Plausible spelling, spacing, punctuation "
            "or abbreviation variation; geography unverified."
        )

    else:
        raise ValueError(
            f"Unexpected matching method: {method}"
        )

df.to_csv(
    OUT / "manual_matching_review_completed.csv",
    index=False,
    encoding="utf-8-sig"
)

method_results = []

for method, group in df.groupby(
    "matching_method",
    sort=True
):

    consistent = int(
        group["name_review_label"]
        .eq("consistent").sum()
    )

    conflict = int(
        group["name_review_label"]
        .eq("conflict").sum()
    )

    method_results.append({
        "matching_method": str(method),
        "reviewed": int(len(group)),
        "name_consistent": consistent,
        "name_conflicts": conflict,
        "name_consistency_pct": round(
            100 * consistent / len(group), 4
        ),
        "geographic_precision": None
    })

flagged = df[
    df["name_review_label"].eq("conflict")
].copy()

flagged.to_csv(
    OUT / "suspected_stop_mapping_errors.csv",
    index=False
)

consistent_count = int(
    df["name_review_label"]
    .eq("consistent").sum()
)

conflict_count = len(flagged)

report = {
    "schema_version": "1.0",
    "matching_version": "V3",
    "sampling_unit": "unique_route_stop_mapping",
    "sampling_design": "stratified_by_matching_method",
    "random_seed": 42,
    "review_type": "AI-assisted manual name comparison",
    "name_review_completed": True,
    "total_samples_reviewed": int(len(df)),
    "name_consistent": consistent_count,
    "name_conflicts": int(conflict_count),
    "sample_name_consistency_pct": round(
        100 * consistent_count / len(df), 4
    ),
    "suspected_conflict_endpoint_occurrences": int(
        flagged["endpoint_occurrences"].sum()
    ),
    "geographically_verified_correct": 0,
    "geographically_verified_incorrect": 0,
    "geographically_unverified": int(len(df)),
    "geographic_matching_precision": None,
    "population_matching_accuracy": None,
    "independent_geographic_validation_completed": False,
    "method_results": method_results,
    "limitations": [
        "Name consistency does not establish physical stop identity.",
        "GTFS coordinates are not independent ETM ground truth.",
        "The sample is stratified and not self-weighting.",
        "The overall sample rate is not population accuracy.",
        "Flagged mappings are suspected errors, not independently verified errors.",
        "Endpoint occurrences are not necessarily distinct tickets."
    ],
    "recommended_actions": [
        "Investigate flagged mappings before assigning replacement stop IDs.",
        "Protect East, West, North and South qualifiers.",
        "Protect block, sector and phase identifiers.",
        "Reject uncertain mappings rather than force a match.",
        "Obtain independent ETM stop reference information."
    ]
}

(OUT / "manual_matching_review_summary.json").write_text(
    json.dumps(
        report,
        indent=2,
        allow_nan=False
    ),
    encoding="utf-8"
)

print("\nMANUAL MATCHING REVIEW")
print("=" * 60)

print(
    pd.DataFrame(method_results)
    .to_string(index=False)
)

print("\nTotal samples reviewed:", len(df))
print("Name-consistent:", consistent_count)
print("Name conflicts:", conflict_count)

print(
    "Sample name consistency:",
    report["sample_name_consistency_pct"],
    "%"
)

print(
    "Flagged endpoint occurrences:",
    report["suspected_conflict_endpoint_occurrences"]
)

print("Geographic precision: NOT ESTABLISHED")
print("Population accuracy: NOT ESTABLISHED")

print("\nSaved completed review and audit reports.")
