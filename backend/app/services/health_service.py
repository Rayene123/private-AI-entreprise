from app.core.config import Settings, get_settings
from app.integrations.supabase.client import SupabaseClientFactory


class HealthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def check_dependencies(self) -> dict[str, str]:
        SupabaseClientFactory(self._settings).check_connectivity()
        return {"supabase": "ok"}


def get_health_service() -> HealthService:
    return HealthService(get_settings())
