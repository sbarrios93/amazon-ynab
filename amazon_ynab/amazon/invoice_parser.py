"""
Heavily borrowed from
https://github.com/davidz627/AmazonSyncForYNAB/
"""


from typing import Union

import re
from datetime import date, datetime

import bs4
from bs4 import BeautifulSoup as bs

from amazon_ynab.utils.utils import not_none
from amazon_ynab.words.string_modifier import shorten_string

# from amazon_ynab.amazon.product_summarizer import shorten_string


class TransactionInvoice:
    def __init__(
        self,
        invoice_number: str,
        transaction_page: str,
        force_amount: float | None,
        short_items: bool,
        words_per_item: int,
    ):
        self.invoice_number = invoice_number
        self.transaction_page = transaction_page
        self.total_amount_paid = force_amount
        self.short_items = short_items
        self.words_per_item = words_per_item

        self.item_list: list[str] = []
        self.item_tuples: list[tuple[str, float]] = []
        self.pre_tax_total: float | None = None
        self.after_tax_total: float | None = None
        self.tax_total: float | None = None
        self.tax_rate: float | None = None
        self.payment_date: date | None = None

        self._parsed_as_soup: bs4.BeautifulSoup = bs(
            self.transaction_page, "html.parser"
        )

        self._parse_orchestrator()

    def _parse_items(self) -> None:
        item_names = self._parsed_as_soup.find_all(
            "i"
        )  # the only italic element in the invoice is the item names

        for item in item_names:
            num_items = int(item.parent.text.split()[0])
            item_name = item.text
            item_value = float(item.parent.parent.findAll("td")[1].text.strip()[1:])
            self.item_tuples.append((item_name, item_value * num_items))

        if self.short_items:
            self.item_list = list(
                map(
                    lambda x: shorten_string(x[0], self.words_per_item),
                    self.item_tuples,
                )
            )
        else:
            self.item_list = list(map(lambda x: x[0], self.item_tuples))

    def _parse_pre_tax_total(self) -> None:

        search_by = re.compile("Total before tax")

        pre_tax_total_element = not_none(
            not_none(
                not_none(
                    not_none(self._parsed_as_soup.find(text=search_by)).parent
                ).parent
            ).findAll("td")
        )[1].text.strip()

        pre_tax_total_value = float(
            pre_tax_total_element.replace("$", "").replace(",", "")
        )

        self.pre_tax_total = pre_tax_total_value

    def _parse_tax_total(self) -> None:
        search_by = re.compile(r"Estimated tax to be collected")

        tax_total_element = not_none(
            not_none(
                not_none(
                    not_none(self._parsed_as_soup.find(text=search_by)).parent
                ).parent
            ).findAll("td")
        )[1].text.strip()

        tax_total_value = float(tax_total_element.replace("$", "").replace(",", ""))

        self.tax_total = tax_total_value

    def _parse_after_tax_total(self) -> None:

        search_by = re.compile(r"Estimated tax to be collected")

        tax_total_element = not_none(
            not_none(
                not_none(
                    not_none(self._parsed_as_soup.find(text=search_by)).parent
                ).parent
            ).findAll("td")
        )[1].text.strip()

        tax_total_value = float(tax_total_element.replace("$", "").replace(",", ""))

        self.tax_total = tax_total_value

    def _calculate_tax_rate(self) -> None:

        if self.pre_tax_total is not None and self.tax_total is not None:
            self.tax_rate = self.tax_total / self.pre_tax_total

    def _parse_payment_date(self) -> None:

        search_by = re.compile(r"Credit Card transactions")

        # this is a little bit hacky, but when we have more than one transaction, we want the one that matches the payment we have from self.total_amount_paid. To do this, I look for that value on the credit card transactions of the invoice, and then the <td> elemenet before that contains the date
        search_in_block = not_none(
            not_none(
                not_none(
                    not_none(
                        not_none(
                            not_none(self._parsed_as_soup.find(text=search_by)).parent
                        ).parent
                    ).parent
                ).parent
            ).findAll("td")
        )[1].findAll("td")

        for ix, text_ in enumerate(search_in_block):
            text_ = (
                text_.text.strip().replace("$", "").replace(",", "")
            )  # this is to clean the potential amount paid
            try:
                if float(text_) == abs(
                    not_none(self.total_amount_paid)
                ):  # self.total_amount_paid is negative
                    date_string: str = (
                        search_in_block[ix - 1].text.strip().split(":")[1].strip()
                    )

                    self.payment_date = datetime.strptime(
                        date_string, "%B %d, %Y"
                    ).date()
            except ValueError:
                pass

    def _parse_orchestrator(self) -> None:
        self._parse_items()
        self._parse_pre_tax_total()
        self._parse_tax_total()
        self._calculate_tax_rate()
        self._parse_payment_date()
        print(self.item_list, self.payment_date, self.total_amount_paid)
