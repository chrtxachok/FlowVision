#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Setup ML Models for OCR Service ===${NC}"

# Check if Hugging Face CLI is installed
if ! command -v huggingface-cli &> /dev/null; then
    echo -e "${YELLOW}Installing Hugging Face CLI...${NC}"
    pip install huggingface-hub
fi

# Create models directory
MODELS_DIR="$(dirname "$0")/../services/ocr-service/models"
mkdir -p "$MODELS_DIR/layoutlm"
mkdir -p "$MODELS_DIR/dbnet"

# Download LayoutLM model
echo -e "${YELLOW}Downloading LayoutLM model...${NC}"
huggingface-cli download microsoft/layoutlm-base-uncased \
    --local-dir "$MODELS_DIR/layoutlm" \
    --cache-dir "$MODELS_DIR/.cache"

# Download DBNet model (example - replace with actual model)
echo -e "${YELLOW}Downloading DBNet model...${NC}"
# huggingface-cli download ...

echo -e "${GREEN}=== Models Setup Complete ===${NC}"
echo "Models saved to: $MODELS_DIR"
