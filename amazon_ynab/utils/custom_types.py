from typing import TypedDict, TypeVar


class AmazonInnerTransactionsDict(TypedDict):
    payments: dict[str, float]
    is_tip: bool


AmazonTransactionsDict = dict[str, AmazonInnerTransactionsDict]
