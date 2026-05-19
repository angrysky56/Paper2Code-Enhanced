#!/usr/bin/env bash
# Load provider config from .env (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, etc.)
# set -a; source "$(dirname "$0")/../.env"; set +a

# Model override — leave empty to use LLM_MODEL from .env
GPT_VERSION="${LLM_MODEL:-o3-mini}"

PAPER_NAME="Transformer"
PDF_LATEX_CLEANED_PATH="../examples/Transformer_cleaned.tex" # _cleaned.tex
OUTPUT_DIR="../outputs/Transformer"
OUTPUT_REPO_DIR="../outputs/Transformer_repo"

mkdir -p "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_REPO_DIR}"

echo "${PAPER_NAME}"

echo "------- PaperCoder -------"

# Build optional --gpt_version flag
_gpt_flag=""
if [[ -n ${GPT_VERSION} ]]; then _gpt_flag="--gpt_version ${GPT_VERSION}"; fi

python ../codes/1_planning.py \
	--paper_name "${PAPER_NAME}" \
	"${_gpt_flag}" \
	--pdf_latex_path "${PDF_LATEX_CLEANED_PATH}" \
	--paper_format LaTeX \
	--output_dir "${OUTPUT_DIR}"

python ../codes/1.1_extract_config.py \
	--paper_name "${PAPER_NAME}" \
	--output_dir "${OUTPUT_DIR}"

cp -rp "${OUTPUT_DIR}/planning_config.yaml" "${OUTPUT_REPO_DIR}/config.yaml"

python ../codes/2_analyzing.py \
	--paper_name "${PAPER_NAME}" \
	"${_gpt_flag}" \
	--pdf_latex_path "${PDF_LATEX_CLEANED_PATH}" \
	--paper_format LaTeX \
	--output_dir "${OUTPUT_DIR}"

python ../codes/3_coding.py \
	--paper_name "${PAPER_NAME}" \
	"${_gpt_flag}" \
	--pdf_latex_path "${PDF_LATEX_CLEANED_PATH}" \
	--paper_format LaTeX \
	--output_dir "${OUTPUT_DIR}" \
	--output_repo_dir "${OUTPUT_REPO_DIR}"
