"""Root Strawberry schema for the patient service."""
import strawberry

from .mutations import Mutation
from .queries import Query

schema = strawberry.Schema(query=Query, mutation=Mutation)
