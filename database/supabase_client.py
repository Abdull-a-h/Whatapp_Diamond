from supabase import create_client, Client
from functools import lru_cache
from app.config import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get Supabase client instance (cached).
    
    Returns:
        Client: Supabase client instance
    """
    settings = get_settings()
    supabase: Client = create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key
    )
    return supabase


@lru_cache()
def get_supabase_admin_client() -> Client:
    """
    Get Supabase admin client with service role key (cached).
    
    Returns:
        Client: Supabase admin client instance
    """
    settings = get_settings()
    supabase: Client = create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_key
    )
    return supabase

