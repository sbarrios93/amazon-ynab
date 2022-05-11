from typing import Union

import time
from datetime import datetime, timedelta
from random import randint

from rich.console import Console
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TimeElapsedColumn
from selenium.common.exceptions import (
    ElementNotSelectableException,
    ElementNotVisibleException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver as Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from amazon_ynab.amazon.invoice_parser import TransactionInvoice


class AmazonClient:
    def __init__(
        self,
        user_email: str,
        user_password: str,
        run_headless: bool = False,
        days_back: int = 30,
        today_inclusive: bool = False,
    ):
        # TODO: check if anything different is needed for running on raspberry pi, jetson nano

        self.user_email = user_email
        self.user_password = user_password
        self.run_headless = run_headless
        self.days_back = days_back
        self.today_inclusive = today_inclusive

        if today_inclusive:
            self.cutoff_date: datetime = datetime.today() - timedelta(
                days=self.days_back + 1
            )
        else:
            self.cutoff_date = datetime.today() - timedelta(days=self.days_back)

        self.raw_transaction_data: list[str] = []

        self.transactions: dict[str, dict[str, Union[str, float]]] = {}

        self.urls: dict[str, str] = {
            "homepage": "https://amazon.com",
            "transactions": "https://www.amazon.com/cpe/yourpayments/transactions",
            "invoice": "https://www.amazon.com/gp/css/summary/print.html/ref=ppx_yo_dt_b_invoice_o00?ie=UTF8&orderID={}",
        }

        self.invoices: dict[str, TransactionInvoice] = {}

    def _start_driver(self) -> None:

        Console().print("Starting driver...")

        options = ChromeOptions()

        if self.run_headless:
            Console().print("[yellow]Running in headless mode[/]")
            options.add_argument("--headless")

        self.driver = Chrome(ChromeDriverManager().install(), options=options)
        self.wait_driver = WebDriverWait(
            self.driver,
            10,
            poll_frequency=2,
            ignored_exceptions=[
                ElementNotVisibleException,
                ElementNotSelectableException,
            ],
        )
        Console().print("[green]Driver created[/]")

    def _sign_in(self) -> None:
        self.driver.get(self.urls["transactions"])

        # TODO: delete this commented block
        # signin_elem = self.wait_driver.until(
        #     EC.element_to_be_clickable((By.XPATH, "//a[@data-nav-role ='signin']"))
        # )
        # signin_elem.click()
        # time.sleep(1)

        email_elem = self.wait_driver.until(
            EC.element_to_be_clickable((By.ID, "ap_email"))
        )
        email_elem.clear()
        email_elem.send_keys(self.user_email)
        self.driver.find_element_by_id("continue").click()

        password_elem = self.wait_driver.until(
            EC.element_to_be_clickable((By.ID, "ap_password"))
        )
        password_elem.clear()
        password_elem.send_keys(self.user_password)
        self.driver.find_element_by_name("rememberMe").click()
        self.driver.find_element_by_id("signInSubmit").click()

        time.sleep(2)

    def _get_raw_transactions(self) -> None:

        self.driver.get(self.urls["transactions"])

        inside_time_frame: bool = True
        while inside_time_frame:

            transaction_divs = self.wait_driver.until(
                EC.presence_of_all_elements_located(
                    (
                        By.XPATH,
                        '//div[@class="a-section a-spacing-base apx-transactions-line-item-component-container"]',
                    )
                )
            )
            transaction_texts = list(
                map(lambda transaction_div: str(transaction_div.text), transaction_divs)
            )

            self.raw_transaction_data += transaction_texts

            # now we need to check the dates of the transactions of the last page, and if they are older than the cutoff date, we need stop the loop
            dates_divs = self.driver.find_elements_by_xpath(
                '//div[contains(@class,"a-section a-spacing-base a-padding-base apx-transaction-date-container")]'
            )

            transaction_dates_texts = list(
                map(lambda date_div: str(date_div.text), dates_divs)
            )

            transaction_dates = list(
                map(
                    lambda date_text: datetime.strptime(date_text, "%B %d, %Y"),
                    transaction_dates_texts,
                )
            )

            if min(transaction_dates) < self.cutoff_date:
                inside_time_frame = False
            else:  # if the last transaction is not older than the cutoff date, we need to click the next button
                pagination_elem = self.wait_driver.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//span[contains(text(), "Next Page")]//parent::span/input',
                        )
                    )
                )

                pagination_elem.click()
                time.sleep(4)

    def _transaction_to_dict(
        self, transaction: list[str]
    ) -> tuple[str, dict[str, Union[str, float]]]:

        payment_type: str = (
            "Gift Card" if "Gift Card" in transaction[0] else "Credit Card"
        )
        amount: float = float(transaction[1].replace("$", "").replace(",", ""))
        order_number: str = transaction[2].split(" ")[-1].replace("#", "")

        return order_number, {"payment_type": payment_type, "amount": amount}

    def _parse_raw_transactions(self) -> None:

        transactions: list[list[str]] = [
            tx.split("\n") for tx in self.raw_transaction_data
        ]

        self.transactions = dict(
            map(lambda tx: self._transaction_to_dict(tx), transactions)
        )

    def _get_invoice_page(self, order_number: str) -> str:
        self.driver.get(self.urls["invoice"].format(order_number))
        time.sleep(randint(50, 200) / 100.0)
        return self.driver.page_source

    def _process_invoices(self) -> None:

        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            processing_tasks = progress.add_task(
                "[green]Processing Invoices[/]", total=len(list(self.transactions))
            )

            for order_number in self.transactions.keys():
                progress.print(f"[green]{order_number}[/]")
                invoice_page = self._get_invoice_page(order_number)
                self.invoices[order_number] = TransactionInvoice(
                    order_number, invoice_page
                )
                progress.update(processing_tasks, advance=1)

    def run_pipeline(self) -> None:
        self._start_driver()
        self._sign_in()
        self._get_raw_transactions()
        self._parse_raw_transactions()
        self._process_invoices()
