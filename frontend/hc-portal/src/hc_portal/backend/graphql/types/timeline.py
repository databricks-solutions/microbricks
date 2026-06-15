from datetime import datetime
from typing import Optional

import strawberry


@strawberry.type
class TimelineEventGQL:
    timestamp: datetime
    event_type: str
    title: str
    detail: Optional[str]
    status: Optional[str]
