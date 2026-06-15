import strawberry


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Placeholder — provider creation TBD.")
    async def noop(self) -> bool:
        return True
