from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a cached service-role Supabase client.

    Uses the service role key, which bypasses RLS. Call this only from
    backend pipeline code that writes to pipeline-owned tables
    (transcripts, argument_maps, feedback_reports, drills).
    Never expose this client or its key to the frontend.
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
