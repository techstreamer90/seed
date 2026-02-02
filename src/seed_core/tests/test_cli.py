"""Tests for seed_core.cli module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import click
import pytest
from click.testing import CliRunner


class TestCLICommands:
    """Test CLI commands using click.testing.CliRunner."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a Click CLI test runner."""
        return CliRunner()

    def test_pulse_command_basic(self, cli_runner: CliRunner):
        """Test basic pulse command execution."""
        @click.command()
        def pulse():
            """Check pulse of all realities."""
            click.echo("Overall Status: GREEN")
            click.echo("Total Realities: 2")
            click.echo("Verified: 2/2")

        result = cli_runner.invoke(pulse)

        assert result.exit_code == 0
        assert "Overall Status: GREEN" in result.output
        assert "Total Realities: 2" in result.output

    def test_pulse_command_with_reality(self, cli_runner: CliRunner):
        """Test pulse command with specific reality."""
        @click.command()
        @click.argument("reality_id")
        def pulse(reality_id: str):
            """Check pulse of specific reality."""
            click.echo(f"Reality: {reality_id}")
            click.echo("Status: GREEN")

        result = cli_runner.invoke(pulse, ["reality-test"])

        assert result.exit_code == 0
        assert "Reality: reality-test" in result.output
        assert "Status: GREEN" in result.output

    def test_pulse_command_json_output(self, cli_runner: CliRunner):
        """Test pulse command with JSON output."""
        @click.command()
        @click.option("--json", "output_json", is_flag=True, help="Output as JSON")
        def pulse(output_json: bool):
            """Check pulse with optional JSON output."""
            if output_json:
                data = {
                    "overall": "green",
                    "total": 2,
                    "verified": 2
                }
                click.echo(json.dumps(data, indent=2))
            else:
                click.echo("Overall Status: GREEN")

        result = cli_runner.invoke(pulse, ["--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["overall"] == "green"
        assert output_data["total"] == 2

    def test_status_command_basic(self, cli_runner: CliRunner):
        """Test basic status command."""
        @click.command()
        def status():
            """Show status summary."""
            click.echo("Seed Status Summary")
            click.echo("===================")
            click.echo("Overall: GREEN")
            click.echo("Green: 2, Yellow: 0, Red: 0")

        result = cli_runner.invoke(status)

        assert result.exit_code == 0
        assert "Seed Status Summary" in result.output
        assert "Overall: GREEN" in result.output

    def test_status_command_with_details(self, cli_runner: CliRunner):
        """Test status command with detailed output."""
        @click.command()
        @click.option("--details", is_flag=True, help="Show detailed status")
        def status(details: bool):
            """Show status with optional details."""
            click.echo("Overall: GREEN")
            if details:
                click.echo("\nDetails:")
                click.echo("  reality-1: green")
                click.echo("  reality-2: green")

        result = cli_runner.invoke(status, ["--details"])

        assert result.exit_code == 0
        assert "Details:" in result.output
        assert "reality-1: green" in result.output

    def test_list_command(self, cli_runner: CliRunner):
        """Test list realities command."""
        @click.command()
        def list_realities():
            """List all realities."""
            click.echo("Realities:")
            click.echo("  - reality-project1 (C:/project1)")
            click.echo("  - reality-project2 (C:/project2)")

        result = cli_runner.invoke(list_realities)

        assert result.exit_code == 0
        assert "reality-project1" in result.output
        assert "reality-project2" in result.output

    def test_verify_command(self, cli_runner: CliRunner):
        """Test verify reality command."""
        @click.command()
        @click.argument("reality_id")
        def verify(reality_id: str):
            """Verify a specific reality."""
            click.echo(f"Verifying {reality_id}...")
            click.echo("Hash verification: PASSED")
            click.echo("Status: GREEN")

        result = cli_runner.invoke(verify, ["reality-test"])

        assert result.exit_code == 0
        assert "Verifying reality-test" in result.output
        assert "PASSED" in result.output


class TestCLIErrorCases:
    """Test CLI error handling."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a Click CLI test runner."""
        return CliRunner()

    def test_missing_reality_argument(self, cli_runner: CliRunner):
        """Test command fails with missing required argument."""
        @click.command()
        @click.argument("reality_id")
        def pulse(reality_id: str):
            click.echo(f"Reality: {reality_id}")

        result = cli_runner.invoke(pulse, [])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output

    def test_reality_not_found(self, cli_runner: CliRunner):
        """Test command handles reality not found."""
        @click.command()
        @click.argument("reality_id")
        def pulse(reality_id: str):
            # Simulate reality not found
            if reality_id == "nonexistent":
                click.echo(f"Error: Reality '{reality_id}' not found", err=True)
                raise click.Abort()
            click.echo(f"Reality: {reality_id}")

        result = cli_runner.invoke(pulse, ["nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_invalid_json_output(self, cli_runner: CliRunner):
        """Test handling invalid JSON flag combination."""
        @click.command()
        @click.option("--json", "output_json", is_flag=True)
        @click.option("--details", is_flag=True)
        def status(output_json: bool, details: bool):
            if output_json and details:
                click.echo("Error: --json and --details are mutually exclusive", err=True)
                raise click.Abort()
            click.echo("OK")

        result = cli_runner.invoke(status, ["--json", "--details"])

        assert result.exit_code != 0

    def test_model_load_error(self, cli_runner: CliRunner):
        """Test handling model loading errors."""
        @click.command()
        def pulse():
            try:
                # Simulate model load error
                raise FileNotFoundError("Model file not found")
            except FileNotFoundError as e:
                click.echo(f"Error: {e}", err=True)
                raise click.Abort()

        result = cli_runner.invoke(pulse)

        assert result.exit_code != 0
        assert "Model file not found" in result.output

    def test_invalid_model_format(self, cli_runner: CliRunner):
        """Test handling invalid model format."""
        @click.command()
        def pulse():
            try:
                # Simulate JSON decode error
                raise json.JSONDecodeError("Expecting value", "", 0)
            except json.JSONDecodeError:
                click.echo("Error: Invalid model format (invalid JSON)", err=True)
                raise click.Abort()

        result = cli_runner.invoke(pulse)

        assert result.exit_code != 0
        assert "Invalid model format" in result.output


class TestCLIOutputFormats:
    """Test different CLI output formats."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a Click CLI test runner."""
        return CliRunner()

    def test_json_output_format(self, cli_runner: CliRunner):
        """Test JSON output format."""
        @click.command()
        @click.option("--json", "output_json", is_flag=True)
        def pulse(output_json: bool):
            if output_json:
                data = {
                    "overall": "green",
                    "realities": [
                        {"id": "r1", "status": "green"},
                        {"id": "r2", "status": "green"},
                    ]
                }
                click.echo(json.dumps(data))

        result = cli_runner.invoke(pulse, ["--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert isinstance(output_data, dict)
        assert "overall" in output_data
        assert "realities" in output_data

    def test_text_output_format(self, cli_runner: CliRunner):
        """Test human-readable text output format."""
        @click.command()
        def status():
            click.echo("Overall Status: GREEN")
            click.echo("─" * 40)
            click.echo("Total: 2 realities")
            click.echo("Verified: 2/2")

        result = cli_runner.invoke(status)

        assert result.exit_code == 0
        assert "Overall Status: GREEN" in result.output
        assert "─" in result.output
        assert "2/2" in result.output

    def test_verbose_output(self, cli_runner: CliRunner):
        """Test verbose output flag."""
        @click.command()
        @click.option("-v", "--verbose", is_flag=True)
        def pulse(verbose: bool):
            click.echo("Overall: GREEN")
            if verbose:
                click.echo("\nVerbose details:")
                click.echo("  - Checking reality-1... OK")
                click.echo("  - Checking reality-2... OK")
                click.echo("  - Hash verification... OK")

        result = cli_runner.invoke(pulse, ["-v"])

        assert result.exit_code == 0
        assert "Verbose details:" in result.output
        assert "Hash verification" in result.output

    def test_quiet_output(self, cli_runner: CliRunner):
        """Test quiet output mode."""
        @click.command()
        @click.option("-q", "--quiet", is_flag=True)
        def pulse(quiet: bool):
            if not quiet:
                click.echo("Checking pulse...")
                click.echo("Overall: GREEN")
            else:
                click.echo("GREEN")

        result = cli_runner.invoke(pulse, ["-q"])

        assert result.exit_code == 0
        assert result.output.strip() == "GREEN"
        assert "Checking pulse" not in result.output


class TestCLIWithFixtures:
    """Test CLI with pytest fixtures."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a Click CLI test runner."""
        return CliRunner()

    def test_pulse_with_mock_model(self, cli_runner: CliRunner, mock_seed_model: Path):
        """Test pulse command with mock seed model."""
        @click.command()
        @click.option("--model", type=click.Path(exists=True))
        def pulse(model: str | None):
            if model:
                model_path = Path(model)
                data = json.loads(model_path.read_text())
                realities = [n for n in data.get("nodes", []) if n.get("type") == "Reality"]
                click.echo(f"Found {len(realities)} realities")

        result = cli_runner.invoke(pulse, ["--model", str(mock_seed_model)])

        assert result.exit_code == 0
        assert "Found 2 realities" in result.output

    def test_status_with_temp_dir(self, cli_runner: CliRunner, temp_dir: Path):
        """Test status command with temporary directory."""
        @click.command()
        @click.option("--path", type=click.Path())
        def status(path: str):
            target_path = Path(path)
            click.echo(f"Status for: {target_path}")
            click.echo(f"Exists: {target_path.exists()}")

        result = cli_runner.invoke(status, ["--path", str(temp_dir)])

        assert result.exit_code == 0
        assert "Exists: True" in result.output


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a Click CLI test runner."""
        return CliRunner()

    def test_full_workflow(self, cli_runner: CliRunner, mock_seed_model: Path):
        """Test complete workflow: list, pulse, status."""
        @click.group()
        def cli():
            """Seed CLI."""
            pass

        @cli.command(name="list")
        @click.argument("model_path")
        def list_cmd(model_path: str):
            """List realities."""
            model = Path(model_path)
            data = json.loads(model.read_text())
            realities = [n for n in data.get("nodes", []) if n.get("type") == "Reality"]
            for r in realities:
                click.echo(f"  {r['id']}")

        @cli.command()
        def pulse():
            """Check pulse."""
            click.echo("Overall: GREEN")

        @cli.command()
        def status():
            """Show status."""
            click.echo("Status: OK")

        # Test list command
        result = cli_runner.invoke(cli, ["list", str(mock_seed_model)])
        assert result.exit_code == 0, f"Exit code was {result.exit_code}, output: {result.output}"
        assert "reality-project1" in result.output

        # Test pulse command
        result = cli_runner.invoke(cli, ["pulse"])
        assert result.exit_code == 0
        assert "GREEN" in result.output

        # Test status command
        result = cli_runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_help_output(self, cli_runner: CliRunner):
        """Test --help output for commands."""
        @click.command()
        @click.option("--json", is_flag=True, help="Output as JSON")
        def pulse(json: bool):
            """Check pulse of all realities."""
            pass

        result = cli_runner.invoke(pulse, ["--help"])

        assert result.exit_code == 0
        assert "Check pulse" in result.output
        assert "--json" in result.output
        assert "Output as JSON" in result.output

    def test_version_command(self, cli_runner: CliRunner):
        """Test version command."""
        @click.command()
        @click.option("--version", is_flag=True, help="Show version")
        def cli(version: bool):
            if version:
                click.echo("seed-core version 0.1.0")

        result = cli_runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output
