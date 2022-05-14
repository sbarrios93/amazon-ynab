from typing import TypedDict

import datetime

from amazon_ynab.amazon.invoice_parser import TransactionInvoice


class AmazonInnerTransactionsDict(TypedDict):
    payments: dict[str, float]
    is_tip: bool


AmazonTransactionsDict = dict[str, AmazonInnerTransactionsDict]

AmazonInvoicesDict = dict[str, TransactionInvoice]


class YNABInnerTransactionsDict(TypedDict):
    amount: int
    date: datetime.date
    payee: str
    memo: str | None


YNABTransactionsDict = dict[str, YNABInnerTransactionsDict]

MatchedTransactionsList = list[tuple[str, str]]
