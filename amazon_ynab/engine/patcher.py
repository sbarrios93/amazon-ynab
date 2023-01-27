from typing import Any

from amazon_ynab.amazon.amazon_client import AmazonClient
from amazon_ynab.utils.custom_types import MatchedTransactionsList
from amazon_ynab.ynab.ynab_client import YNABClient


def patcher(
    amazon_client: AmazonClient,
    ynab_client: YNABClient,
    matched_transactions: MatchedTransactionsList,
    payee_id: str,
    payee_name: str,
) -> None:

    transactions: list[dict[str, Any]] = []

    for amazon_transaction_id, ynab_transaction_id in matched_transactions:
        invoice = amazon_client.invoices[amazon_transaction_id]
        items = invoice.item_list

        items_string = " ".join(items)

        transactions_element = {
            "id": ynab_transaction_id,
            # memo has a max limit of 200 characters
            "memo": items_string[:190] + " | AMAZON",
            "payee_id": payee_id,
            "payee_name": payee_name,
        }

        transactions.append(transactions_element)

    if transactions:
        ynab_client.bulk_patch_transactions(transactions)


def tips_patcher(ynab_client: YNABClient, payee_id: str, payee_name: str) -> None:
    transactions: list[dict[str, Any]] = []

    for transaction_id, _ in ynab_client.tip_transactions.items():
        transactions_element = {
            "id": transaction_id,
            # memo has a max limit of 200 characters
            "memo": "Amazon Tip | AMAZON",
            "payee_id": payee_id,
            "payee_name": payee_name,
        }

        transactions.append(transactions_element)

        if transactions:
            ynab_client.bulk_patch_transactions(transactions)
