"""Alembic env.py wired for OBO + Lakebase.

Migrations are run by a *human* against a feature-branch endpoint locally, or by
a CI workflow against the dev/test/prod project. In both cases:

  - PGHOST / PGUSER / PGPORT / PGDATABASE / PGSSLMODE come from the env.
  - ENDPOINT_NAME points at the Lakebase endpoint to migrate.
  - The Postgres password is a short-lived OAuth credential generated via
    `WorkspaceClient(token=...).postgres.generate_database_credential(...)`.

Locally, the developer's CLI auth (set LOCAL_DEV_TOKEN_FROM_CLI=true and
LOCAL_DEV_TOKEN to a `databricks auth token` value) provides the user identity.
In CI, the workflow injects the SP/OIDC token the same way.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from databricks.sdk import WorkspaceClient
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # we hand-author migrations; no SQLAlchemy models in scope


def _build_url() -> str:
    host = os.environ["PGHOST"]
    user = os.environ["PGUSER"]
    port = os.environ.get("PGPORT", "5432")
    dbname = os.environ.get("PGDATABASE", "databricks_postgres")
    sslmode = os.environ.get("PGSSLMODE", "require")

    if context.is_offline_mode():
        # Offline mode (`alembic upgrade head --sql`) emits SQL without connecting.
        # Use a stub password so URL parsing succeeds.
        password = "<offline>"
    else:
        token = os.environ.get("LOCAL_DEV_TOKEN") or os.environ.get("DATABRICKS_TOKEN")
        if not token:
            raise RuntimeError(
                "No user token available for migrations. Set LOCAL_DEV_TOKEN "
                "(from `databricks auth token -p hc-dev | jq -r .access_token`) "
                "or DATABRICKS_TOKEN before running alembic."
            )
        ws_host = os.environ.get("DATABRICKS_HOST")
        if not ws_host:
            raise RuntimeError(
                "DATABRICKS_HOST must be set so the SDK can mint a Lakebase credential."
            )
        endpoint = os.environ["ENDPOINT_NAME"]
        cred = WorkspaceClient(host=ws_host, token=token, auth_type="pat").postgres.generate_database_credential(
            endpoint=endpoint
        )
        password = cred.token

    return (
        f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
        f"?sslmode={sslmode}"
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_build_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _build_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
