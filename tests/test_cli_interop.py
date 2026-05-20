import os
import sys
import json
import subprocess
from unittest import mock
import pytest

# Ensure the root and codes directories are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../codes")))

try:
    from codes.pipeline import run_pipeline, PipelineConfig, PipelineResult, _build_arg_parser, main
except ImportError:
    from pipeline import run_pipeline, PipelineConfig, PipelineResult, _build_arg_parser, main


def test_cli_help():
    """Verify that calling the pipeline CLI with --help returns successfully."""
    cmd = [sys.executable, "codes/pipeline.py", "--help"]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert res.returncode == 0
    assert "Paper2Code-Enhanced" in res.stdout


@mock.patch("codes.pipeline.subprocess.run")
@mock.patch("codes.pipeline.shutil.copy2")
@mock.patch("codes.pipeline.os.makedirs")
@mock.patch("codes.pipeline.init_db")
@mock.patch("codes.pipeline.create_run")
@mock.patch("codes.pipeline.complete_run")
@mock.patch("codes.pipeline.get_run_summary")
def test_run_pipeline_success(
    mock_get_summary, mock_complete, mock_create, mock_init, mock_makedirs, mock_copy, mock_sub_run
):
    """Test a successful full pipeline run with database metrics tracking."""
    mock_create.return_value = 42
    mock_get_summary.return_value = {
        "status": "completed",
        "total_cost": 0.05,
        "total_tokens_in": 1000,
        "total_tokens_out": 500,
    }

    config = PipelineConfig(
        paper_name="TestPaper",
        pdf_json_path="dummy.json",
        output_dir="dummy_out",
        output_repo_dir="dummy_repo",
        run_planning=True,
        run_analyzing=True,
        run_coding=True,
        run_debugging=False,
    )

    result = run_pipeline(config)

    # Assert database is initialized and run created
    mock_init.assert_called_once_with(quiet=True)
    mock_create.assert_called_once()
    mock_complete.assert_called_once_with(42, status="completed")

    # Assert subprocesses are run for planning, extract_config, analyzing, and coding stages
    assert mock_sub_run.call_count == 4  # 1_planning, 1.1_extract, 2_analyzing, 3_coding

    # Assert copy of config is called
    mock_copy.assert_called_once()

    # Assert PipelineResult contains mock SQLite DB metrics
    assert result.status == "success"
    assert result.run_id == 42
    assert result.cost_usd == 0.05
    assert result.tokens_in == 1000
    assert result.tokens_out == 500
    assert "planning" in result.stages_completed
    assert "analyzing" in result.stages_completed
    assert "coding" in result.stages_completed


@mock.patch("codes.pipeline.subprocess.run")
@mock.patch("codes.pipeline.init_db")
@mock.patch("codes.pipeline.create_run")
@mock.patch("codes.pipeline.complete_run")
def test_run_pipeline_stage_failure(mock_complete, mock_create, mock_init, mock_sub_run):
    """Verify that stage failures are caught and reported cleanly."""
    mock_create.return_value = 42
    # Make subprocess.run throw CalledProcessError on the planning stage
    mock_sub_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd="1_planning.py")

    config = PipelineConfig(
        paper_name="TestPaper",
        pdf_json_path="dummy.json",
        output_dir="dummy_out",
        output_repo_dir="dummy_repo",
        run_planning=True,
        run_analyzing=False,
        run_coding=False,
    )

    result = run_pipeline(config)

    assert result.status == "failed"
    assert result.run_id == 42
    assert "planning" in result.stages_failed
    assert "Stage 'planning' failed" in result.error
    mock_complete.assert_called_once_with(42, status="failed")


@mock.patch("sys.exit")
@mock.patch("codes.pipeline.subprocess.run")
@mock.patch("codes.pipeline.shutil.copy2")
@mock.patch("codes.pipeline.os.makedirs")
@mock.patch("codes.pipeline.init_db")
@mock.patch("codes.pipeline.create_run")
@mock.patch("codes.pipeline.complete_run")
@mock.patch("codes.pipeline.get_run_summary")
def test_main_cli_json_output(
    mock_get_summary, mock_complete, mock_create, mock_init, mock_makedirs, mock_copy, mock_sub_run, mock_exit
):
    """Verify that main() CLI parses arguments, isolates streams, and prints only JSON to stdout."""
    mock_create.return_value = 100
    mock_get_summary.return_value = {
        "status": "completed",
        "total_cost": 0.12,
        "total_tokens_in": 2500,
        "total_tokens_out": 1200,
    }

    test_args = [
        "pipeline.py",
        "--paper_name", "TestPaperCLI",
        "--pdf_json_path", "dummy.json",
        "--output_dir", "dummy_out",
        "--output_repo_dir", "dummy_repo",
        "--output-format", "json",
        "--stages", "planning,analyzing",
    ]

    with mock.patch("sys.argv", test_args):
        # Capture standard out and standard error during main() execution
        import io
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()

        with mock.patch("sys.stdout", captured_stdout), mock.patch("sys.stderr", captured_stderr):
            main()

        # Parse final output to ensure it is valid JSON and only contain PipelineResult
        stdout_content = captured_stdout.getvalue().strip()
        assert stdout_content.startswith("{")
        assert stdout_content.endswith("}")

        parsed_res = json.loads(stdout_content)
        assert parsed_res["stage"] == "pipeline"
        assert parsed_res["status"] == "success"
        assert parsed_res["run_id"] == 100
        assert parsed_res["cost_usd"] == 0.12
        assert parsed_res["tokens"]["in"] == 2500
        assert parsed_res["stages_completed"] == ["planning", "analyzing"]

        # Ensure sys.exit is called with 0 (since it was a success)
        mock_exit.assert_called_once_with(0)
