from pathlib import Path

app_name = "microbricks-deck"
app_entrypoint = "microbricks_deck.backend.app:app"
app_slug = "microbricks_deck"
api_prefix = "/api"
dist_dir = Path(__file__).parent / "__dist__"