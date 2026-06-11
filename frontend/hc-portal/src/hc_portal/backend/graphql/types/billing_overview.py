import strawberry

from .billing import InvoiceGQL


@strawberry.type
class BillingOverviewGQL:
    invoices: list[InvoiceGQL]
    total: int
    limit: int
    offset: int
    total_outstanding_cents: int
    overdue_count: int
    due_soon_count: int
    partial: bool
