from datetime import timedelta

from amazon_ynab.utils.custom_types import (
    AmazonInvoicesDict,
    MatchedTransactionsList,
    YNABTransactionsDict,
)


def match_transactions(
    amazon_transactions: AmazonInvoicesDict,
    ynab_transactions: YNABTransactionsDict,
    ynab_amount_multiplier: int = 1_000,
    timedelta_lower_bound: int = 0,
    timedelta_upper_bound: int = 5,
) -> MatchedTransactionsList:
    """
    Matches the transactions between amazon and ynab.
    """

    transaction_candidates_for_amount = []
    transaction_candidates_for_date = []

    for amazon_transaction_id, amazon_invoice in amazon_transactions.items():
        for ynab_transaction_id, ynab_transaction_details in ynab_transactions.items():
            if amazon_invoice.total_amount_paid is not None:
                # check matching values
                if float(
                    ynab_transaction_details["amount"] / ynab_amount_multiplier
                ) == float(amazon_invoice.total_amount_paid):
                    transaction_candidates_for_amount.append(
                        (amazon_transaction_id, ynab_transaction_id)
                    )

                # check matching dates
                if (
                    ynab_transaction_details["date"] is not None
                    and amazon_invoice.payment_date is not None
                    and (
                        timedelta(timedelta_lower_bound)
                        <= (
                            ynab_transaction_details["date"]
                            - amazon_invoice.payment_date
                        )
                        <= timedelta(timedelta_upper_bound)
                    )
                ):
                    transaction_candidates_for_date.append(
                        (amazon_transaction_id, ynab_transaction_id)
                    )
    matches = [
        (amazon, ynab)
        for (amazon, ynab) in transaction_candidates_for_amount
        if (amazon, ynab) in transaction_candidates_for_date
    ]

    return matches
