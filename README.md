# 🚀 hhistory

> **The ultimate shell history system that never forgets where you've been**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Shells: bash/zsh](https://img.shields.io/badge/shells-bash%20%7C%20zsh-green.svg)](https://github.com/bwahacker/hhistory)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**Stop losing your command history across terminals.** hhistory gives you a **global timeline** of every command you've ever run, with **context awareness** and **intelligent session tracking**.

```bash
# See what you did in this project last week
hh --timeline | grep "2024-01-15"

# Find that git command you ran somewhere...
hh --search "git rebase"

# What was I working on in this directory?
hh .

# Show me my workflow from yesterday
hh --recent 50 --shell
```

## ✨ Why hhistory?

| Feature | Traditional History | hhistory |
|---------|-------------------|----------|
| **Cross-terminal** | ❌ Each terminal isolated | ✅ **Global timeline** |
| **Context aware** | ❌ Just commands | ✅ **Directory + timestamp** |
| **Shell spawning** | ❌ Breaks with subshells | ✅ **TTY+PID tracking** |
| **Search** | ❌ Basic grep | ✅ **Semantic search** |
| **Performance** | ❌ Single file locks | ✅ **Per-shell databases** |
| **Cleanup** | ❌ Manual maintenance | ✅ **Auto-cleanup** |

## 🎯 Perfect For

- **Developers** who work across multiple terminals and projects
- **DevOps engineers** who need to track complex workflows
- **System administrators** who manage multiple servers
- **Anyone** who's ever said "what was that command I ran yesterday?"

## 🚀 Quick Start

```bash
# Install
git clone https://github.com/bwahacker/hhistory.git
cd hhistory
make hh

# Add to your shell
echo 'source ~/bin/hh-alias.sh' >> ~/.bashrc  # or ~/.zshrc

# Start using it
source ~/bin/hh-alias.sh
hh  # See your current directory history
```

## 🎮 Usage Examples

### 🔍 Find That Command You Forgot
```bash
# Search across all your terminals
hh --search "docker build"

# Find commands from last week
hh --timeline | grep "2024-01-10"
```

### 📊 See Your Workflow
```bash
# What have you been working on?
hh --recent 20 --shell

# Your most used commands
hh --stats

# Timeline of your day
hh --timeline
```

### 🗂️ Context-Aware History
```bash
# What did you do in this project?
hh .

# What commands work in this directory?
hh /path/to/project

# Show commands with shell context
hh --shell
```

## 🏗️ Architecture

hhistory uses **TTY+PID identification** with **shell lifecycle management**:

- 🔐 **Unique Shell IDs**: `{TTY}_{PID}` (e.g., `ttys001_12345`)
- 🗄️ **Per-Shell Databases**: No race conditions, no locks
- 🧹 **Auto-Cleanup**: Removes dead shells automatically
- 🔄 **On-Demand Merging**: Global queries when you need them
- 👨‍👩‍👧‍👦 **Parent-Child Support**: Handles shell spawning perfectly

```
~/.hh_databases/
├── session_ttys001_12345.db  # Terminal 1, Process 12345
├── session_ttys001_12346.db  # Terminal 1, Process 12346 (subshell)
└── session_ttys002_12347.db  # Terminal 2, Process 12347

~/.hh_lifecycle/
├── active_ttys001_12345      # Shell is alive
└── active_ttys002_12347      # Shell is alive
```

## 🎯 Features

### 🌟 Core Features
- **Global Timeline**: Every command from every terminal
- **Directory Context**: Know where each command was run
- **Shell Tracking**: TTY+PID identification for precision
- **Smart Search**: Find commands by content, not just history
- **Session Management**: Automatic cleanup of dead shells

### 🚀 Advanced Features
- **Statistics**: See your most used commands and directories
- **Time-based Queries**: Filter by date ranges
- **Shell Spawning**: Handle parent-child shell relationships
- **Performance**: No locks, no contention, no slowdowns
- **Reliability**: Corrupted shells don't affect others

### 🛠️ Developer Experience
- **Quick Aliases**: `hht`, `hhr`, `hhs`, `hha`, `hhstats`
- **Shell Integration**: Works with bash, zsh, and more
- **Zero Configuration**: Just install and go
- **Clean API**: Simple, predictable commands

## 📦 Installation

### From Source (Recommended)
```bash
git clone https://github.com/bwahacker/hhistory.git
cd hhistory
make hh
echo 'source ~/bin/hh-alias.sh' >> ~/.bashrc  # or ~/.zshrc
```

### Manual Installation
```bash
# Copy files
mkdir -p ~/bin
cp hh-intern.py ~/bin/
cp hh-alias.sh ~/bin/
chmod +x ~/bin/hh-intern.py

# Add to shell
echo 'source ~/bin/hh-alias.sh' >> ~/.bashrc
```

## 🎮 Commands

### Basic Usage
```bash
hh                    # Show current directory history
hh /path/to/dir       # Show history for specific directory
hh --timeline         # Global timeline view
hh --recent 50        # Recent 50 commands
hh --search "query"   # Search commands
hh --stats            # Database statistics
```

### Quick Aliases
```bash
hht         # Timeline view
hhr         # Recent commands  
hhs         # Search commands
hha         # All history
hhshell     # With shell info
hhstats     # Database statistics
hhclean     # Clean up old sessions
hhcleandead # Clean up dead shells
```

### Advanced Options
```bash
# Show with timestamps and shell info
hh --timeline --shell

# Search and show context
hh --search "git" --shell

# Clean up old data
hh --cleanup 30        # Remove sessions older than 30 days
hh --cleanup-dead      # Remove dead shell databases
```

## 🔧 Configuration

### Environment Variables
```bash
# Custom database directory (optional)
export HH_DB_DIR=~/.my_hhistory_databases

# Custom history file (optional)
export HH_HISTORY_FILE=~/.my_custom_history
```

### Shell Integration
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
source ~/bin/hh-alias.sh

# Optional: Auto-cleanup on shell start
hh --cleanup-dead >/dev/null 2>&1
```

## 🏗️ Data Structure

Each command is stored with rich context:
```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,           -- The actual command
    directory TEXT NOT NULL,         -- Where it was run
    shell_id TEXT NOT NULL,          -- TTY_PID identifier
    tty TEXT NOT NULL,               -- Terminal device
    pid INTEGER NOT NULL,            -- Process ID
    ppid INTEGER,                    -- Parent process ID
    timestamp REAL NOT NULL,         -- Unix timestamp
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🧪 Examples

### Real-World Workflows

**Find that deployment command:**
```bash
hh --search "kubectl apply" --shell
```

**See your git workflow:**
```bash
hh --search "git" | grep "commit\|push\|pull"
```

**What was I working on yesterday?**
```bash
hh --timeline | grep "$(date -d 'yesterday' +%Y-%m-%d)"
```

**Most used commands this week:**
```bash
hh --stats
```

## 🤝 Contributing

We love contributions! Here's how to help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup
```bash
git clone https://github.com/bwahacker/hhistory.git
cd hhistory
make hh
# Start hacking!
```

## 🐛 Troubleshooting

### Common Issues

**"No entries found"**
- Make sure you've run some commands first
- Check that `~/.myhistory` exists and has content
- Verify your shell is saving history properly

**"Permission denied"**
- Ensure `~/bin/hh-intern.py` is executable: `chmod +x ~/bin/hh-intern.py`

**"Command not found: hh"**
- Make sure you've sourced the alias file: `source ~/bin/hh-alias.sh`
- Add the source line to your shell config file

### Debug Mode
```bash
# Run with verbose output
HH_DEBUG=1 hh --stats
```

## 📈 Performance

- **Write Performance**: ~0.1ms per command (no locks)
- **Read Performance**: ~10ms for 1000 commands
- **Storage**: ~1KB per 100 commands
- **Memory**: Minimal (streaming reads)

## 🔮 Roadmap

- [ ] **Web Interface**: Browse history in your browser
- [ ] **Cloud Sync**: Share history across machines
- [ ] **Command Categorization**: Auto-tag commands by type
- [ ] **Export/Import**: Backup and restore functionality
- [ ] **Real-time Sharing**: Live history between team members
- [ ] **Plugin System**: Extend with custom analyzers
- [ ] **Machine Learning**: Smart command suggestions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the need to never lose command context
- Built for developers who work across multiple terminals
- Thanks to the open source community for amazing tools

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=bwahacker/hhistory&type=Date)](https://star-history.com/#bwahacker/hhistory&Date)

---

**Made with ❤️ for developers who never want to lose their command history again.**

**Created by [Mitch Haile](https://www.mitchhaile.com)**

[![GitHub stars](https://img.shields.io/github/stars/bwahacker/hhistory?style=social)](https://github.com/bwahacker/hhistory)
[![GitHub forks](https://img.shields.io/github/forks/bwahacker/hhistory?style=social)](https://github.com/bwahacker/hhistory)
[![GitHub issues](https://img.shields.io/github/issues/bwahacker/hhistory)](https://github.com/bwahacker/hhistory/issues)
