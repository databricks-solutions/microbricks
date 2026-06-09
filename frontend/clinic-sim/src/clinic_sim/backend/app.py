from .core import create_app
from .router import router
from .routers.simulator import router as sim_router

# `router` is the apx singleton api_router (prefix `/api`); attaching the sim
# sub-router to it gives us `/api/sim/...`.
router.include_router(sim_router)

app = create_app(routers=[router])
