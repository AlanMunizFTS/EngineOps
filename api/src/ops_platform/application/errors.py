class ApplicationError(Exception):
    """Base error translated to an HTTP response only at the API boundary."""


class NotFoundError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class ValidationError(ApplicationError):
    pass
