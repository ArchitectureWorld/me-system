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
