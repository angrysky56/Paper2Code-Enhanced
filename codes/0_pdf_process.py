import argparse
import json
import os
import re
import subprocess
import sys

# Ensure the codes directory is in sys.path so we can import utils safely
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from utils import unified_api_call
except ImportError:
    unified_api_call = None


def remove_spans(data):
    """
    Original legacy cleaner for s2orc-doc2json Grobid outputs.
    Recursively removes noise keys like spans, author details, bib entries, and hashes.
    """
    if isinstance(data, dict):
        for key in [
            "cite_spans",
            "ref_spans",
            "eq_spans",
            "authors",
            "bib_entries",
            "year",
            "venue",
            "identifiers",
            "_pdf_hash",
            "header",
        ]:
            data.pop(key, None)
        for key, value in data.items():
            data[key] = remove_spans(value)
    elif isinstance(data, list):
        return [remove_spans(item) for item in data]
    return data


def process_legacy_json(input_json_path, output_json_path):
    """Loads a Grobid-processed JSON, cleans it, and saves it."""
    print(f"[PREPROCESS] Loading legacy JSON: {input_json_path}")
    with open(input_json_path) as f:
        data = json.load(f)

    cleaned_data = remove_spans(data)

    print(f"[SAVED] Cleaned legacy JSON to {output_json_path}")
    with open(output_json_path, "w") as f:
        json.dump(cleaned_data, f)


def process_pdf_local(pdf_path):
    """
    Robust local text extractor using pypdf.
    Zero outside binary dependencies. Extracts structured layout-aware text page-by-page.
    """
    print(f"[PREPROCESS] Processing PDF locally with pypdf: {pdf_path}")
    try:
        from pypdf import PdfReader
    except ImportError:
        print("[ERROR] pypdf library is required for PDF parsing. Please install it using 'uv pip install pypdf'.")
        sys.exit(1)

    reader = PdfReader(pdf_path)
    pages = []

    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({
            "text": text.strip(),
            "page_num": idx + 1
        })

    return pages


def process_pdf_vlm(pdf_path, gpt_version="MiniMax-M2.7"):
    """
    Leverages Vision-Language Models (VLMs) via API to restructure raw extracted text
    into high-fidelity Markdown, native LaTeX mathematical formulas, and clean HTML tables.
    """
    print(f"[PREPROCESS] Processing PDF with VLM support ({gpt_version}): {pdf_path}")
    if not unified_api_call:
        print("[WARNING] utils.unified_api_call not available. Falling back to local text extraction.")
        return process_pdf_local(pdf_path)

    # First extract text using local pypdf
    raw_pages = process_pdf_local(pdf_path)
    refined_pages = []

    for page in raw_pages:
        idx = page["page_num"]
        text = page["text"]

        if not text:
            refined_pages.append({
                "text": f"*(Page {idx} is empty or scanned without digital text extraction support)*",
                "page_num": idx
            })
            continue

        print(f"Refining Page {idx}/{len(raw_pages)} with VLM...")

        prompt = f"""You are a world-class academic paper formatting system.
Take the following raw extracted text from Page {idx} of a PDF paper.
Convert it into clean, high-fidelity Markdown:
- Format all mathematical equations and formulas in standard LaTeX notation (e.g., $...$ or $$...$$).
- Format all tables into clean Markdown or HTML tables.
- Standardize headings, lists, and paragraphs.
- Do not summarize, skip, or omit any text or data. Preserve the exact scientific meaning and details.

Raw page text:
\"\"\"
{text}
\"\"\"

Output only the formatted Markdown content for this page, with no conversational prefix or suffix.
"""
        messages = [{"role": "user", "content": prompt}]
        try:
            completion = unified_api_call(
                messages=messages,
                gpt_version=gpt_version,
                temperature=0.1
            )
            completion_json = json.loads(completion.model_dump_json())
            refined_text = completion_json["choices"][0]["message"]["content"].strip()

            # Remove any markdown thinking blocks if present
            if "</think>" in refined_text:
                refined_text = refined_text.split("</think>")[-1].strip()

            refined_pages.append({
                "text": refined_text,
                "page_num": idx
            })
        except Exception as e:
            print(f"[WARNING] VLM call failed for page {idx}: {e}. Falling back to raw text.")
            refined_pages.append({
                "text": text,
                "page_num": idx
            })

    return refined_pages


def process_pdf_olmocr(pdf_path, output_dir=None):
    """
    Wrapper for Allen Institute for AI's olmOCR tool.
    Executes 'python -m olmocr.pipeline' as a subprocess if installed.
    """
    print(f"[PREPROCESS] Processing PDF with olmOCR: {pdf_path}")
    if not output_dir:
        output_dir = os.path.dirname(pdf_path) or "."

    workspace_dir = os.path.join(output_dir, "olmocr_workspace")
    os.makedirs(workspace_dir, exist_ok=True)

    cmd = [
        sys.executable, "-m", "olmocr.pipeline",
        workspace_dir,
        "--pdfs", pdf_path,
        "--markdown"
    ]

    print(f"Running command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("[olmOCR] Success!")

        # Load the generated markdown outputs from olmocr_workspace/results
        results_dir = os.path.join(workspace_dir, "results")
        pages = []
        if os.path.exists(results_dir):
            for file in sorted(os.listdir(results_dir)):
                if file.endswith(".md"):
                    with open(os.path.join(results_dir, file)) as f:
                        pages.append({
                            "text": f.read().strip(),
                            "page_num": len(pages) + 1
                        })
        return pages
    except Exception as e:
        print(f"[ERROR] Failed to run olmocr: {e}. Falling back to VLM refinement.")
        return None


def main(args):
    input_path = args.input_json_path
    output_path = args.output_json_path
    mode = args.mode
    gpt_version = args.gpt_version
    paper_name = args.paper_name or os.path.splitext(os.path.basename(input_path))[0]

    # Ingestion Routing: Check if PDF or JSON
    if input_path.lower().endswith(".pdf"):
        print(f"[INJECT] Direct PDF mode detected: {input_path}")

        pages = None

        # Determine execution mode
        if mode == "auto":
            # If an API key is available, use VLM. Else use local.
            api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                mode = "vlm"
            else:
                mode = "local"
                print("[INFO] No API key detected. Using local pypdf mode.")

        if mode == "olmocr":
            pages = process_pdf_olmocr(input_path, os.path.dirname(output_path))
            if not pages:
                mode = "vlm"  # Fallback to VLM

        if mode == "vlm":
            pages = process_pdf_vlm(input_path, gpt_version=gpt_version)

        if mode == "local" or not pages:
            pages = process_pdf_local(input_path)

        # Standardize structure to be compatible with downstream stages

        # Infer title and abstract from first page if possible
        title = paper_name
        abstract = ""
        if len(pages) > 0:
            first_page_text = pages[0]["text"]
            # Extract simple title / abstract approximations
            abstract_match = re.search(r"(?:Abstract|ABSTRACT)([\s\S]*?)(?:Introduction|1\s+Introduction|INTRODUCTION)", first_page_text, re.IGNORECASE)
            if abstract_match:
                abstract = abstract_match.group(1).strip()
            else:
                # Fallback: first 500 characters
                abstract = first_page_text[:500] + "..."

        structured_data = {
            "paper_id": paper_name,
            "title": title,
            "abstract": abstract,
            "pdf_parse": {
                "paper_id": paper_name,
                "abstract": [{"text": abstract, "section": "Abstract", "sec_num": None}],
                "body_text": [
                    {
                        "text": p["text"],
                        "section": f"Page {p['page_num']}",
                        "sec_num": str(p["page_num"])
                    }
                    for p in pages
                ]
            }
        }

        print(f"[SAVED] Structured paper JSON to {output_path}")
        with open(output_path, "w") as f:
            json.dump(structured_data, f)

    else:
        # Legacy Mode: Grobid JSON
        process_legacy_json(input_path, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modernized Paper2Code PDF Ingestion Processor.")
    parser.add_argument("--input_json_path", type=str, required=True, help="Path to input PDF or Grobid JSON.")
    parser.add_argument("--output_json_path", type=str, required=True, help="Path to save processed and cleaned JSON.")
    parser.add_argument("--mode", type=str, default="auto", choices=["auto", "vlm", "olmocr", "local"],
                        help="Processing mode: auto (VLM if key present else local), vlm, olmocr, or local.")
    parser.add_argument("--gpt_version", type=str, default=os.environ.get("LLM_MODEL", "MiniMax-M2.7"),
                        help="VLM model choice (default: LLM_MODEL env var or MiniMax-M2.7).")
    parser.add_argument("--paper_name", type=str, default=None, help="Name of the paper.")

    args = parser.parse_args()
    main(args)
