from app.application.prefecture.ports.inbound.list_prefecture import ListPrefecturePort


def get_prefecture_port() -> ListPrefecturePort:
    """Composition Root must register a provider before serving requests."""
    raise RuntimeError("ListPrefecturePort provider is not registered")
