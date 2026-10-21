class InvalidTemperatureInput(ValueError):
    """Input falls outside the station observation range."""


class StationNotFound(ValueError):
    """Requested station does not exist."""


class FetchUnavailable(Exception):
    """Upstream capacity or time budget is unavailable to this request."""
