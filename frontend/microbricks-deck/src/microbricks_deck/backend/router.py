from .core import create_router
from .models import VersionOut

router = create_router()


@router.get("/healthz", operation_id="healthz")
async def healthz():
    return {"ok": True}


@router.get("/version", response_model=VersionOut, operation_id="version")
async def version():
    return VersionOut.from_metadata()
