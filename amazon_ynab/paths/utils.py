from typing import Union

import pathlib


def check_if_path_exists(path: Union[str, pathlib.Path]) -> bool:
    """
    Checks if a path exists.
    """
    return pathlib.Path(path).exists()
