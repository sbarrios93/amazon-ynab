from typing import Union

import pathlib

import typer
import yaml
from rich.console import Console


def create_secrets_file(path: Union[str, pathlib.Path]) -> None:

    console = Console()
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
    # make path (dir) if it doesn't exist
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as secrets_file:
        yaml.dump(secrets, secrets_file)

    console.print(f"[green]Created secrets file at {path}[/]")


def load_secrets(path: Union[str, pathlib.Path]) -> dict[str, dict[str, str]]:

    with open(path, encoding="utf-8") as secrets_file:
        secrets: dict[str, dict[str, str]] = yaml.load(
            secrets_file, Loader=yaml.SafeLoader
        )

    return secrets
