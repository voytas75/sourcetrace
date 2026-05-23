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
from sourcetrace.storage.filesystem import ContinuityPackPersistenceStatus, FileBackedCaseRepository

__all__ = [
    "CaseRepository",
    "ClaimRepository",
    "CorePersistence",
    "DocumentRepository",
    "ContinuityPackPersistenceStatus",
    "FileBackedCaseRepository",
    "InMemoryCaseRepository",
    "InMemoryClaimRepository",
    "InMemoryDocumentRepository",
    "create_in_memory_persistence",
]
