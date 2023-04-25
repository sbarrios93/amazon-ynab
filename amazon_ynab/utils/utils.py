from typing import TypeVar

import pathlib
from datetime import datetime, timedelta

import typer
import yaml
from rich.console import Console

T = TypeVar("T")


def create_secrets_file(path: str | pathlib.Path) -> None:
    console = Console()
    # create the secrets file
    amazon_username = typer.prompt("Amazon email: ")
    amazon_password = typer.prompt(
        "Amazon password: ", hide_input=True, confirmation_prompt=True
    )
    ynab_token = typer.prompt("YNAB token: ")
    amazon_payee_id = typer.prompt("Amazon payee ID: ")
    amazon_payee_name = typer.prompt("Amazon payee name: ")

    secrets = {
        "amazon": {
            "username": amazon_username,
            "password": amazon_password,
        },
        "ynab": {
            "token": ynab_token,
            "amazon_payee_id": amazon_payee_id,
            "amazon_payee_name": amazon_payee_name,
        },
    }
    # make path (dir) if it doesn't exist
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as secrets_file:
        yaml.dump(secrets, secrets_file)

    console.print(f"[green]Created secrets file at {path}[/]")


def load_secrets(path: str | pathlib.Path) -> dict[str, dict[str, str]]:
    with open(path, encoding="utf-8") as secrets_file:
        secrets: dict[str, dict[str, str]] = yaml.load(
            secrets_file, Loader=yaml.SafeLoader
        )

    return secrets


def not_none(obj: T | None, *, message: str | None = None) -> T:
    """Check that obj is not None. Raises TypeError if it is.

    This is meant to help get code to type check that uses Optional types.

    """
    if obj is None:
        if message is not None:
            raise TypeError(message)
        raise TypeError("object is unexpectedly None")
    return obj


def days_back_to_cutoff_date(days_back: int) -> datetime:
    cutoff_date = datetime.today() - timedelta(days=days_back)

    return cutoff_date
