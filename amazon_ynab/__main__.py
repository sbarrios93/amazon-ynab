from datetime import datetime

import typer
from rich.console import Console

from amazon_ynab import version
from amazon_ynab.amazon.amazon_client import AmazonClient
from amazon_ynab.matcher.matcher import match_transactions
from amazon_ynab.paths.common_paths import get_paths
from amazon_ynab.paths.utils import check_if_path_exists
from amazon_ynab.utils import utils
from amazon_ynab.ynab.ynab_client import YNABClient

PATHS: dict[str, str] = get_paths()


app: typer.Typer = typer.Typer(
    name="amazon-ynab",
    help="Amazon YNAB is a reconciler that scrapes Amazon orders and adds memo info on each corresponding YNAB transaction",
    add_completion=False,
)
console = Console()


def version_callback(print_version: bool) -> None:
    """Print the version of the package."""
    if print_version:
        console.print(f"[yellow]amazon-ynab[/] version: [bold blue]{version}[/]")
        raise typer.Exit()


@app.command("init")
def init_app(
    path_to_secrets: str = typer.Option(
        PATHS["SECRETS_PATH"], "--secrets", "-s", help="Path to secrets file"
    ),
    restart: bool = typer.Option(
        False, "--restart", help="Force the recreation of the secrets file"
    ),
) -> None:
    """Initialize the application."""
    console.print("Initializing the application...")

    if restart:
        # show warning, prompt user to confirm they want to overwrite the secrets file
        console.print(
            f"[yellow]WARNING:[/] This will overwrite the secrets file at {path_to_secrets}"
        )
        confirm = typer.confirm("Are you sure you want to overwrite the secrets file?")
        if confirm:
            console.print("[yellow]Overwriting the secrets file...[/]")
            utils.create_secrets_file(path_to_secrets)
        else:
            console.print("[red]Aborting...[/]")
            raise typer.Exit()
    else:
        # check if file containing the secrets exists
        if check_if_path_exists(path_to_secrets):
            console.print("[green]✔[/] Secrets file exists")
        else:
            console.print("[red]✘[/] Secrets file does not exist, creating it...")
            utils.create_secrets_file(path_to_secrets)


@app.command("run")
def run(  # noqa
    path_to_secrets: str = typer.Option(
        PATHS["SECRETS_PATH"], "--secrets", "-s", help="Path to secrets file"
    ),
    headless: bool = typer.Option(
        False, "--headless", "-h", help="Run selenium in headless mode"
    ),
    days_back: int = typer.Option(
        30, "--days-back", "-d", help="Number of days back to scrape"
    ),
    today_inclusive: bool = typer.Option(
        False, "--today-inclusive", "-t", help="Include today in the scrape"
    ),
    short_items: bool = typer.Option(
        False, "--short-items", "-s", help="Shorten item names to fit in YNAB"
    ),
    words_per_item: int = typer.Option(
        6,
        "--words-per-item",
        "-w",
        help="Number of words to show per item [Only used when --short-items is set]",
    ),
) -> None:

    if not check_if_path_exists(path_to_secrets):
        console.print(
            "[red]✘[/] Secrets file does not exist, either run the init command or create the secrets file manually. Paths are defined in the paths.yml file."
        )
        raise typer.Exit()

    secrets: dict[str, dict[str, str]] = utils.load_secrets(path_to_secrets)

    # parse days back to a datetime date
    cutoff_date: datetime = utils.days_back_to_cutoff_date(days_back)

    # init client
    amazon_client = AmazonClient(
        user_credentials=(secrets["amazon"]["username"], secrets["amazon"]["password"]),
        run_headless=headless,
        cutoff_date=cutoff_date,
        short_items=short_items,
        words_per_item=words_per_item,
    )

    # amazon_client.run_pipeline()

    ynab_client = YNABClient(secrets["ynab"]["token"], cutoff_date)

    # prepare the YNAB Client to be used. First call the YNAB Client read the budgets.
    ynab_client.prepare_client()

    # if there is an entry on the secrets file that has a budget id
    # we can use that one as long as it is contained in the budgets
    if secrets["ynab"]["budget_id"]:
        budget_matched = False
        for _, budget_id in ynab_client.all_budgets.items():
            if budget_id == secrets["ynab"]["budget_id"]:
                ynab_client.selected_budget = budget_id
                budget_matched = True
                console.print(
                    f"[green]✔[/] Budget ID matched: {ynab_client.selected_budget}"
                )
                break
        if not budget_matched:
            console.print(
                "[red]✘[/] Budget ID found on secrets file, but it is not in the YNAB budgets list, if you want to use a specific budget id, please add it to the secrets file. You can also set it to null on the secrets file and the program will prompt you for a budget id."
            )
            raise typer.Exit()
    elif len(ynab_client.all_budgets) == 1:
        # if we only have one budget and no budget id, we can use that one

        console.print(
            f"[yellow]WARNING:[/] No budget ID found on secrets file, using the only budget ID found: {list(ynab_client.all_budgets.keys())[0]}"
        )
        ynab_client.selected_budget = ynab_client.all_budgets[
            list(ynab_client.all_budgets.keys())[0]
        ]
    else:
        # if no budget id is found in the secrets file, and there is more than one budget prompt the user to select one
        console.print(
            "[yellow]No budget ID found in secrets file, please select one[/]"
        )
        ynab_client.prompt_user_for_budget_id()

        ynab_client.selected_budget = secrets["ynab"]["budget_id"]
    ynab_client._parse_filtered_transactions()

    print("timestop")

    match_transactions(amazon_client.invoices, ynab_client.transactions_to_match)


# add callback so we can access some options without using arguments
@app.callback()
def callback(
    print_version: bool = typer.Option(  # noqa
        None,
        "-v",
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Prints the version of the amazon-ynab package.",
    )
) -> None:
    """Print the version of the package."""
    pass  # noqa


if __name__ == "__main__":
    app()
