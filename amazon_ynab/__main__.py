from datetime import datetime

import typer
from rich.console import Console

from amazon_ynab import version
from amazon_ynab.engine.engine import Engine
from amazon_ynab.paths.common_paths import get_paths
from amazon_ynab.paths.utils import check_if_path_exists
from amazon_ynab.utils import utils

PATHS: dict[str, str] = get_paths()
app: typer.Typer = typer.Typer(
    name="amazon-ynab",
    help=(
        "Amazon YNAB is a reconciler that scrapes Amazon orders and adds memo info on"
        " each corresponding YNAB transaction"
    ),
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
            "[yellow]WARNING:[/] This will overwrite the secrets file at"
            f" {path_to_secrets}"
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
            "[red]✘[/] Secrets file does not exist, either run the init command or"
            " create the secrets file manually. Paths are defined in the paths.yml"
            " file."
        )
        raise typer.Exit()

    secrets = utils.load_secrets(path_to_secrets)
    # parse days back to a datetime date
    cutoff_date = utils.days_back_to_cutoff_date(days_back)

    engine = Engine(
        secrets=secrets,
        run_headless=headless,
        cutoff_date=cutoff_date,
        short_items=short_items,
        words_per_item=words_per_item,
    )

    engine.run()


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
