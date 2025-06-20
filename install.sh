#!/bin/bash

# hhistory - One-liner installer
# The ultimate shell history system that never forgets where you've been

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
echo "🚀 hhistory - The ultimate shell history system"
echo "================================================"
echo -e "${NC}"

# Check if we're in a git repo or need to clone
if [ -f "hh-intern.py" ] && [ -f "hh-alias.sh" ]; then
    echo -e "${GREEN}✓ Found hhistory files in current directory${NC}"
    REPO_DIR="."
else
    echo -e "${YELLOW}📥 Cloning hhistory repository...${NC}"
    TEMP_DIR=$(mktemp -d)
    git clone https://github.com/bwahacker/hhistory.git "$TEMP_DIR" 2>/dev/null || {
        echo -e "${RED}✗ Failed to clone repository${NC}"
        echo "Please check your internet connection and try again."
        exit 1
    }
    REPO_DIR="$TEMP_DIR"
    cd "$REPO_DIR"
fi

# Check Python version
echo -e "${YELLOW}🔍 Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is required but not installed${NC}"
    echo "Please install Python 3.7+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    echo -e "${RED}✗ Python 3.7+ is required, found $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"

# Create bin directory
echo -e "${YELLOW}📁 Setting up installation...${NC}"
mkdir -p ~/bin

# Copy files
echo -e "${YELLOW}📋 Installing hhistory...${NC}"
cp "$REPO_DIR/hh-intern.py" ~/bin/
cp "$REPO_DIR/hh-alias.sh" ~/bin/
chmod +x ~/bin/hh-intern.py

# Detect shell
SHELL_CONFIG=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    # Try to detect shell
    CURRENT_SHELL=$(basename "$SHELL")
    case "$CURRENT_SHELL" in
        zsh)
            SHELL_CONFIG="$HOME/.zshrc"
            SHELL_NAME="zsh"
            ;;
        bash)
            SHELL_CONFIG="$HOME/.bashrc"
            SHELL_NAME="bash"
            ;;
        *)
            echo -e "${YELLOW}⚠️  Could not detect shell type, you'll need to manually add to your shell config${NC}"
            SHELL_CONFIG=""
            SHELL_NAME="unknown"
            ;;
    esac
fi

# Add to shell config
if [ -n "$SHELL_CONFIG" ]; then
    echo -e "${YELLOW}🔧 Adding to $SHELL_NAME configuration...${NC}"
    
    # Check if already added
    if grep -q "source ~/bin/hh-alias.sh" "$SHELL_CONFIG" 2>/dev/null; then
        echo -e "${GREEN}✓ hhistory already configured in $SHELL_CONFIG${NC}"
    else
        echo "" >> "$SHELL_CONFIG"
        echo "# hhistory - Enhanced shell history" >> "$SHELL_CONFIG"
        echo "source ~/bin/hh-alias.sh" >> "$SHELL_CONFIG"
        echo -e "${GREEN}✓ Added hhistory to $SHELL_CONFIG${NC}"
    fi
fi

# Clean up temp directory if we cloned
if [ "$REPO_DIR" != "." ]; then
    rm -rf "$REPO_DIR"
fi

# Test installation
echo -e "${YELLOW}🧪 Testing installation...${NC}"
if [ -f ~/bin/hh-intern.py ] && [ -x ~/bin/hh-intern.py ]; then
    echo -e "${GREEN}✓ Installation successful!${NC}"
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi

# Print success message
echo -e "${GREEN}"
echo "🎉 hhistory installed successfully!"
echo ""
echo "Next steps:"
echo "1. Restart your terminal or run: source ~/bin/hh-alias.sh"
echo "2. Start using hhistory:"
echo "   hh                    # Show current directory history"
echo "   hh --timeline         # Show global timeline"
echo "   hh --search 'git'     # Search for git commands"
echo "   hh --stats            # Show statistics"
echo ""
echo "Quick aliases:"
echo "  hht         # Timeline view"
echo "  hhr         # Recent commands"
echo "  hhs         # Search commands"
echo "  hhstats     # Statistics"
echo ""
echo "📖 Documentation: https://github.com/bwahacker/hhistory"
echo "🐛 Issues: https://github.com/bwahacker/hhistory/issues"
echo -e "${NC}"

# Offer to load aliases now
if [ -n "$SHELL_CONFIG" ]; then
    echo -e "${YELLOW}Would you like to load hhistory aliases now? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        source ~/bin/hh-alias.sh
        echo -e "${GREEN}✓ hhistory aliases loaded! Try 'hh' to get started.${NC}"
    fi
fi 