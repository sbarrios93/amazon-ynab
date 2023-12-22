from datetime import datetime

import typer
from rich.console import Console

from amazon_ynab.amazon.amazon_client import AmazonClient
from amazon_ynab.engine.matcher import match_transactions
from amazon_ynab.engine.patcher import patcher, tips_patcher
from amazon_ynab.utils.custom_types import MatchedTransactionsList
from amazon_ynab.ynab.ynab_client import YNABClient


class Engine:
    def __init__(  # noqa: PLR0913 Too many arguments to function call
        self,
        secrets: dict[str, dict[str, str]],
        run_headless: bool,
        cutoff_date: datetime,
        short_items: bool,
        words_per_item: int,
    ) -> None:
        self.secrets = secrets
        self.run_headless = run_headless
        self.cutoff_date = cutoff_date
        self.short_items = short_items
        self.words_per_item = words_per_item

        self.console = Console()

        self.matched_transactions: MatchedTransactionsList = []

        self.amazon_client = AmazonClient(
            user_credentials=(
                self.secrets["amazon"]["username"],
                self.secrets["amazon"]["password"],
            ),
            run_headless=self.run_headless,
            cutoff_date=self.cutoff_date,
            short_items=self.short_items,
            words_per_item=self.words_per_item,
        )

        self.ynab_client = YNABClient(self.secrets["ynab"]["token"], self.cutoff_date)

    def pre_start_ynab(self) -> None:
        # we need to call the ynab client to read the budgets
        self.ynab_client.prepare_client()

        if self.secrets["ynab"].get("budget_id"):
            budget_matched = False
            for _, budget_id in self.ynab_client.all_budgets.items():
                if budget_id == self.secrets["ynab"]["budget_id"]:
                    self.ynab_client.selected_budget = budget_id
                    budget_matched = True
                    self.console.print(
                        "[green]✔[/] Budget ID matched:"
                        f" {self.ynab_client.selected_budget}"
                    )
                    break
            if not budget_matched:
                self.console.print(
                    "[red]✘[/] Budget ID found on secrets file, but it is not in the"
                    " YNAB budgets list, if you want to use a specific budget id,"
                    " please add it to the secrets file. You can also set it to null on"
                    " the secrets file and the program will prompt you for a budget id."
                )
                raise typer.Exit()
        elif len(self.ynab_client.all_budgets) == 1:
            # if we only have one budget and no budget id, we can use that one
            self.console.print(
                "[yellow]WARNING:[/] No budget ID found on secrets file, using the"
                " only budget ID found: "
                f"{next(iter(self.ynab_client.all_budgets.keys()))}"
            )
            self.ynab_client.selected_budget = self.ynab_client.all_budgets[
                next(iter(self.ynab_client.all_budgets.keys()))
            ]
        else:
            # if no budget id is found in the secrets file, and there is
            # more than one budget prompt the user to select one
            self.console.print("[red]✘[/] No budget ID found on secrets file")
            self.ynab_client.prompt_user_for_budget_id()

    def run(self) -> None:
        self.pre_start_ynab()
        self.amazon_client.run_pipeline()
        self.ynab_client.parse_transactions()

        self.matched_transactions = match_transactions(
            self.amazon_client.invoices, self.ynab_client.transactions_to_match
        )

        patcher(
            amazon_client=self.amazon_client,
            ynab_client=self.ynab_client,
            matched_transactions=self.matched_transactions,
            payee_id=self.secrets["ynab"]["amazon_payee_id"],
            payee_name=self.secrets["ynab"]["amazon_payee_name"],
        )

        tips_patcher(
            ynab_client=self.ynab_client,
            payee_id=self.secrets["ynab"]["amazon_payee_id"],
            payee_name=self.secrets["ynab"]["amazon_payee_name"],
        )
