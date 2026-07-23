class MESystemError(Exception):
    """Base error for ME-System."""


# Compatibility name for the existing graph/query implementation. New code should
# inherit from MESystemError directly; this alias avoids a breaking API rename.
GraphCoreError = MESystemError


class ContractValidationError(MESystemError, ValueError):
    """Raised when a ME-System domain contract is invalid."""


class DuplicateGraphObjectError(MESystemError):
    """Raised when a canonical node or edge ID already exists."""


class GraphObjectNotFoundError(MESystemError, KeyError):
    """Raised when a requested graph object does not exist."""


class GraphNamespaceError(MESystemError, ValueError):
    """Raised when a node or edge crosses graph namespaces illegally."""


class CandidateReviewError(MESystemError, ValueError):
    """Raised when a candidate change cannot be reviewed or applied."""


class GraphStoreConfigurationError(MESystemError, ValueError):
    """Raised when persistent graph storage configuration is invalid."""


class GraphStoreUnavailableError(MESystemError):
    """Raised when persistent graph storage cannot complete an operation."""


class GraphMigrationError(MESystemError):
    """Raised when a graph database migration cannot be applied."""


class HermesConfigurationError(MESystemError, ValueError):
    """Raised when the Hermes read-only MCP configuration is invalid."""


class ProjectAccessError(MESystemError, PermissionError):
    """Raised when an object is outside the configured Hermes project scope."""


class SourceConflictError(MESystemError, ValueError):
    """Raised when an idempotent source key refers to different content."""


class SourceNotFoundError(MESystemError, KeyError):
    """Raised when a registered source cannot be found."""


class EvidenceConflictError(MESystemError, ValueError):
    """Raised when an evidence fragment identity conflicts with stored content."""


class IngestionStateError(MESystemError, ValueError):
    """Raised when an ingestion run performs an illegal state transition."""


class CandidateConflictError(MESystemError, ValueError):
    """Raised when a candidate idempotency key refers to different content."""


class CandidateNotFoundError(MESystemError, KeyError):
    """Raised when a durable candidate cannot be found."""


class CandidateStateError(MESystemError, ValueError):
    """Raised when a durable candidate is not in the required review state."""


class ReviewTransactionError(MESystemError):
    """Raised when an atomic candidate review cannot be completed."""
