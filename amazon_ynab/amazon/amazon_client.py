import time
from datetime import datetime, timedelta

from rich.console import Console
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


class AmazonClient:
    def __init__(
        self,
        user_email: str,
        user_password: str,
        run_headless: bool = False,
        days_back: int = 30,
        today_inclusive: bool = False,
    ):

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

        # TODO: check if anything different is needed for running on raspberry pi, jetson nano
        self.urls: dict[str, str] = {
            "homepage": "https://amazon.com",
            "transactions": "https://www.amazon.com/cpe/yourpayments/transactions",
        }

    def start_driver(self) -> None:

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

    def sign_in(self) -> None:
        self.driver.get(self.urls["homepage"])

        signin_elem = self.wait_driver.until(
            EC.element_to_be_clickable((By.XPATH, "//a[@data-nav-role ='signin']"))
        )
        signin_elem.click()

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

    def get_raw_transactions(self) -> None:

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

        print(self.raw_transaction_data)
