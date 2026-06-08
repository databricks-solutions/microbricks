from __future__ import annotations

from typing import TypeAlias
from ._defaults import ConfigDependency, ClientDependency, UserWorkspaceClientDependency
from ._headers import HeadersDependency


class Dependencies:
    """FastAPI dependency injection shorthand for route handler parameters."""

    Client: TypeAlias = ClientDependency
    """Databricks WorkspaceClient using app-level service principal credentials."""

    UserClient: TypeAlias = UserWorkspaceClientDependency
    """WorkspaceClient authenticated on behalf of the current user via OBO token."""

    Config: TypeAlias = ConfigDependency
    """Application configuration loaded from environment variables."""

    Headers: TypeAlias = HeadersDependency
    """Databricks Apps HTTP headers for the current request."""
