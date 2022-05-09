from typing import Dict

import yaml
from rich.console import Console


# read from "./paths.yml" and return the paths as a dictionary
def get_paths() -> dict[str, str]:
    with open("./paths.yml", encoding="utf-8") as paths_file:
        paths: dict[str, str] = yaml.safe_load(paths_file)
    return paths


def print_paths() -> None:
    console = Console()
    paths: dict[str, str] = get_paths()
    console.print(paths)


if __name__ == "__main__":
    print_paths()
