class GraphCoreError(Exception):
    """Base error for ME-System graph core."""


class ContractValidationError(GraphCoreError, ValueError):
    """Raised when a graph contract is invalid."""


class DuplicateGraphObjectError(GraphCoreError):
    """Raised when a canonical node or edge ID already exists."""


class GraphObjectNotFoundError(GraphCoreError, KeyError):
    """Raised when a requested graph object does not exist."""


class GraphNamespaceError(GraphCoreError, ValueError):
    """Raised when a node or edge crosses graph namespaces illegally."""


class CandidateReviewError(GraphCoreError, ValueError):
    """Raised when a candidate change cannot be reviewed or applied."""


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
