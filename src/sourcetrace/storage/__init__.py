"""Persistence and search adapters."""

from sourcetrace.storage.interfaces import (
    CaseRepository,
    ClaimRepository,
    CorePersistence,
    DocumentRepository,
)
from sourcetrace.storage.memory import (
    InMemoryCaseRepository,
    InMemoryClaimRepository,
    InMemoryDocumentRepository,
    create_in_memory_persistence,
)
from sourcetrace.storage.filesystem import FileBackedCaseRepository

__all__ = [
    "CaseRepository",
    "ClaimRepository",
    "CorePersistence",
    "DocumentRepository",
    "FileBackedCaseRepository",
    "InMemoryCaseRepository",
    "InMemoryClaimRepository",
    "InMemoryDocumentRepository",
    "create_in_memory_persistence",
]
