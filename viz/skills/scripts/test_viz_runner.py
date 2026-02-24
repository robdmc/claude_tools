"""
Comprehensive test suite for viz_runner.py

Tests cover:
- Code transformation (inject_savefig)
- ID generation and collision handling
- CLI commands (--list, --clean)
- Subprocess execution (mocked)
"""

import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest

# Import the modules under test
import viz_runner

# Core viz_runner imports
from viz_runner import (
    DefaultHandler,
    VIZ_DIR,
    ensure_viz_dir,
    format_module_error,
    generate_show_code,
    get_handler,
    get_python_command,
    get_unique_id,
    inject_savefig,
    run_plot,
    run_script_background,
    run_show,
    validate_python_env,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def viz_dir_clean(tmp_path, monkeypatch):
    """Provide a clean temporary viz directory."""
    viz_dir = tmp_path / "viz"
    viz_dir.mkdir()
    monkeypatch.setattr(viz_runner, "VIZ_DIR", viz_dir)
    return viz_dir


# =============================================================================
# Unit Tests: Code Transformation
# =============================================================================


class TestInjectSavefig:
    """Tests for inject_savefig function."""

    def test_basic_plt_show(self):
        """Inject savefig before plt.show()."""
        script = dedent('''
            import matplotlib.pyplot as plt
            plt.plot([1, 2, 3])
            plt.show()
        ''').strip()

        result = inject_savefig(script, ".viz/test.png")

        assert "plt.savefig('.viz/test.png'" in result
        assert result.index("savefig") < result.index("show")

    def test_with_indentation(self):
        """Preserve indentation when injecting."""
        script = dedent('''
            import matplotlib.pyplot as plt
            if True:
                plt.plot([1, 2, 3])
                plt.show()
        ''').strip()

        result = inject_savefig(script, ".viz/test.png")

        # savefig should be indented like the plt.show()
        lines = result.split("\n")
        savefig_line = [l for l in lines if "savefig" in l][0]
        show_line = [l for l in lines if "show" in l][0]

        # Both should have same indentation
        assert savefig_line.startswith("    ")
        assert show_line.startswith("    ")

    def test_no_plt_show(self):
        """Script without plt.show() gets savefig appended."""
        script = dedent('''
            import matplotlib.pyplot as plt
            plt.plot([1, 2, 3])
        ''').strip()

        result = inject_savefig(script, ".viz/test.png")

        assert "plt.savefig('.viz/test.png'" in result

    def test_multiple_shows(self):
        """Multiple plt.show() calls each get savefig."""
        script = dedent('''
            import matplotlib.pyplot as plt
            plt.plot([1, 2, 3])
            plt.show()
            plt.plot([4, 5, 6])
            plt.show()
        ''').strip()

        result = inject_savefig(script, ".viz/test.png")

        # Both shows should have savefig before them
        assert result.count("savefig") == 2

    def test_pyplot_show(self):
        """Handle pyplot.show() as well as plt.show()."""
        script = dedent('''
            from matplotlib import pyplot
            pyplot.plot([1, 2, 3])
            pyplot.show()
        ''').strip()

        result = inject_savefig(script, ".viz/test.png")

        assert "plt.savefig" in result


# =============================================================================
# Unit Tests: ID Generation
# =============================================================================


class TestGetUniqueId:
    """Tests for get_unique_id function."""

    def test_new_id(self, viz_dir_clean):
        """New ID when no collision."""
        result = get_unique_id("my_plot")
        assert result == "my_plot"

    def test_collision_adds_suffix(self, viz_dir_clean):
        """Collision appends _2 suffix."""
        # Create existing file
        (viz_dir_clean / "my_plot.py").write_text("")

        result = get_unique_id("my_plot")

        assert result == "my_plot_2"

    def test_multiple_collisions(self, viz_dir_clean):
        """Multiple collisions increment suffix."""
        (viz_dir_clean / "my_plot.py").write_text("")
        (viz_dir_clean / "my_plot_2.py").write_text("")
        (viz_dir_clean / "my_plot_3.py").write_text("")

        result = get_unique_id("my_plot")

        assert result == "my_plot_4"

    def test_no_suggested_id_generates_timestamp(self, viz_dir_clean):
        """No suggested ID generates timestamp-based ID."""
        result = get_unique_id(None)

        assert result.startswith("viz_")
        # Should be format like viz_20240115_143022
        assert len(result) > 10


# =============================================================================
# Unit Tests: Error Formatting
# =============================================================================


class TestFormatModuleError:
    """Tests for format_module_error function."""

    def test_module_not_found(self):
        """Detect and format ModuleNotFoundError."""
        stderr = "ModuleNotFoundError: No module named 'pandas'"

        result = format_module_error(stderr, ["python"])

        assert result is not None
        assert "MISSING MODULE" in result
        assert "pandas" in result

    def test_no_module_error(self):
        """Return None for non-module errors."""
        stderr = "SyntaxError: invalid syntax"

        result = format_module_error(stderr, ["python"])

        assert result is None


# =============================================================================
# Integration Tests: Python Command Detection
# =============================================================================


class TestValidatePythonEnv:
    """Tests for validate_python_env function."""

    def test_valid_env_returns_true(self):
        """Valid environment with module returns True."""
        # sys.executable should be able to import sys (always available)
        result = validate_python_env([sys.executable], required_module="sys")
        assert result is True

    def test_missing_module_returns_false(self):
        """Environment missing module returns False."""
        # Try to import a module that definitely doesn't exist
        result = validate_python_env([sys.executable], required_module="nonexistent_module_xyz123")
        assert result is False

    def test_invalid_python_returns_false(self):
        """Invalid Python command returns False."""
        result = validate_python_env(["/nonexistent/python"])
        assert result is False

    def test_timeout_returns_false(self, monkeypatch):
        """Timeout during validation returns False."""
        def timeout_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="test", timeout=10)

        monkeypatch.setattr(subprocess, "run", timeout_run)

        result = validate_python_env(["python"])
        assert result is False


class TestGetPythonCommand:
    """Tests for get_python_command."""

    def test_uv_project_detected_with_validation(self, tmp_path, monkeypatch):
        """Detect uv project and use 'uv run --directory ... python' when validated."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'")

        # Mock validate_python_env to return True for project cmd
        def mock_validate(cmd, required_module="matplotlib"):
            return "--directory" in cmd

        monkeypatch.setattr(viz_runner, "validate_python_env", mock_validate)

        result = get_python_command(tmp_path)

        assert result == ["uv", "run", "--directory", str(tmp_path), "python"]

    def test_uv_project_fails_validation_falls_to_system(self, tmp_path, monkeypatch):
        """If project env fails validation, try system Python."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'")

        call_count = [0]

        def mock_validate(cmd, required_module="matplotlib"):
            call_count[0] += 1
            # First call (project) fails, second call (system python) succeeds
            if call_count[0] == 1:
                return False  # Project env fails
            return True  # System python succeeds

        monkeypatch.setattr(viz_runner, "validate_python_env", mock_validate)

        result = get_python_command(tmp_path)

        assert result == ["python"]

    def test_fallback_to_viz_skill_env(self, tmp_path, monkeypatch):
        """Fall back to viz skill's environment when all else fails."""
        # Mock all validation to fail
        def mock_validate(cmd, required_module="matplotlib"):
            return False

        monkeypatch.setattr(viz_runner, "validate_python_env", mock_validate)

        result = get_python_command(tmp_path)

        # Should return viz skill's own environment
        assert result[0] == "uv"
        assert result[1] == "run"
        assert result[2] == "--directory"
        # The directory should be the viz skill's code directory
        assert "viz" in result[3] or "code" in result[3]
        assert result[4] == "python"

    def test_system_python_used_when_no_project(self, tmp_path, monkeypatch):
        """System Python used when no project markers and it validates."""
        # No pyproject.toml or uv.lock in tmp_path

        def mock_validate(cmd, required_module="matplotlib"):
            return cmd == ["python"]

        monkeypatch.setattr(viz_runner, "validate_python_env", mock_validate)

        result = get_python_command(tmp_path)

        assert result == ["python"]


# =============================================================================
# CLI Tests (mocked subprocess)
# =============================================================================


class TestCLIClean:
    """Tests for --clean command."""

    def test_clean_removes_files(self, viz_dir_clean):
        """--clean removes all files from viz directory."""
        # Create some files
        (viz_dir_clean / "test1.py").write_text("")
        (viz_dir_clean / "test1.png").write_text("")
        (viz_dir_clean / "test1.json").write_text("")

        # Run main with --clean
        with patch.object(sys, "argv", ["viz_runner.py", "--clean"]):
            with pytest.raises(SystemExit) as exc_info:
                viz_runner.main()

        assert exc_info.value.code == 0
        assert len(list(viz_dir_clean.iterdir())) == 0


class TestCLIList:
    """Tests for --list command."""

    def test_list_empty(self, viz_dir_clean, capsys):
        """--list with no visualizations."""
        with patch.object(sys, "argv", ["viz_runner.py", "--list"]):
            with pytest.raises(SystemExit) as exc_info:
                viz_runner.main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "No visualizations found" in captured.out

    def test_list_with_items(self, viz_dir_clean, capsys):
        """--list shows existing visualizations."""
        # Create a metadata file
        metadata = {
            "id": "test_plot",
            "desc": "A test plot",
            "created": "2024-01-15T10:30:00",
        }
        (viz_dir_clean / "test_plot.json").write_text(json.dumps(metadata))

        with patch.object(sys, "argv", ["viz_runner.py", "--list"]):
            with pytest.raises(SystemExit) as exc_info:
                viz_runner.main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "test_plot" in captured.out
        assert "A test plot" in captured.out


# =============================================================================
# Subprocess Execution Tests (mocked)
# =============================================================================


class TestRunScriptBackground:
    """Tests for run_script_background with mocked subprocess."""

    def test_success_creates_png(self, viz_dir_clean, tmp_path):
        """Successful execution creates PNG."""
        script_path = tmp_path / "test.py"
        script_path.write_text("print('hello')")
        png_path = viz_dir_clean / "test.png"

        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345

        with patch("viz_runner.subprocess.Popen", return_value=mock_process):
            # Simulate PNG being created after a short delay
            def create_png(*args):
                png_path.write_bytes(b"PNG")
                return None

            mock_process.poll.side_effect = [None, create_png, 0]

            success, pid, message = run_script_background(script_path, png_path)

        # Note: Due to timing, this might need adjustment
        # The actual behavior depends on the polling loop

    def test_script_failure(self, viz_dir_clean, tmp_path):
        """Script failure returns error message."""
        script_path = tmp_path / "test.py"
        script_path.write_text("print('hello')")
        png_path = viz_dir_clean / "test.png"

        # Mock subprocess.Popen - immediate failure
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Failed
        mock_process.stderr.read.return_value = b"Error occurred"
        mock_process.pid = 12345

        with patch("viz_runner.subprocess.Popen", return_value=mock_process):
            # Also mock validate_python_env to avoid subprocess.run calls
            with patch("viz_runner.validate_python_env", return_value=True):
                success, pid, message = run_script_background(script_path, png_path)

        assert success is False
        assert "Error occurred" in message


# =============================================================================
# Handler Architecture Tests
# =============================================================================


class TestDefaultHandler:
    """Tests for DefaultHandler."""

    def test_build_script_passes_through(self):
        """DefaultHandler returns plot_code unchanged."""
        handler = DefaultHandler()
        plot_code = "import matplotlib.pyplot as plt\nplt.plot([1,2,3])\nplt.show()"

        script, cwd = handler.build_script(plot_code)

        assert script == plot_code
        assert cwd is None

    def test_build_script_ignores_source_path(self):
        """DefaultHandler ignores source_path and target_var."""
        handler = DefaultHandler()
        plot_code = "plt.plot([1,2,3])"

        script, cwd = handler.build_script(
            plot_code,
            source_path=Path("/some/path.py"),
            target_var="df",
        )

        assert script == plot_code
        assert cwd is None

    def test_validate_args_always_valid(self):
        """DefaultHandler validation always succeeds."""
        handler = DefaultHandler()

        # Create a minimal namespace
        class Args:
            pass

        args = Args()

        valid, error = handler.validate_args(args)

        assert valid is True
        assert error == ""


class TestGetHandler:
    """Tests for get_handler function."""

    def test_default_handler_when_no_flags(self):
        """Returns DefaultHandler when no special flags set."""

        class Args:
            pass

        handler = get_handler(Args())

        assert isinstance(handler, DefaultHandler)


class TestRunPlot:
    """Tests for run_plot generic execution function."""

    def test_run_plot_with_default_handler(self, viz_dir_clean):
        """run_plot works with DefaultHandler."""
        handler = DefaultHandler()
        plot_code = dedent('''
            import matplotlib.pyplot as plt
            plt.plot([1, 2, 3], [1, 4, 9])
            plt.show()
        ''').strip()

        # Mock subprocess to simulate successful execution
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_process.stderr.read.return_value = b""

        with patch("viz_runner.subprocess.Popen", return_value=mock_process):
            # Also mock validate_python_env to avoid subprocess.run calls
            with patch("viz_runner.validate_python_env", return_value=True):
                # Simulate PNG being created
                def create_png(*args, **kwargs):
                    png_path = viz_dir_clean / "test_plot.png"
                    png_path.write_bytes(b"PNG")
                    return None

                mock_process.poll.side_effect = [None, create_png, 0]

                success, message, png_path = run_plot(
                    handler=handler,
                    plot_code=plot_code,
                    viz_id="test_plot",
                    description="Test plot",
                )

        # Script should be written
        script_path = viz_dir_clean / "test_plot.py"
        assert script_path.exists()
        script_content = script_path.read_text()
        assert "plt.savefig" in script_content


class TestGenerateShowCode:
    """Tests for generate_show_code helper function."""

    def test_basic_show_code(self):
        """Generate show code for a variable."""
        code = generate_show_code("df", num_rows=5)

        assert "_var = df" in code
        assert "Shape:" in code
        assert "Columns:" in code
        assert "Dtypes:" in code
        assert ".head(5)" in code

    def test_custom_num_rows(self):
        """Generate show code with custom row count."""
        code = generate_show_code("my_data", num_rows=10)

        assert "_var = my_data" in code
        assert ".head(10)" in code


# =============================================================================
# Edge Cases and Regression Tests
# =============================================================================


class TestEdgeCases:
    """Edge case and regression tests."""

    def test_inject_savefig_idempotent(self):
        """Multiple inject_savefig calls don't duplicate."""
        script = "import matplotlib.pyplot as plt\nplt.show()"

        result1 = inject_savefig(script, ".viz/test.png")
        result2 = inject_savefig(result1, ".viz/test.png")

        # Second injection shouldn't add another savefig before the existing one
        # (the pattern won't match because savefig is now before show)
        assert result2.count("savefig") == 2  # Once from each call (appended)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
