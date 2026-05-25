from fastapi import APIRouter

from app.services.supabase_client import get_supabase

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "roundlab-api"}


@router.get("/health/supabase")
async def supabase_health_check() -> dict[str, str]:
    try:
        get_supabase().table("profiles").select("id").limit(1).execute()
        return {"status": "ok", "database": "reachable"}
    except Exception:
        return {"status": "error", "database": "unreachable"}
