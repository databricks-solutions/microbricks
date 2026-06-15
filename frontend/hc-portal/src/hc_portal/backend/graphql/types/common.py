import strawberry


@strawberry.type
class PageInfo:
    total: int
    limit: int
    offset: int
