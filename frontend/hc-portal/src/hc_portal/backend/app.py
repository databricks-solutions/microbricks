from .core import create_app
from .router import router
from .routers.aggregations import router as bff_router

# `router` is the apx singleton api_router (prefix `/api`); attaching the bff
# sub-router to it gives us `/api/bff/...` per the hc-bff-pattern skill.
router.include_router(bff_router)

app = create_app(routers=[router])
