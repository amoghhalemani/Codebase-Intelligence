"""Old legacy reporting utilities that are no longer used anywhere."""

def generate_legacy_audit_csv(start_date: str, end_date: str) -> str:
    """Deprecated: Generates ancient CSV audit report. 0 callers in project."""
    return f"Audit,{start_date},{end_date},LEGACY"


def purge_old_temporary_records(days_older_than: int) -> int:
    """Orphan utility: Cleans up temporary table. 0 callers in project."""
    return 0
