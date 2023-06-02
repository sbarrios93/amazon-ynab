from typing import Annotated

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
    path_to_secrets: Annotated[
        str, typer.Option("--secrets", "-s", help="Path to secrets file")
    ] = PATHS["SECRETS_PATH"],
    restart: Annotated[
        bool, typer.Option("--restart", help="Force the recreation of the secrets file")
    ] = False,
) -> None:
    """Initialize the application."""
    console.print("Initializing the application...")

    if restart:
        # show warning, prompt user to confirm they want to overwrite the secrets file
        console.print(
            "[yellow]WARNING:[/] This will overwrite the secrets file at"
            f" {path_to_secrets}"
        )
        if typer.confirm("Are you sure you want to overwrite the secrets file?"):
            console.print("[yellow]Overwriting the secrets file...[/]")
            utils.create_secrets_file(path_to_secrets)
        else:
            console.print("[red]Aborting...[/]")
            raise typer.Exit()
    elif check_if_path_exists(path_to_secrets):
        # check if file containing the secrets exists
        console.print("[green]✔[/] Secrets file exists")
    else:
        console.print("[red]✘[/] Secrets file does not exist, creating it...")
        utils.create_secrets_file(path_to_secrets)


@app.command("run")
def run(
    path_to_secrets: Annotated[
        str, typer.Option("--secrets", "-s", help="Path to secrets file")
    ] = PATHS["SECRETS_PATH"],
    headless: Annotated[
        bool, typer.Option("--headless", "-h", help="Run selenium in headless mode")
    ] = False,
    days_back: Annotated[
        int, typer.Option("--days-back", "-d", help="Number of days back to scrape")
    ] = 30,
    short_items: Annotated[
        bool,
        typer.Option("--short-items", "-s", help="Shorten item names to fit in YNAB"),
    ] = False,
    words_per_item: Annotated[
        int,
        typer.Option(
            "--words-per-item",
            "-w",
            help=(
                "Number of words to show per item [Only used when --short-items is set]"
            ),
        ),
    ] = 6,
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
    pass


if __name__ == "__main__":
    app()
