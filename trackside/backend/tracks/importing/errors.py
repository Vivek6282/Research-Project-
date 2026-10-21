"""Trackside — Errors raised while importing a track file."""


class TrackImportError(Exception):
    """A problem with the uploaded file that the user can fix; the message is shown to them."""

    def __init__(self, message: str, status_code: int = 400):
        """Keep the user-facing message and the HTTP status to answer with."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code
