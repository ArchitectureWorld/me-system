class GraphCoreError(Exception):
    """Base error for the single ME-Core runtime."""


class ContractValidationError(GraphCoreError, ValueError):
    """Raised when a ME-Core contract is invalid."""


class DuplicateGraphObjectError(GraphCoreError):
    """Raised when a canonical node or edge ID already exists."""


class GraphObjectNotFoundError(GraphCoreError, KeyError):
    """Raised when a requested graph object does not exist."""


class GraphNamespaceError(GraphCoreError, ValueError):
    """Raised when a node or edge crosses graph namespaces illegally."""


class CandidateReviewError(GraphCoreError, ValueError):
    """Raised when a candidate change cannot be reviewed or applied."""


class GraphStoreConfigurationError(GraphCoreError, ValueError):
    """Raised when persistent ME-Core storage configuration is invalid."""


class GraphStoreUnavailableError(GraphCoreError):
    """Raised when persistent ME-Core storage cannot complete an operation."""


class GraphMigrationError(GraphCoreError):
    """Raised when a ME-Core database migration cannot be applied."""


class HermesConfigurationError(GraphCoreError, ValueError):
    """Raised when the Hermes read-only MCP configuration is invalid."""


class ProjectAccessError(GraphCoreError, PermissionError):
    """Raised when an object is outside the configured Hermes project scope."""


class SourceConflictError(GraphCoreError, ValueError):
    """Raised when a source replay conflicts with immutable source identity."""


class SourceNotFoundError(GraphCoreError, KeyError):
    """Raised when a source ledger record does not exist."""


class EvidenceConflictError(GraphCoreError, ValueError):
    """Raised when evidence fragments conflict by ID, source, or ordinal."""


class IngestionRunError(GraphCoreError, ValueError):
    """Raised when an ingestion run transition is invalid."""


class IngestionRunNotFoundError(GraphCoreError, KeyError):
    """Raised when an ingestion run does not exist."""
