from pathlib import Path

app_name = "hc-portal"
app_entrypoint = "hc_portal.backend.app:app"
app_slug = "hc_portal"
api_prefix = "/api"
dist_dir = Path(__file__).parent / "__dist__"