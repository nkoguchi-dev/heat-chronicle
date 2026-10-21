class InvalidTemperatureInput(ValueError):
    """Input falls outside the station observation range."""


class StationNotFound(ValueError):
    """Requested station does not exist."""
