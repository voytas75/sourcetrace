"""Persistence and search adapters."""

from sourcetrace.storage.interfaces import (
    CaseRepository,
    ClaimRepository,
    CorePersistence,
    DocumentRepository,
    ResearchJobRepository,
    ResearchPersistence,
    ResearchProgressEventStore,
    ResearchResultRepository,
)
from sourcetrace.storage.memory import (
    InMemoryCaseRepository,
    InMemoryClaimRepository,
    InMemoryDocumentRepository,
    create_in_memory_persistence,
)
from sourcetrace.storage.filesystem import ContinuityPackPersistenceStatus, FileBackedCaseRepository
from sourcetrace.storage.research_filesystem import (
    FileBackedResearchJobRepository,
    FileBackedResearchProgressEventStore,
    FileBackedResearchResultRepository,
    create_file_backed_research_persistence,
    recover_interrupted_research_jobs,
)

__all__ = [
    "CaseRepository",
    "ClaimRepository",
    "CorePersistence",
    "DocumentRepository",
    "ResearchJobRepository",
    "ResearchPersistence",
    "ResearchProgressEventStore",
    "ResearchResultRepository",
    "ContinuityPackPersistenceStatus",
    "FileBackedCaseRepository",
    "FileBackedResearchJobRepository",
    "FileBackedResearchProgressEventStore",
    "FileBackedResearchResultRepository",
    "InMemoryCaseRepository",
    "InMemoryClaimRepository",
    "InMemoryDocumentRepository",
    "InMemoryResearchJobRepository",
    "InMemoryResearchProgressEventStore",
    "InMemoryResearchResultRepository",
    "create_file_backed_research_persistence",
    "recover_interrupted_research_jobs",
    "create_in_memory_persistence",
    "create_in_memory_research_persistence",
]

from sourcetrace.storage.research import (
    InMemoryResearchJobRepository,
    InMemoryResearchProgressEventStore,
    InMemoryResearchResultRepository,
    create_in_memory_research_persistence,
)
