from typing import Dict, Optional, Union

import pathlib

import typer
import yaml
from rich.console import Console

from amazon_ynab import version
from amazon_ynab.amazon.amazon_client import AmazonClient
from amazon_ynab.paths.common_paths import get_paths
from amazon_ynab.paths.utils import check_if_path_exists
from amazon_ynab.utils import utils

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
def run(
    path_to_secrets: str = typer.Option(
        PATHS["SECRETS_PATH"], "--secrets", "-s", help="Path to secrets file"
    )
) -> None:

    if not check_if_path_exists(path_to_secrets):
        console.print(
            "[red]✘[/] Secrets file does not exist, either run the init command or create the secrets file manually. Paths are defined in the paths.yml file."
        )
        raise typer.Exit()
    else:
        secrets = utils.load_secrets(path_to_secrets)

        # init client
        amazon_client = AmazonClient(
            secrets["amazon"]["username"], secrets["amazon"]["password"]
        )

        amazon_client.start_driver()
        amazon_client.sign_in()
        amazon_client.get_raw_transactions()


# add callback so we can access some options without using arguments
@app.callback()
def callback(
    print_version: bool = typer.Option(
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
