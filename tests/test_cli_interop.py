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


@mock.patch("codes.pipeline.load_stage_module")
@mock.patch("codes.pipeline.shutil.copy2")
@mock.patch("codes.pipeline.os.makedirs")
@mock.patch("codes.pipeline.init_db")
@mock.patch("codes.pipeline.create_run")
@mock.patch("codes.pipeline.complete_run")
@mock.patch("codes.pipeline.get_run_summary")
def test_run_pipeline_success(
    mock_get_summary, mock_complete, mock_create, mock_init, mock_makedirs, mock_copy, mock_load_stage
):
    """Test a successful full pipeline run with database metrics tracking."""
    mock_create.return_value = 42
    mock_get_summary.return_value = {
        "status": "completed",
        "total_cost": 0.05,
        "total_tokens_in": 1000,
        "total_tokens_out": 500,
    }

    mock_stage = mock.MagicMock()
    mock_load_stage.return_value = mock_stage

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

    # Assert stage modules are loaded
    assert mock_load_stage.call_count == 4  # 1_planning, 1.1_extract, 2_analyzing, 3_coding

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


@mock.patch("codes.pipeline.load_stage_module")
@mock.patch("codes.pipeline.init_db")
@mock.patch("codes.pipeline.create_run")
@mock.patch("codes.pipeline.complete_run")
def test_run_pipeline_stage_failure(mock_complete, mock_create, mock_init, mock_load_stage):
    """Verify that stage failures are caught and reported cleanly."""
    mock_create.return_value = 42
    # Make planning.run_stage throw an exception
    mock_stage = mock.MagicMock()
    mock_stage.run_stage.side_effect = Exception("Stage failed")
    mock_load_stage.return_value = mock_stage

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
@mock.patch("codes.pipeline.load_stage_module")
@mock.patch("codes.pipeline.shutil.copy2")
@mock.patch("codes.pipeline.os.makedirs")
@mock.patch("codes.pipeline.init_db")
@mock.patch("codes.pipeline.create_run")
@mock.patch("codes.pipeline.complete_run")
@mock.patch("codes.pipeline.get_run_summary")
def test_main_cli_json_output(
    mock_get_summary, mock_complete, mock_create, mock_init, mock_makedirs, mock_copy, mock_load_stage, mock_exit
):
    """Verify that main() CLI parses arguments, isolates streams, and prints only JSON to stdout."""
    mock_create.return_value = 100
    mock_get_summary.return_value = {
        "status": "completed",
        "total_cost": 0.12,
        "total_tokens_in": 2500,
        "total_tokens_out": 1200,
    }

    mock_stage = mock.MagicMock()
    mock_load_stage.return_value = mock_stage

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


def test_planning_run_stage():
    import importlib.util
    spec = importlib.util.spec_from_file_location("planning", "codes/1_planning.py")
    planning = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(planning)
    
    with mock.patch.object(planning, "unified_api_call") as mock_api, \
         mock.patch.object(planning, "write_stage_result") as mock_write_stage, \
         mock.patch.object(planning, "init_db") as mock_init_db, \
         mock.patch.object(planning, "create_run") as mock_create_run:
         
        mock_create_run.return_value = 42
        mock_response = mock.MagicMock()
        mock_response.choices = [mock.MagicMock(message=mock.MagicMock(role="assistant", content="mock response content"))]
        mock_response.model_dump_json.return_value = '{"choices": [{"message": {"role": "assistant", "content": "mock response content"}}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}}'
        mock_api.return_value = mock_response
        
        config = mock.MagicMock()
        config.paper_name = "Attention Is All You Need"
        config.model = "MiniMax-M2.7"
        config.paper_format = "JSON"
        config.pdf_json_path = "dummy.json"
        config.output_dir = "dummy_out"
        config.run_id = 42

        file_data = {
            "dummy.json": '{"title": "mock"}',
            "planning_config.yaml": "learning_rate: 0.01",
            "planning_trajectories.json": "[]",
        }
        def custom_open(filename, *args, **kwargs):
            for k, v in file_data.items():
                if k in filename:
                    return mock.mock_open(read_data=v).return_value
            return mock.mock_open(read_data="{}").return_value

        with mock.patch("builtins.open", custom_open):
            try:
                planning.run_stage(config)
            except AttributeError:
                pytest.fail("planning module has no run_stage function")
        
        assert mock_api.call_count >= 1
        assert mock_write_stage.call_count >= 1


def test_extract_config_run_stage():
    import importlib.util
    spec = importlib.util.spec_from_file_location("extract_config", "codes/1.1_extract_config.py")
    extract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extract)
    
    config = mock.MagicMock()
    config.paper_name = "Attention Is All You Need"
    config.output_dir = "dummy_out"
    
    with mock.patch("builtins.open", mock.mock_open(read_data=r'[{"choices": [{"message": {"content": "```yaml\nlearning_rate: 0.01\n```"}}]}]')), \
         mock.patch.object(extract, "extract_planning") as mock_extract, \
         mock.patch.object(extract, "content_to_json") as mock_content, \
         mock.patch.object(extract, "format_json_data") as mock_fmt, \
         mock.patch.object(extract.shutil, "copy"), \
         mock.patch.object(extract.os, "makedirs"):
        
        mock_extract.return_value = ["overall", "arch", "logic"]
        mock_content.return_value = {}
        mock_fmt.return_value = "{}"
        
        try:
            extract.run_stage(config)
        except AttributeError:
            pytest.fail("extract_config module has no run_stage function")


def test_analyzing_run_stage():
    import importlib.util
    spec = importlib.util.spec_from_file_location("analyzing", "codes/2_analyzing.py")
    analyzing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzing)
    
    with mock.patch.object(analyzing, "unified_api_call") as mock_api, \
         mock.patch.object(analyzing, "write_stage_result") as mock_write_stage, \
         mock.patch.object(analyzing, "init_db") as mock_init_db:
         
        mock_response = mock.MagicMock()
        mock_response.choices = [mock.MagicMock(message=mock.MagicMock(role="assistant", content="mock analysis response"))]
        mock_response.model_dump_json.return_value = '{"choices": [{"message": {"role": "assistant", "content": "mock analysis response"}}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}}'
        mock_api.return_value = mock_response
        
        config = mock.MagicMock()
        config.paper_name = "Attention Is All You Need"
        config.model = "MiniMax-M2.7"
        config.paper_format = "JSON"
        config.pdf_json_path = "dummy.json"
        config.output_dir = "dummy_out"
        config.run_id = 42
        
        file_data = {
            "dummy.json": '{"title": "mock"}',
            "planning_config.yaml": "learning_rate: 0.01",
            "planning_trajectories.json": "[]",
        }
        def custom_open(filename, *args, **kwargs):
            for k, v in file_data.items():
                if k in filename:
                    return mock.mock_open(read_data=v).return_value
            return mock.mock_open(read_data="{}").return_value

        with mock.patch("builtins.open", custom_open), \
             mock.patch.object(analyzing, "extract_planning") as mock_extract, \
             mock.patch.object(analyzing, "content_to_json") as mock_content, \
             mock.patch.object(analyzing, "load_accumulated_cost") as mock_load, \
             mock.patch.object(analyzing.os.path, "exists") as mock_exists:
            
            mock_extract.return_value = ["overall", "arch", "logic"]
            mock_content.return_value = {"Task list": ["dataset.py"], "Logic Analysis": [["dataset.py", "load data"]]}
            mock_exists.return_value = False
            mock_load.return_value = 0.0
            
            try:
                analyzing.run_stage(config)
            except AttributeError:
                pytest.fail("analyzing module has no run_stage function")
            assert mock_api.call_count >= 1


def test_coding_run_stage():
    import importlib.util
    spec = importlib.util.spec_from_file_location("coding", "codes/3_coding.py")
    coding = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coding)
    
    with mock.patch.object(coding, "unified_api_call") as mock_api, \
         mock.patch.object(coding, "write_stage_result") as mock_write_stage, \
         mock.patch.object(coding, "init_db") as mock_init_db:
         
        mock_response = mock.MagicMock()
        mock_response.choices = [mock.MagicMock(message=mock.MagicMock(role="assistant", content="mock code output"))]
        mock_response.model_dump_json.return_value = '{"choices": [{"message": {"role": "assistant", "content": "mock code output"}}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}}'
        mock_api.return_value = mock_response
        
        config = mock.MagicMock()
        config.paper_name = "Attention Is All You Need"
        config.model = "MiniMax-M2.7"
        config.paper_format = "JSON"
        config.pdf_json_path = "dummy.json"
        config.output_dir = "dummy_out"
        config.output_repo_dir = "dummy_repo"
        config.run_id = 42
        
        file_data = {
            "dummy.json": '{"title": "mock"}',
            "planning_config.yaml": "learning_rate: 0.01",
            "planning_trajectories.json": "[]",
            "dataset.py_simple_analysis_response.json": '[{"choices": [{"message": {"content": "mock logic content"}}]}]',
        }
        def custom_open(filename, *args, **kwargs):
            for k, v in file_data.items():
                if k in filename:
                    return mock.mock_open(read_data=v).return_value
            return mock.mock_open(read_data="{}").return_value

        with mock.patch("builtins.open", custom_open), \
             mock.patch.object(coding, "extract_planning") as mock_extract, \
             mock.patch.object(coding, "load_accumulated_cost") as mock_load, \
             mock.patch.object(coding, "content_to_json") as mock_content:
            
            mock_extract.return_value = ["overall", "arch", "logic"]
            mock_content.return_value = {"Task list": ["dataset.py"]}
            mock_load.return_value = 0.0
            
            try:
                coding.run_stage(config)
            except AttributeError:
                pytest.fail("coding module has no run_stage function")
            assert mock_api.call_count >= 1


def test_debugging_run_stage():
    import importlib.util
    spec = importlib.util.spec_from_file_location("debugging", "codes/4_debugging.py")
    debugging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(debugging)
    
    with mock.patch.object(debugging, "unified_api_call") as mock_api, \
         mock.patch.object(debugging, "write_execution_trial") as mock_write_trial, \
         mock.patch.object(debugging, "init_db") as mock_init_db, \
         mock.patch.object(debugging, "complete_run") as mock_complete_run:
         
        mock_response = mock.MagicMock()
        mock_response.choices = [mock.MagicMock(message=mock.MagicMock(role="assistant", content="mock debugging fix code"))]
        mock_response.model_dump_json.return_value = '{"choices": [{"message": {"role": "assistant", "content": "mock debugging fix code"}}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}}'
        mock_api.return_value = mock_response
        
        config = mock.MagicMock()
        config.paper_name = "Attention Is All You Need"
        config.model = "MiniMax-M2.7"
        config.output_dir = "dummy_out"
        config.output_repo_dir = "dummy_repo"
        config.error_file_path = "dummy_err.txt"
        config.debug_save_num = 1
        config.run_id = 42
        
        file_data = {
            "dummy_err.txt": "dummy trace",
            "planning_trajectories.json": "[]",
            "config.yaml": "learning_rate: 0.01",
            "reproduce.sh": "python main.py",
        }
        def custom_open(filename, *args, **kwargs):
            for k, v in file_data.items():
                if k in filename:
                    return mock.mock_open(read_data=v).return_value
            return mock.mock_open(read_data="{}").return_value

        with mock.patch("builtins.open", custom_open), \
             mock.patch.object(debugging, "get_executor") as mock_exec, \
             mock.patch.object(debugging.os.path, "exists") as mock_exists, \
             mock.patch.object(debugging, "extract_planning") as mock_extract, \
             mock.patch.object(debugging, "content_to_json") as mock_content, \
             mock.patch.object(debugging, "read_python_files") as mock_read:
            
            mock_exists.return_value = True
            mock_extract.return_value = ["overall", "arch", "logic"]
            mock_content.return_value = {"Task list": ["dataset.py"]}
            mock_read.return_value = {"dataset.py": "class Dataset:"}
            
            executor = mock.MagicMock()
            executor.run.side_effect = [
                mock.MagicMock(success=False, returncode=1, stdout="", stderr="Error trace", elapsed_seconds=1.2, timed_out=False),
                mock.MagicMock(success=True, returncode=0, stdout="", stderr="", elapsed_seconds=1.2, timed_out=False)
            ]
            mock_exec.return_value = executor
            
            try:
                debugging.run_stage(config)
            except AttributeError:
                pytest.fail("debugging module has no run_stage function")
            assert mock_api.call_count >= 1



