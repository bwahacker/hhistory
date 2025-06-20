# hhistory Makefile
# The ultimate shell history system

.PHONY: install test clean help

# Default target
all: help

# Install hhistory
install:
	@echo "Installing hhistory..."
	@chmod +x hh-intern.py
	@chmod +x install.sh
	@mkdir -p ~/bin
	@cp hh-intern.py ~/bin/
	@cp hh-alias.sh ~/bin/
	@echo "Installation complete!"
	@echo "Add 'source ~/bin/hh-alias.sh' to your shell config"

# Run tests
test:
	@echo "Running hhistory tests..."
	@python3 test_hh.py

# Quick test (basic functionality)
test-quick:
	@echo "Running quick test..."
	@python3 -c "import hh_intern; print('✓ Basic import successful')" 2>/dev/null || echo "❌ Import failed"

# Clean up temporary files
clean:
	@echo "Cleaning up..."
	@rm -f ~/.myhistory
	@rm -rf ~/.hh_databases
	@rm -rf ~/.hh_lifecycle
	@echo "Cleanup complete!"

# Uninstall hhistory
uninstall:
	@echo "Uninstalling hhistory..."
	@rm -f ~/bin/hh-intern.py
	@rm -f ~/bin/hh-alias.sh
	@echo "Please remove 'source ~/bin/hh-alias.sh' from your shell config"
	@echo "Uninstall complete!"

# Show help
help:
	@echo "hhistory - The ultimate shell history system"
	@echo ""
	@echo "Available targets:"
	@echo "  install     - Install hhistory to ~/bin"
	@echo "  test        - Run full test suite"
	@echo "  test-quick  - Run quick functionality test"
	@echo "  clean       - Clean up temporary files and databases"
	@echo "  uninstall   - Remove hhistory installation"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Usage examples:"
	@echo "  make install    # Install hhistory"
	@echo "  make test       # Run tests"
	@echo "  make clean      # Clean up data"

