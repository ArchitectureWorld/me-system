class GraphCoreError(Exception):
    """Base error for ME-System."""


class ContractValidationError(GraphCoreError, ValueError):
    """Raised when a ME-System contract is invalid."""


class DuplicateGraphObjectError(GraphCoreError):
    """Raised when a canonical node or edge ID already exists."""


class GraphObjectNotFoundError(GraphCoreError, KeyError):
    """Raised when a requested graph object does not exist."""


class GraphNamespaceError(GraphCoreError, ValueError):
    """Raised when a node or edge crosses graph namespaces illegally."""


class CandidateReviewError(GraphCoreError, ValueError):
    """Raised when an in-memory candidate change cannot be reviewed or applied."""


class GraphStoreConfigurationError(GraphCoreError, ValueError):
    """Raised when persistent graph storage configuration is invalid."""


class GraphStoreUnavailableError(GraphCoreError):
    """Raised when persistent graph storage cannot complete an operation."""


class GraphMigrationError(GraphCoreError):
    """Raised when a graph database migration cannot be applied."""


class HermesConfigurationError(GraphCoreError, ValueError):
    """Raised when the Hermes read-only MCP configuration is invalid."""


class ProjectAccessError(GraphCoreError, PermissionError):
    """Raised when an object is outside the configured Hermes project scope."""


class SourceConflictError(GraphCoreError):
    """Raised when an idempotent source retry contains different immutable content."""


class SourceNotFoundError(GraphCoreError, KeyError):
    """Raised when a source record does not exist."""


class EvidenceConflictError(GraphCoreError):
    """Raised when an evidence fragment conflicts with an existing identity or ordinal."""


class IngestionStateError(GraphCoreError, ValueError):
    """Raised when an ingestion run cannot make the requested state transition."""


class CandidateConflictError(GraphCoreError):
    """Raised when an idempotent candidate retry contains a different payload."""


class CandidateNotFoundError(GraphCoreError, KeyError):
    """Raised when a persistent candidate does not exist."""


class CandidateStateError(GraphCoreError, ValueError):
    """Raised when a persistent candidate is no longer in the required state."""


class ReviewTransactionError(GraphCoreError):
    """Raised when candidate review and canonical graph persistence cannot commit atomically."""
