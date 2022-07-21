import time
from datetime import datetime
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
from amazon_ynab.utils.custom_types import (
    AmazonInnerTransactionsDict,
    AmazonInvoicesDict,
    AmazonTransactionsDict,
)


class AmazonClient:
    def __init__(
        self,
        user_credentials: tuple[str, str],
        run_headless: bool,
        cutoff_date: datetime,
        short_items: bool,
        words_per_item: int,
    ):  # noqa
        # TODO: check if anything different is needed for running on raspberry pi, jetson nano

        self.user_email = user_credentials[0]
        self.user_password = user_credentials[1]
        self.run_headless = run_headless
        self.cutoff_date = cutoff_date
        self.short_items = short_items
        self.words_per_item = words_per_item

        self.raw_transaction_data: list[str] = []

        self.transactions: AmazonTransactionsDict = {}

        self.urls: dict[str, str] = {
            "homepage": "https://amazon.com",
            "transactions": "https://www.amazon.com/cpe/yourpayments/transactions",
            "invoice": "https://www.amazon.com/gp/css/summary/print.html/ref=ppx_yo_dt_b_invoice_o00?ie=UTF8&orderID={}",
        }

        self.invoices: AmazonInvoicesDict = {}

    def _start_driver(self) -> None:

        Console().print("Starting driver...")

        options = ChromeOptions()

        if self.run_headless:
            Console().print("[yellow]Running in headless mode[/]")
            options.add_argument("--headless")

        self.driver = Chrome(ChromeDriverManager().install(), options=options)
        self.wait_driver = WebDriverWait(
            self.driver,
            30,
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
        self.driver.find_element("id", "continue").click()

        password_elem = self.wait_driver.until(
            EC.element_to_be_clickable((By.ID, "ap_password"))
        )
        password_elem.clear()
        password_elem.send_keys(self.user_password)
        self.driver.find_element("name", "rememberMe").click()
        self.driver.find_element("id", "signInSubmit").click()

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
                map(
                    lambda transaction_div: str(transaction_div.text),
                    transaction_divs,
                )
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
            else:  # if the last transaction is not older than the cutoff date, we need to click the next button unless is the last page
                if "end of the line" in self.driver.page_source:
                    break

                pagination_elem = self.wait_driver.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//span[contains(text(), "Next Page")]//parent::span/input',
                        )
                    )
                )

                pagination_elem.click()
                time.sleep(randint(200, 350) / 100.0)

    def _transaction_to_dict(
        self, transaction: list[str]
    ) -> tuple[str, AmazonInnerTransactionsDict]:

        payment_type: str = (
            "Gift Card" if "Gift Card" in transaction[0] else "Credit Card"
        )
        amount: float = float(transaction[1].replace("$", "").replace(",", ""))
        order_number: str = transaction[2].split(" ")[-1].replace("#", "")

        if transaction[-1].split()[-1].lower() == "tips":
            is_tip: bool = True
        else:
            is_tip = False

        return order_number, {
            "payments": {payment_type: amount},
            "is_tip": is_tip,
        }

    def _parse_raw_transactions(self) -> None:

        transactions: list[list[str]] = [
            tx.split("\n") for tx in self.raw_transaction_data
        ]

        for transaction in transactions:
            order_number, order_info = self._transaction_to_dict(transaction)
            if order_info["is_tip"]:  # dont parse tip orders
                pass
            else:
                # some transactions can be paid with more than one type of payment type, lets look if the order number
                # already exists, meaning that there are multiple entries for the same order, if not, then add a new entry
                if self.transactions.get(order_number, None) is None:
                    self.transactions[order_number] = order_info
                else:
                    self.transactions[order_number]["payments"].update(
                        order_info["payments"]
                    )

        Console().print(f"[blue]Found {len(self.transactions)} transactions[/]")

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
                "[green]Processing Invoices[/]",
                total=len(list(self.transactions)),
            )

            for order_number in self.transactions:
                # dont parse amazon transactions that are not products
                # this could be an amazon prime payment or other type of payment
                # this order ids usually start with a letter instead of a number

                if order_number[0].isalpha():
                    progress.print(
                        f"[yellow]{order_number} is not a product[/]...skipping"
                    )
                else:
                    progress.print(f"[green]{order_number}[/]")
                    # we only care about what we paid with credit/debit card, not with gift card
                    if (
                        self.transactions[order_number]["payments"].get(
                            "Credit Card", None
                        )
                        is not None
                    ):
                        invoice_page = self._get_invoice_page(order_number)
                        self.invoices[order_number] = TransactionInvoice(
                            order_number,
                            invoice_page,
                            force_amount=self.transactions[order_number]["payments"][
                                "Credit Card"
                            ],
                            short_items=self.short_items,
                            words_per_item=self.words_per_item,
                        )
                    else:
                        progress.print(
                            f"[yellow]{order_number} is not a credit card transaction[/]"
                        )
                        for payment_type, amount in self.transactions[order_number][
                            "payments"
                        ].items():
                            if amount is not None:
                                progress.print(
                                    f"[yellow]Order got a {payment_type} payment of {amount}[/]"
                                )

                progress.update(processing_tasks, advance=1)

    def run_pipeline(self) -> None:
        self._start_driver()
        self._sign_in()
        self._get_raw_transactions()
        self._parse_raw_transactions()
        self._process_invoices()
