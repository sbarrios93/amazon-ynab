from typing import TypedDict


class InnerTransactionsDict(TypedDict):
    payments: dict[str, float]
    is_tip: bool
