#!/bin/bash
# WhatsApp Bot Setup Script
# Automated environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
PYTHON_BIN="python3"
NO_TEMPLATES=false
INSTALL_SYSTEM=false

# Help function
show_help() {
    cat << EOF
WhatsApp Bot Setup Script

Usage: ./setup.sh [OPTIONS]

Options:
  -h, --help              Show this help message
  --python PATH           Use specific Python binary (default: python3)
  --no-templates          Don't create config templates
  --install-system-deps   Install system dependencies (requires sudo)

Examples:
  ./setup.sh                           # Normal setup
  ./setup.sh --python python3.11       # Use specific Python version
  ./setup.sh --install-system-deps     # Install system packages too

EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        --python)
            PYTHON_BIN="$2"
            shift 2
            ;;
        --no-templates)
            NO_TEMPLATES=true
            shift
            ;;
        --install-system-deps)
            INSTALL_SYSTEM=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🚀 WhatsApp Bot Setup Script${NC}"
echo "=============================="
echo ""

# Check Python version
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo -e "${RED}❌ $PYTHON_BIN not found${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_BIN --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python version: $PYTHON_VERSION${NC}"

# Check Python version >= 3.9
if ! $PYTHON_BIN -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo -e "${RED}❌ Python 3.9+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

# Install system dependencies if requested
if [ "$INSTALL_SYSTEM" = true ]; then
    echo ""
    echo -e "${YELLOW}📦 Installing system dependencies...${NC}"

    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y python3-pip qrencode
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip qrencode
    elif command -v brew &> /dev/null; then
        brew install qrencode
    else
        echo -e "${YELLOW}⚠️  Could not detect package manager. Please install qrencode manually.${NC}"
    fi
fi

# Upgrade pip
echo ""
echo -e "${YELLOW}⬆️  Upgrading pip...${NC}"
if $PYTHON_BIN -m pip install --upgrade pip setuptools wheel --user 2>&1 | grep -q "externally-managed-environment"; then
    # Handle externally-managed Python (e.g., Homebrew Python on macOS)
    $PYTHON_BIN -m pip install --break-system-packages --user --upgrade pip setuptools wheel
    echo -e "${YELLOW}⚠️  Using --break-system-packages flag (externally-managed environment detected)${NC}"
else
    $PYTHON_BIN -m pip install --upgrade pip setuptools wheel --user
fi
echo -e "${GREEN}✅ pip upgraded${NC}"

# Install dependencies
echo ""
echo -e "${YELLOW}📥 Installing dependencies...${NC}"
if $PYTHON_BIN -m pip install --user -r bot/requirements.txt 2>&1 | grep -q "externally-managed-environment"; then
    # Handle externally-managed Python (e.g., Homebrew Python on macOS)
    $PYTHON_BIN -m pip install --break-system-packages --user -r bot/requirements.txt
    echo -e "${YELLOW}⚠️  Using --break-system-packages flag (externally-managed environment detected)${NC}"
else
    $PYTHON_BIN -m pip install --user -r bot/requirements.txt
fi
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Create necessary directories
echo ""
echo -e "${YELLOW}📁 Creating directories...${NC}"
mkdir -p store bot/logs
echo -e "${GREEN}✅ Directories created${NC}"

# Copy config templates
if [ "$NO_TEMPLATES" = false ]; then
    echo ""
    if [ ! -f .env ]; then
        echo -e "${YELLOW}📝 Creating .env from template...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ .env created${NC}"
        echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env and add your PERPLEXITY_API_KEY!${NC}"
    else
        echo -e "${GREEN}✅ .env already exists (skipping)${NC}"
    fi

    if [ ! -f bot/app.json ]; then
        echo -e "${YELLOW}📝 Creating app.json from template...${NC}"
        cp bot/app.json.example bot/app.json
        echo -e "${GREEN}✅ app.json created${NC}"
        echo -e "${YELLOW}⚠️  IMPORTANT: Edit bot/app.json with your WhatsApp groups/users!${NC}"
    else
        echo -e "${GREEN}✅ app.json already exists (skipping)${NC}"
    fi
fi

# Set permissions
chmod +x run-bot.sh run-bridge.sh 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your PERPLEXITY_API_KEY"
echo "2. Edit app.json with your phone number and monitored groups/users"
echo "3. Run: ./run-bot.sh"
echo ""
