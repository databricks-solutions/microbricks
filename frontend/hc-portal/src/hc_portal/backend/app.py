from strawberry.fastapi import GraphQLRouter

from .core import create_app
from .graphql import schema
from .graphql.context import get_bff_context as get_context
from .router import router

# GraphQL gateway — accessible at /api/graphql (inherits router's /api prefix).
graphql_app = GraphQLRouter(schema, context_getter=get_context)
router.include_router(graphql_app, prefix="/graphql")

app = create_app(routers=[router])
