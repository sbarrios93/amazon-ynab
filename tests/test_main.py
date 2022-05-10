# type: ignore[attr-defined]
from typer.testing import CliRunner

from amazon_ynab.__main__ import app

runner = CliRunner()


def test_version_callback():
    """Test the version_callback function."""
    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
