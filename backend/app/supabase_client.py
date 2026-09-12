from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase_admin_client() -> Client:
    """Server-side Supabase client using the service role key.

    Kept behind this factory (rather than imported directly) so tests and
    later phases can substitute a fake implementing the same interface.
    """
    settings = get_settings()
    return create_client(str(settings.supabase_url), settings.supabase_service_role_key)
