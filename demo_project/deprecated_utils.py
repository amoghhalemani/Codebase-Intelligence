"""Deprecated utility functions left over from an old migration."""

def format_as_legacy_xml(data: dict) -> str:
    """[DEAD CODE] Old XML serializer replaced by JSON. 0 callers in project."""
    items = "".join(f"<{k}>{v}</{k}>" for k, v in data.items())
    return f"<root>{items}</root>"


def ping_obsolete_monitoring_server(server_ip: str = "10.0.0.99") -> bool:
    """[DEAD CODE] Pings decommissioned monitoring agent. 0 callers in project."""
    return False
