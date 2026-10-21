from app.application.prefecture.ports.inbound.list_prefecture import ListPrefecturePort
from app.application.station.ports.inbound.list_station import ListStationPort


def get_prefecture_port() -> ListPrefecturePort:
    """Composition Root must register a provider before serving requests."""
    raise RuntimeError("ListPrefecturePort provider is not registered")


def get_station_port() -> ListStationPort:
    """Composition Root must register a provider before serving requests."""
    raise RuntimeError("ListStationPort provider is not registered")
