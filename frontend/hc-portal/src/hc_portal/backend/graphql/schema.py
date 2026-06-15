"""Root Strawberry schema for the BFF GraphQL gateway."""
import strawberry

from .queries import Query

schema = strawberry.Schema(query=Query)
