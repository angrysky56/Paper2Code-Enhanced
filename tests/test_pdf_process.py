import os
import sys
import json
import pytest
from unittest import mock
from pypdf import PdfWriter

# Ensure the root and codes directories are in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../codes")))

import importlib.util

dir_path = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.abspath(os.path.join(dir_path, "../codes/0_pdf_process.py"))
spec = importlib.util.spec_from_file_location("pdf_process", file_path)
pdf_process = importlib.util.module_from_spec(spec)
sys.modules["pdf_process"] = pdf_process
spec.loader.exec_module(pdf_process)


def test_remove_spans():
    """Verify that remove_spans correctly recursively removes citation noise keys."""
    dirty_data = {
        "cite_spans": [1, 2, 3],
        "ref_spans": [],
        "authors": [{"name": "Author"}],
        "paper_id": "123",
        "body_text": [
            {
                "text": "Hello",
                "eq_spans": [4, 5],
            }
        ]
    }
    
    cleaned = pdf_process.remove_spans(dirty_data)
    
    assert "cite_spans" not in cleaned
    assert "ref_spans" not in cleaned
    assert "authors" not in cleaned
    assert cleaned["paper_id"] == "123"
    assert "eq_spans" not in cleaned["body_text"][0]
    assert cleaned["body_text"][0]["text"] == "Hello"


def test_process_legacy_json(tmp_path):
    """Test process_legacy_json successfully loads, cleans, and saves a JSON file."""
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"
    
    dirty_data = {
        "cite_spans": [1, 2],
        "title": "Legacy Test Paper",
        "body_text": [{"text": "Main body text", "bib_entries": {}}]
    }
    
    with open(input_file, "w") as f:
        json.dump(dirty_data, f)
        
    pdf_process.process_legacy_json(str(input_file), str(output_file))
    
    assert output_file.exists()
    with open(output_file) as f:
        cleaned_data = json.load(f)
        
    assert "cite_spans" not in cleaned_data
    assert "bib_entries" not in cleaned_data["body_text"][0]
    assert cleaned_data["title"] == "Legacy Test Paper"


def test_process_pdf_local(tmp_path):
    """Verify that process_pdf_local extracts pages from a valid PDF file using pypdf."""
    pdf_file = tmp_path / "dummy.pdf"
    
    # Create a minimal blank PDF using pypdf
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)  # US Letter size
    writer.add_blank_page(width=612, height=792)
    
    with open(pdf_file, "wb") as f:
        writer.write(f)
        
    pages = pdf_process.process_pdf_local(str(pdf_file))
    
    assert len(pages) == 2
    assert pages[0]["page_num"] == 1
    assert pages[1]["page_num"] == 2


def test_process_pdf_vlm(tmp_path):
    """Verify process_pdf_vlm calls the unified API and returns refined text."""
    pdf_file = tmp_path / "dummy.pdf"
    
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(pdf_file, "wb") as f:
        writer.write(f)
        
    # Mocking pypdf layout extraction to return some dummy raw text
    with mock.patch.object(pdf_process, "process_pdf_local") as mock_local:
        mock_local.return_value = [{"text": "Raw Text Page 1", "page_num": 1}]
        
        # Mock the API completion
        mock_completion = mock.MagicMock()
        mock_completion.model_dump_json.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": "Refined LaTeX Math $E=mc^2$ Page 1"
                }
            }]
        })
        
        with mock.patch.object(pdf_process, "unified_api_call", return_value=mock_completion) as mock_api_call:
            pages = pdf_process.process_pdf_vlm(str(pdf_file))
            
            assert len(pages) == 1
            assert pages[0]["page_num"] == 1
            assert "Refined LaTeX Math" in pages[0]["text"]
            assert "$E=mc^2$" in pages[0]["text"]
            mock_api_call.assert_called_once()


def test_process_pdf_olmocr_success(tmp_path):
    """Verify that process_pdf_olmocr invokes the command and loads markdown outputs."""
    pdf_file = tmp_path / "dummy.pdf"
    workspace_dir = tmp_path / "olmocr_workspace"
    results_dir = workspace_dir / "results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Create a mock markdown result file
    with open(results_dir / "page_1.md", "w") as f:
        f.write("# Page 1 Markdown from olmOCR")
        
    mock_sub_run = mock.MagicMock(returncode=0)
    with mock.patch.object(pdf_process.subprocess, "run", return_value=mock_sub_run) as mock_run:
        pages = pdf_process.process_pdf_olmocr(str(pdf_file), str(tmp_path))
        
        assert pages is not None
        assert len(pages) == 1
        assert pages[0]["text"] == "# Page 1 Markdown from olmOCR"
        assert pages[0]["page_num"] == 1
        mock_run.assert_called_once()


def test_main_direct_routing_json(tmp_path):
    """Verify that main routes legacy JSON files to process_legacy_json."""
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"
    
    with open(input_file, "w") as f:
        json.dump({"cite_spans": [], "title": "Test JSON"}, f)
        
    from types import SimpleNamespace
    args = SimpleNamespace(
        input_json_path=str(input_file),
        output_json_path=str(output_file),
        mode="auto",
        gpt_version="gpt-4o",
        paper_name=None
    )
    
    pdf_process.main(args)
    
    assert output_file.exists()
    with open(output_file) as f:
        data = json.load(f)
    assert "cite_spans" not in data
    assert data["title"] == "Test JSON"


def test_main_direct_routing_pdf(tmp_path):
    """Verify main routes PDF files to process_pdf_local and constructs S2ORC schema."""
    pdf_file = tmp_path / "paper.pdf"
    output_file = tmp_path / "output.json"
    
    with mock.patch.object(pdf_process, "process_pdf_local") as mock_local:
        mock_local.return_value = [
            {"text": "Abstract\nThis is a paper.\n1 Introduction", "page_num": 1}
        ]
        
        from types import SimpleNamespace
        args = SimpleNamespace(
            input_json_path=str(pdf_file),
            output_json_path=str(output_file),
            mode="local",
            gpt_version="gpt-4o",
            paper_name="test_paper"
        )
        
        pdf_process.main(args)
        
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
            
        assert data["paper_id"] == "test_paper"
        assert "pdf_parse" in data
        assert data["pdf_parse"]["paper_id"] == "test_paper"
        assert len(data["pdf_parse"]["body_text"]) == 1
        assert data["pdf_parse"]["body_text"][0]["section"] == "Page 1"


@mock.patch("codes.pipeline.load_stage_module")
@mock.patch("codes.pipeline.init_db")
@mock.patch("codes.pipeline.create_run")
@mock.patch("codes.pipeline.complete_run")
@mock.patch("codes.pipeline.get_run_summary")
def test_pipeline_pdf_routing(
    mock_get_summary, mock_complete, mock_create, mock_init, mock_load_stage, tmp_path
):
    """Verify that pipeline.py intercepts a PDF file, calls pdf_process, and overrides the config."""
    from codes.pipeline import run_pipeline, PipelineConfig

    mock_create.return_value = 100
    mock_get_summary.return_value = {"status": "completed"}

    mock_stage = mock.MagicMock()
    
    def side_effect(name, filename):
        if name == "0_pdf_process":
            return pdf_process
        return mock_stage
    mock_load_stage.side_effect = side_effect

    pdf_file = tmp_path / "test_paper.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(pdf_file, "wb") as f:
        writer.write(f)

    config = PipelineConfig(
        paper_name="test_paper",
        pdf_json_path=str(pdf_file),
        output_dir=str(tmp_path / "out"),
        output_repo_dir=str(tmp_path / "repo"),
        run_planning=True,
        run_analyzing=False,
        run_coding=False,
        run_debugging=False,
    )

    result = run_pipeline(config)

    assert result.status == "success"
    # Ensure config.pdf_json_path has been overridden to the compiled JSON path
    assert config.pdf_json_path.endswith("test_paper_cleaned.json")
    assert os.path.exists(config.pdf_json_path)

    # Let's verify the file content is structured cleanly in S2ORC schema
    with open(config.pdf_json_path) as f:
        data = json.load(f)
    assert data["paper_id"] == "test_paper"
    assert "pdf_parse" in data

