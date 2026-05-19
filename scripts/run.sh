#!/usr/bin/env bash
# Load provider config from .env (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, etc.)
# The Python scripts load .env automatically via python-dotenv.
# Uncomment the line below if you also need env vars available to this shell script:
# set -a; source "$(dirname "$0")/../.env"; set +a

# Model override — leave empty to use LLM_MODEL from .env
GPT_VERSION="${LLM_MODEL-}"

PAPER_NAME="Transformer"
# PDF_PATH="../examples/Transformer.pdf"                       # .pdf (raw PDF, preprocessed to JSON)
PDF_JSON_PATH="../examples/Transformer.json"                 # .json
PDF_JSON_CLEANED_PATH="../examples/Transformer_cleaned.json" # _cleaned.json
OUTPUT_DIR="../outputs/Transformer"
OUTPUT_REPO_DIR="../outputs/Transformer_repo"

mkdir -p "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_REPO_DIR}"

echo "${PAPER_NAME}"

echo "------- Preprocess -------"

python ../codes/0_pdf_process.py \
	--input_json_path "${PDF_JSON_PATH}" \
	--output_json_path "${PDF_JSON_CLEANED_PATH}"

echo "------- PaperCoder -------"

# Build optional --gpt_version flag (only passed if GPT_VERSION is set, otherwise scripts use .env)
_gpt_flag=""
if [[ -n ${GPT_VERSION} ]]; then _gpt_flag="--gpt_version ${GPT_VERSION}"; fi

python ../codes/1_planning.py \
	--paper_name "${PAPER_NAME}" \
	"${_gpt_flag}" \
	--pdf_json_path "${PDF_JSON_CLEANED_PATH}" \
	--output_dir "${OUTPUT_DIR}"

python ../codes/1.1_extract_config.py \
	--paper_name "${PAPER_NAME}" \
	--output_dir "${OUTPUT_DIR}"

cp -rp "${OUTPUT_DIR}/planning_config.yaml" "${OUTPUT_REPO_DIR}/config.yaml"

python ../codes/2_analyzing.py \
	--paper_name "${PAPER_NAME}" \
	"${_gpt_flag}" \
	--pdf_json_path "${PDF_JSON_CLEANED_PATH}" \
	--output_dir "${OUTPUT_DIR}"

python ../codes/3_coding.py \
	--paper_name "${PAPER_NAME}" \
	"${_gpt_flag}" \
	--pdf_json_path "${PDF_JSON_CLEANED_PATH}" \
	--output_dir "${OUTPUT_DIR}" \
	--output_repo_dir "${OUTPUT_REPO_DIR}"
