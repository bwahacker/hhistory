# Load this file with 'source'
# Enhanced hhistory alias for timeline + directory + session history

# Main function to call hhistory
hh() {
    if [ -f ~/bin/hh-intern.py ]; then
        python3 ~/bin/hh-intern.py "$@"
    else
        echo "hhistory not found. Please run: curl -sSL https://raw.githubusercontent.com/bwahacker/hhistory/main/install.sh | bash"
        return 1
    fi
}

# Quick aliases for common operations
alias hht='hh --timeline'           # Timeline view
alias hhr='hh --recent'             # Recent commands
alias hhs='hh --search'             # Search commands
alias hhf='hh --fuzzy'              # Fuzzy search commands
alias hhstats='hh --stats'          # Statistics
alias hhall='hh --all'              # All history
alias hhclean='hh --cleanup'        # Cleanup old sessions
alias hhcleanup='hh --cleanup-dead' # Cleanup dead shells

# Function to save current shell history
save_history() {
    # Save current history to ~/.myhistory
    history > ~/.myhistory
    
    # Update hhistory database
    hh
}

# Auto-save history on shell exit
trap save_history EXIT

# Export function so it's available in subshells
export -f hh
export -f save_history
