from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class IndexStatus(str, Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass
class FileRecord:
    path: str
    hash: str
    language: str
    indexing_status: IndexStatus = IndexStatus.PENDING


@dataclass
class Symbol:
    id: str
    name: str
    qualified_name: str
    kind: str
    file: str
    module: str
    start_line: int
    end_line: int
    signature: Optional[str] = None


@dataclass
class Import:
    module: str
    file: str
    imported_path: str
    local_name: str
    alias: Optional[str]
    level: int
    line: int


@dataclass
class Reference:
    source_symbol_id: str
    target_name: str
    target_symbol_id: Optional[str]
    reference_type: str
    resolution_status: ResolutionStatus
    file: str
    line: int
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyEdge:
    source_id: str
    target_id: str
    relationship: str
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class ParsedFile:
    path: str
    module_id: str
    language: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[Import] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    class_hierarchy: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class TestCase:
    test_id: str
    file: str
    name: str
    associated_symbols: list[str] = field(default_factory=list)
    coverage_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeSet:
    repository_path: str
    revision: Optional[str]
    changed_files: list[str]
    changed_symbols: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AnalysisFinding:
    rule: str
    location: str
    explanation: str
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    limitations: list[str] = field(default_factory=list)
