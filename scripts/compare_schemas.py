#!/usr/bin/env python3
"""
Compare two schema JSON files and report differences.

Usage:
    python compare_schemas.py alembic_schema.json guardiandb_schema.json
"""
import json
import sys
from typing import Dict, List

def compare_schemas(schema1: dict, schema2: dict) -> Dict[str, List[str]]:
    """Compare two schemas and return differences."""
    differences = {
        'missing_in_alembic': [],
        'missing_in_guardiandb': [],
        'column_mismatches': [],
        'index_mismatches': [],
    }

    all_tables = set(schema1.keys()) | set(schema2.keys())

    for table in all_tables:
        if table not in schema1:
            differences['missing_in_alembic'].append(table)
            continue
        if table not in schema2:
            differences['missing_in_guardiandb'].append(table)
            continue

        # Compare columns
        cols1 = set(schema1[table]['columns'].keys())
        cols2 = set(schema2[table]['columns'].keys())

        if cols1 != cols2:
            missing_in_s1 = cols2 - cols1
            missing_in_s2 = cols1 - cols2
            if missing_in_s1:
                differences['column_mismatches'].append(
                    f"{table}: Alembic missing columns {missing_in_s1}"
                )
            if missing_in_s2:
                differences['column_mismatches'].append(
                    f"{table}: GuardianDB missing columns {missing_in_s2}"
                )

        # Compare column types for common columns
        common_cols = cols1 & cols2
        for col in common_cols:
            type1 = schema1[table]['columns'][col]['type']
            type2 = schema2[table]['columns'][col]['type']
            # Normalize type comparisons (VARCHAR vs TEXT, INTEGER vs BIGINT, etc.)
            if not types_compatible(type1, type2):
                differences['column_mismatches'].append(
                    f"{table}.{col}: type mismatch (Alembic: {type1}, GuardianDB: {type2})"
                )

    return differences

def types_compatible(type1: str, type2: str) -> bool:
    """Check if two SQL types are compatible."""
    # Normalize type strings
    type1 = type1.upper().replace('VARYING', '').strip()
    type2 = type2.upper().replace('VARYING', '').strip()

    # Common equivalences
    equivalences = [
        {'TEXT', 'VARCHAR', 'CHAR'},
        {'INTEGER', 'BIGINT', 'INT'},
        {'TIMESTAMP', 'DATETIME'},
        {'JSON', 'JSONB'},
    ]

    for equiv_set in equivalences:
        t1_base = any(t in type1 for t in equiv_set)
        t2_base = any(t in type2 for t in equiv_set)
        if t1_base and t2_base:
            return True

    return type1 == type2

def generate_report(differences: Dict[str, List[str]]) -> str:
    """Generate a markdown report of schema differences."""
    report = ["# Schema Drift Report\n"]

    if not any(differences.values()):
        report.append("✅ No schema drift detected. Alembic and GuardianDB schemas match.\n")
        return "\n".join(report)

    report.append("⚠️ **Schema drift detected between Alembic and GuardianDB**\n")

    if differences['missing_in_alembic']:
        report.append("\n## Tables Missing in Alembic (exist in GuardianDB only)\n")
        for table in differences['missing_in_alembic']:
            report.append(f"- `{table}`")

    if differences['missing_in_guardiandb']:
        report.append("\n## Tables Missing in GuardianDB (exist in Alembic only)\n")
        for table in differences['missing_in_guardiandb']:
            report.append(f"- `{table}`")

    if differences['column_mismatches']:
        report.append("\n## Column Mismatches\n")
        for mismatch in differences['column_mismatches']:
            report.append(f"- {mismatch}")

    report.append("\n---")
    report.append("\n**Action Required**: Update models.py or GuardianDB to resolve drift.")

    return "\n".join(report)

def main():
    if len(sys.argv) < 3:
        print("Usage: compare_schemas.py <alembic_schema.json> <guardiandb_schema.json>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        schema1 = json.load(f)

    with open(sys.argv[2]) as f:
        schema2 = json.load(f)

    differences = compare_schemas(schema1, schema2)
    report = generate_report(differences)

    print(report)

    # Write report to file
    with open('schema_drift_report.md', 'w') as f:
        f.write(report)

    # Exit with error code if drift detected
    if any(differences.values()):
        sys.exit(1)

if __name__ == '__main__':
    main()
