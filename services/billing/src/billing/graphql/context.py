"""GraphQL request context — extracts OBO auth from headers the same way REST does."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from psycopg_pool import AsyncConnectionPool

from ..auth import branch_name, user_email, user_token
from ..db import get_pool


@dataclass
class GraphQLContext:
    user_token: str
    user_email: str
    branch: str | None
    request: Request

    async def pool(self) -> AsyncConnectionPool:
        return await get_pool(self.user_email, self.user_token, self.branch)


async def get_context(request: Request) -> GraphQLContext:
    token = await user_token(
        x_forwarded_access_token=request.headers.get("X-Forwarded-Access-Token"),
        authorization=request.headers.get("Authorization"),
    )
    email = await user_email(
        x_forwarded_email=request.headers.get("X-Forwarded-Email"),
    )
    branch = await branch_name(
        branch_name=request.query_params.get("branch_name"),
    )
    return GraphQLContext(
        user_token=token,
        user_email=email,
        branch=branch,
        request=request,
    )
