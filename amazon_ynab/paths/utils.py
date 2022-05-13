import pathlib


def check_if_path_exists(path: str | pathlib.Path) -> bool:
    """
    Checks if a path exists.
    """
    return pathlib.Path(path).exists()
