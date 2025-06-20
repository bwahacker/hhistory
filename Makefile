.PHONY: hh install clean cleanup cleanup-dead

# Install the enhanced hhistory system
hh: install

install:
	@echo "Installing enhanced hhistory (TTY+PID)..."
	@mkdir -p ~/bin
	cp hh-intern.py ~/bin/hh-intern.py
	cp hh-alias.sh ~/bin/hh-alias.sh
	chmod +x ~/bin/hh-intern.py
	@echo "Installation complete!"
	@echo "Add 'source ~/bin/hh-alias.sh' to your ~/.bashrc or ~/.zshrc"

# Clean up old session databases
cleanup:
	@echo "Cleaning up old session databases..."
	@if [ -d ~/.hh_databases ]; then \
		find ~/.hh_databases -name "session_*.db" -mtime +30 -delete; \
		echo "Removed session databases older than 30 days"; \
	else \
		echo "No session databases found"; \
	fi

# Clean up dead shell databases
cleanup-dead:
	@echo "Cleaning up dead shell databases..."
	@if [ -f ~/bin/hh-intern.py ]; then \
		~/bin/hh-intern.py --cleanup-dead; \
	else \
		echo "hhistory not installed"; \
	fi

# Clean up installation and all data
clean:
	rm -f ~/bin/hh-intern.py ~/bin/hh-alias.sh ~/.hh_session.json ~/.myhistory
	rm -rf ~/.hh_databases ~/.hh_lifecycle
	rm -f ~/.hh_global_history.json ~/.hh_global_history.db

