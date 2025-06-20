# Load this file with 'source'
# Enhanced hhistory alias for timeline + directory + session history

# Function to save history based on shell type
save_history() {
    if [ -n "$ZSH_VERSION" ]; then
        # zsh
        fc -W ~/.myhistory
    elif [ -n "$BASH_VERSION" ]; then
        # bash
        history -w ~/.myhistory
    else
        # fallback - try to copy history file
        if [ -f ~/.zsh_history ]; then
            cp ~/.zsh_history ~/.myhistory
        elif [ -f ~/.bash_history ]; then
            cp ~/.bash_history ~/.myhistory
        fi
    fi
}

# Save current history and update global history
alias hh='save_history && ~/bin/hh-intern.py'

# Quick aliases for common operations
alias hht='hh --timeline'           # Show timeline view
alias hhr='hh --recent'             # Show recent commands
alias hhs='hh --search'             # Search commands
alias hha='hh --all'                # Show all history
alias hhshell='hh --shell'          # Show with shell info
alias hhstats='hh --stats'          # Show database statistics
alias hhclean='hh --cleanup'        # Clean up old session databases
alias hhcleandead='hh --cleanup-dead' # Clean up dead shell databases
