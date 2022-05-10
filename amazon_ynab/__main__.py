# type: ignore[attr-defined]
from typing import Dict, Optional, Union

import pathlib

import typer
import yaml
from rich.console import Console

from amazon_ynab import version
from amazon_ynab.paths.common_paths import get_paths
from amazon_ynab.paths.utils import check_if_path_exists

PATHS: dict[str, str] = get_paths()


app = typer.Typer(
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


def create_secrets_file(path: Union[str, pathlib.Path]) -> None:
    # create the secrets file
    amazon_username = typer.prompt("Amazon email: ")
    amazon_password = typer.prompt(
        "Amazon password: ", hide_input=True, confirmation_prompt=True
    )
    ynab_token = typer.prompt("YNAB token: ")

    secrets = {
        "amazon": {
            "username": amazon_username,
            "password": amazon_password,
        },
        "ynab": {
            "token": ynab_token,
        },
    }
    # make path if it doesn't exist
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as secrets_file:
        yaml.dump(secrets, secrets_file)

    console.print(f"[green]Created secrets file at {path}[/]")

    return None


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
        console.print("[yellow]WARNING[/]")
        console.print(f"This will overwrite the secrets file at {path_to_secrets}")
        confirm = typer.confirm("Are you sure you want to overwrite the secrets file?")
        if confirm:
            console.print("[green]Overwriting the secrets file...[/]")
            create_secrets_file(path_to_secrets)
        else:
            console.print("[red]Aborting...[/]")
            raise typer.Exit()
    else:
        # check if file containing the secrets exists
        if check_if_path_exists(path_to_secrets):
            console.print("[green]✔[/] Secrets file exists")
        else:
            console.print("[red]✘[/] Secrets file does not exist, creating it...")
            create_secrets_file(path_to_secrets)


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
    pass


if __name__ == "__main__":
    app()
