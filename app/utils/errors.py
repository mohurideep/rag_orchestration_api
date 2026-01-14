class AppError(Exception):
    """Base class for application-specific errors."""
    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
    

class ValidationError(AppError):
    pass

class UpstreamError(AppError):
    pass

class NotFoundError(AppError):
    pass
