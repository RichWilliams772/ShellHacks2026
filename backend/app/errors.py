"""Expected backend errors."""


class GridSyncError(Exception):
    """Base error for loader, pairing, and lookup failures."""


class LoaderError(GridSyncError):
    """A CSV or JSON project file could not be normalized."""


class SameUtilityError(GridSyncError):
    """The caller asked to compare a utility with itself."""


class UnknownUtilityError(GridSyncError):
    """One or both requested utilities are not in the loaded dataset."""


class ProjectNotFoundError(GridSyncError):
    """No loaded project has the requested id."""


class OpportunityNotFoundError(GridSyncError):
    """No cross-utility pair matches the requested opportunity id."""


class ScenarioRejected(GridSyncError):
    """A what-if shift cannot be applied to the selected project."""
