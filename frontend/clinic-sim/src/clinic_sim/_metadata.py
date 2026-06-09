from pathlib import Path

app_name = "clinic-sim"
app_entrypoint = "clinic_sim.backend.app:app"
app_slug = "clinic_sim"
api_prefix = "/api"
dist_dir = Path(__file__).parent / "__dist__"