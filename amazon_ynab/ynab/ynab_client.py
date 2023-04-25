from typing import Any

import json
import re
from datetime import datetime

import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.rule import Rule

from amazon_ynab.utils.custom_types import YNABTransactionsDict


class YNABClient:
    def __init__(self, token: str, since_date: datetime) -> None:
        self.token = token
        self.since_date = since_date

        self.urls: dict[str, str] = {"base": "https://api.youneedabudget.com/v1"}

        self.urls["budgets"] = self.urls["base"] + "/budgets"
        self.urls["transactions"] = self.urls["budgets"] + "/{}/transactions"

        self.request_headers: dict[str, str] = {
            "Authorization": f"Bearer {self.token}",
            "accept": "application/json",
        }

        self.all_budgets: dict[str, str] = {}
        self.selected_budget: str | None = None  # budget id in the API

        self.transactions_to_match: YNABTransactionsDict = {}

        self.tip_transactions: YNABTransactionsDict = {}

    def _get_budgets(self) -> Any:
        """
        Gets all budgets associated with the user's account.
        """
        url = self.urls["budgets"]
        response = requests.get(url, headers=self.request_headers)
        return response.json()["data"]["budgets"]

    def _parse_budgets(self) -> None:
        """
        Selects the budget that contains the transactions.
        """

        for budget in self._get_budgets():
            self.all_budgets[budget["name"]] = budget["id"]

    def prepare_client(self) -> None:
        """
        Prepares the client to be used.
        """
        self._parse_budgets()

    def prompt_user_for_budget_id(self) -> None:
        """
        Prompts the user to select a budget.
        """
        console = Console()

        console.print(Rule(title="[bold]Select a budget from the list below:[/]"))

        for num, (budget_name, budget_id) in enumerate(self.all_budgets.items()):
            console.print(Markdown(f"{num + 1}. {budget_name}"))

        selected = int(
            Prompt(
                "Enter a number: ",
                console=console,
                show_choices=True,
                choices=list(str(i) for i in list(range(1, len(self.all_budgets) + 1))),
            ).ask()
        )

        self.selected_budget = list(self.all_budgets.values())[selected - 1]

        console.print(Rule())

    def _get_transactions(self):
        """
        Gets all transactions associated with the budget.
        """

        params: dict[str, str] = {"since_date": self.since_date.strftime("%Y-%m-%d")}

        url = self.urls["transactions"].format(self.selected_budget)
        response = requests.get(url, headers=self.request_headers, params=params)
        print(response.json())
        return response.json()["data"]["transactions"]

    @staticmethod
    def _filter_transactions(transactions: Any) -> Any:
        """
        Filters transactions by date.
        """

        search_by = re.compile(r"^.*[amazon|AMZN].*$", re.IGNORECASE)

        filtered_transactions = filter(
            lambda item: search_by.match(item["payee_name"])
            and (item["memo"] in ["", None]),
            transactions,
        )

        return filtered_transactions

    def parse_transactions(self) -> None:
        """
        Parses the transactions.
        """
        search_by = re.compile(r"^.*Tips.*$", re.IGNORECASE)

        for transaction in self._filter_transactions(self._get_transactions()):
            # let's isolate the tip transactions
            if search_by.match(transaction["payee_name"]):
                self.tip_transactions[transaction["id"]] = {
                    "amount": transaction["amount"],
                    "date": datetime.strptime(transaction["date"], "%Y-%m-%d").date(),
                    "payee": transaction["payee_name"],
                    "memo": transaction["memo"],
                }

            else:
                self.transactions_to_match[transaction["id"]] = {
                    "amount": transaction["amount"],
                    "date": datetime.strptime(transaction["date"], "%Y-%m-%d").date(),
                    "payee": transaction["payee_name"],
                    "memo": transaction["memo"],
                }

    def bulk_patch_transactions(self, transactions: list[dict[str, Any]]) -> None:
        data = json.dumps({"transactions": transactions})

        self.request_headers.update({"Content-Type": "application/json"})

        resp = requests.patch(
            self.urls["transactions"].format(self.selected_budget),
            data=data,
            headers=self.request_headers,
        )
        if resp.status_code != 200:
            print(f"Something went wrong, got response: {str(resp.content)}")
        else:
            print(f"Successfully updated transactions {transactions}")
