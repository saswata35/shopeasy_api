class ApiError(Exception):
    """Application-level HTTP error with a status code and message."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message