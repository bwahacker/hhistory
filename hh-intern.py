#!/usr/bin/python3 
#
# Enhanced contextual history with timeline, directory, and session tracking
# Now using TTY+PID identification with shell lifecycle management
#
# Copyright (c) 2021, Mitch Haile.
# 
# MIT License
#

import os
import sys
import sqlite3
import json
import time
import uuid
import glob
import signal
import atexit
import threading
import logging
from datetime import datetime
from collections import defaultdict, OrderedDict
import argparse
from difflib import SequenceMatcher

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Database files
DB_DIR = os.path.expanduser("~/.hh_databases")
SESSION_FILE = os.path.expanduser("~/.hh_session.json")
LIFECYCLE_DIR = os.path.expanduser("~/.hh_lifecycle")

def safe_makedirs(path):
    """Safely create directories with error handling"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except (OSError, PermissionError) as e:
        logger.error(f"Could not create directory {path}: {e}")
        return False

def safe_connect_db(db_file):
    """Safely connect to SQLite database with error handling"""
    try:
        return sqlite3.connect(db_file)
    except sqlite3.Error as e:
        logger.error(f"Could not connect to database {db_file}: {e}")
        return None
    except PermissionError as e:
        logger.error(f"Permission denied accessing {db_file}: {e}")
        return None

def get_shell_identifier():
    """Get unique identifier for this shell (TTY + PID) with error handling"""
    try:
        tty = os.ttyname(sys.stdout.fileno())
        tty_name = os.path.basename(tty)
    except (OSError, AttributeError, ValueError) as e:
        logger.warning(f"Could not determine TTY: {e}")
        tty_name = "unknown"
    
    try:
        pid = os.getpid()
        ppid = os.getppid()
    except OSError as e:
        logger.error(f"Could not determine process IDs: {e}")
        pid = 0
        ppid = 0
    
    return {
        'tty': tty_name,
        'pid': pid,
        'ppid': ppid,
        'identifier': f"{tty_name}_{pid}",
        'parent_identifier': f"{tty_name}_{ppid}" if ppid != 1 else None
    }

def create_lifecycle_marker(shell_id):
    """Create a lifecycle marker file for this shell with error handling"""
    if not safe_makedirs(LIFECYCLE_DIR):
        return None
    
    marker_file = os.path.join(LIFECYCLE_DIR, f"active_{shell_id}")
    
    try:
        with open(marker_file, 'w') as f:
            json.dump({
                'shell_id': shell_id,
                'start_time': time.time(),
                'tty': get_shell_identifier()['tty'],
                'pid': get_shell_identifier()['pid']
            }, f)
        return marker_file
    except (OSError, IOError, json.JSONEncodeError) as e:
        logger.error(f"Could not create lifecycle marker: {e}")
        return None

def remove_lifecycle_marker(shell_id):
    """Remove lifecycle marker file when shell exits with error handling"""
    marker_file = os.path.join(LIFECYCLE_DIR, f"active_{shell_id}")
    try:
        if os.path.exists(marker_file):
            os.remove(marker_file)
    except OSError as e:
        logger.warning(f"Could not remove lifecycle marker {marker_file}: {e}")

def cleanup_dead_shells():
    """Clean up databases for shells that are no longer active with error handling"""
    if not os.path.exists(LIFECYCLE_DIR):
        return 0
    
    removed_count = 0
    
    # Check all active markers
    for marker_file in glob.glob(os.path.join(LIFECYCLE_DIR, "active_*")):
        try:
            with open(marker_file, 'r') as f:
                data = json.load(f)
            
            shell_id = data['shell_id']
            pid = data.get('pid')
            
            # Check if process is still running
            if pid:
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                except OSError:
                    # Process is dead, clean up
                    remove_lifecycle_marker(shell_id)
                    db_file = os.path.join(DB_DIR, f"session_{shell_id}.db")
                    if os.path.exists(db_file):
                        try:
                            os.remove(db_file)
                            removed_count += 1
                            print(f"Cleaned up dead shell: {shell_id}")
                        except OSError as e:
                            logger.warning(f"Could not remove database {db_file}: {e}")
        except (json.JSONDecodeError, OSError, IOError) as e:
            # Corrupted marker, remove it
            logger.warning(f"Corrupted marker file {marker_file}: {e}")
            try:
                os.remove(marker_file)
            except OSError:
                pass
    
    return removed_count

class SessionDB:
    def __init__(self, shell_id):
        self.shell_id = shell_id
        self.db_file = os.path.join(DB_DIR, f"session_{shell_id}.db")
        self.marker_file = None
        if not self.init_db():
            raise RuntimeError(f"Could not initialize database for shell {shell_id}")
        self.setup_lifecycle()
    
    def init_db(self):
        """Initialize the session SQLite database with error handling"""
        if not safe_makedirs(DB_DIR):
            return False
        
        conn = safe_connect_db(self.db_file)
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Create history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    directory TEXT NOT NULL,
                    shell_id TEXT NOT NULL,
                    tty TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    ppid INTEGER,
                    timestamp REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_directory ON history(directory)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON history(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_command ON history(command)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shell_id ON history(shell_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tty ON history(tty)')
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            conn.close()
            return False
    
    def setup_lifecycle(self):
        """Set up lifecycle management for this shell with error handling"""
        self.marker_file = create_lifecycle_marker(self.shell_id)
        
        # Register cleanup function to run on exit
        atexit.register(self.cleanup_on_exit)
        
        # Also handle signals
        def signal_handler(signum, frame):
            self.cleanup_on_exit()
            sys.exit(0)
        
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except (OSError, ValueError) as e:
            logger.warning(f"Could not set up signal handlers: {e}")
    
    def cleanup_on_exit(self):
        """Clean up when shell exits with error handling"""
        if self.marker_file:
            remove_lifecycle_marker(self.shell_id)
    
    def add_entry(self, command, directory, timestamp=None):
        """Add a new history entry to this session's database with error handling"""
        if timestamp is None:
            timestamp = time.time()
        
        shell_info = get_shell_identifier()
        
        conn = safe_connect_db(self.db_file)
        if not conn:
            logger.error(f"Could not connect to database to add entry")
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO history (command, directory, shell_id, tty, pid, ppid, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (command, directory, self.shell_id, shell_info['tty'], 
                  shell_info['pid'], shell_info['ppid'], timestamp))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Could not add history entry: {e}")
            conn.close()
            return False
    
    def get_entries(self):
        """Get all entries from this session with error handling"""
        conn = safe_connect_db(self.db_file)
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT command, directory, shell_id, tty, pid, timestamp
                FROM history 
                ORDER BY timestamp DESC
            ''')
            
            entries = [HistoryEntry(row[0], row[1], row[2], row[5], row[3], row[4]) 
                      for row in cursor.fetchall()]
            conn.close()
            return entries
        except sqlite3.Error as e:
            logger.error(f"Could not retrieve entries: {e}")
            conn.close()
            return []

class GlobalHistory:
    def __init__(self):
        self.db_dir = DB_DIR
        safe_makedirs(DB_DIR)
    
    def get_all_session_dbs(self):
        """Get list of all session database files with error handling"""
        try:
            pattern = os.path.join(DB_DIR, "session_*.db")
            return glob.glob(pattern)
        except OSError as e:
            logger.error(f"Could not list session databases: {e}")
            return []
    
    def merge_all_sessions(self):
        """Merge all session databases into a temporary global view with error handling"""
        all_entries = []
        
        for db_file in self.get_all_session_dbs():
            conn = safe_connect_db(db_file)
            if not conn:
                continue
            
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT command, directory, shell_id, tty, pid, timestamp
                    FROM history 
                    ORDER BY timestamp DESC
                ''')
                
                entries = [HistoryEntry(row[0], row[1], row[2], row[5], row[3], row[4]) 
                          for row in cursor.fetchall()]
                all_entries.extend(entries)
                conn.close()
            except sqlite3.Error as e:
                logger.warning(f"Could not read {db_file}: {e}")
                conn.close()
        
        # Sort by timestamp (newest first)
        return sorted(all_entries, key=lambda x: x.timestamp, reverse=True)
    
    def get_entries_by_directory(self, directory):
        """Get all entries for a specific directory across all sessions with error handling"""
        try:
            entries = self.merge_all_sessions()
            return [entry for entry in entries if entry.directory == directory]
        except Exception as e:
            logger.error(f"Error getting entries by directory: {e}")
            return []
    
    def get_entries_by_shell(self, shell_id):
        """Get all entries for a specific shell with error handling"""
        db_file = os.path.join(DB_DIR, f"session_{shell_id}.db")
        if not os.path.exists(db_file):
            return []
        
        conn = safe_connect_db(db_file)
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT command, directory, shell_id, tty, pid, timestamp
                FROM history 
                WHERE shell_id = ?
                ORDER BY timestamp DESC
            ''', (shell_id,))
            
            entries = [HistoryEntry(row[0], row[1], row[2], row[5], row[3], row[4]) 
                      for row in cursor.fetchall()]
            conn.close()
            return entries
        except sqlite3.Error as e:
            logger.error(f"Could not get entries for shell {shell_id}: {e}")
            conn.close()
            return []
    
    def get_entries_by_tty(self, tty):
        """Get all entries for a specific TTY with error handling"""
        try:
            entries = self.merge_all_sessions()
            return [entry for entry in entries if entry.tty == tty]
        except Exception as e:
            logger.error(f"Error getting entries by TTY: {e}")
            return []
    
    def get_recent_entries(self, limit=50):
        """Get most recent entries across all sessions with error handling"""
        try:
            entries = self.merge_all_sessions()
            return entries[:limit]
        except Exception as e:
            logger.error(f"Error getting recent entries: {e}")
            return []
    
    def get_timeline(self, start_time=None, end_time=None):
        """Get entries within a time range across all sessions with error handling"""
        if start_time is None:
            start_time = 0
        if end_time is None:
            end_time = time.time()
        
        try:
            entries = self.merge_all_sessions()
            return [entry for entry in entries 
                    if start_time <= entry.timestamp <= end_time]
        except Exception as e:
            logger.error(f"Error getting timeline: {e}")
            return []
    
    def search_commands(self, query):
        """Search commands by content across all sessions with error handling"""
        try:
            entries = self.merge_all_sessions()
            query_lower = query.lower()
            return [entry for entry in entries 
                    if query_lower in entry.command.lower()]
        except Exception as e:
            logger.error(f"Error searching commands: {e}")
            return []
    
    def fuzzy_search_commands(self, query, threshold=0.6, limit=20):
        """Fuzzy search commands using sequence matching with error handling"""
        try:
            entries = self.merge_all_sessions()
            query_lower = query.lower()
            
            # Calculate similarity scores
            scored_entries = []
            for entry in entries:
                command_lower = entry.command.lower()
                
                # Check for exact substring match first (higher priority)
                if query_lower in command_lower:
                    score = 1.0
                else:
                    # Use sequence matcher for fuzzy matching
                    score = SequenceMatcher(None, query_lower, command_lower).ratio()
                
                if score >= threshold:
                    scored_entries.append((entry, score))
            
            # Sort by score (highest first) and then by timestamp (newest first)
            scored_entries.sort(key=lambda x: (-x[1], -x[0].timestamp))
            
            # Return unique commands (avoid duplicates)
            seen_commands = set()
            unique_entries = []
            for entry, score in scored_entries:
                if entry.command not in seen_commands and len(unique_entries) < limit:
                    unique_entries.append((entry, score))
                    seen_commands.add(entry.command)
            
            return unique_entries
        except Exception as e:
            logger.error(f"Error in fuzzy search: {e}")
            return []
    
    def get_stats(self):
        """Get database statistics across all sessions with error handling"""
        try:
            entries = self.merge_all_sessions()
            
            if not entries:
                return {
                    'total_entries': 0,
                    'unique_directories': 0,
                    'unique_shells': 0,
                    'unique_ttys': 0,
                    'date_range': None
                }
            
            directories = set(entry.directory for entry in entries)
            shells = set(entry.shell_id for entry in entries)
            ttys = set(entry.tty for entry in entries)
            timestamps = [entry.timestamp for entry in entries]
            
            return {
                'total_entries': len(entries),
                'unique_directories': len(directories),
                'unique_shells': len(shells),
                'unique_ttys': len(ttys),
                'date_range': (min(timestamps), max(timestamps)) if timestamps else None
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_entries': 0,
                'unique_directories': 0,
                'unique_shells': 0,
                'unique_ttys': 0,
                'date_range': None
            }
    
    def get_top_directories(self, limit=10):
        """Get most used directories across all sessions with error handling"""
        try:
            entries = self.merge_all_sessions()
            dir_counts = defaultdict(int)
            
            for entry in entries:
                dir_counts[entry.directory] += 1
            
            sorted_dirs = sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_dirs[:limit]
        except Exception as e:
            logger.error(f"Error getting top directories: {e}")
            return []
    
    def get_top_commands(self, limit=10):
        """Get most used commands across all sessions with error handling"""
        try:
            entries = self.merge_all_sessions()
            cmd_counts = defaultdict(int)
            
            for entry in entries:
                cmd_counts[entry.command] += 1
            
            sorted_cmds = sorted(cmd_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_cmds[:limit]
        except Exception as e:
            logger.error(f"Error getting top commands: {e}")
            return []
    
    def cleanup_dead_shells(self):
        """Clean up databases for shells that are no longer active"""
        return cleanup_dead_shells()
    
    def cleanup_old_sessions(self, days_old=30):
        """Remove session databases older than specified days with error handling"""
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        removed_count = 0
        
        for db_file in self.get_all_session_dbs():
            try:
                # Check if database has recent activity
                conn = safe_connect_db(db_file)
                if not conn:
                    continue
                
                cursor = conn.cursor()
                cursor.execute('SELECT MAX(timestamp) FROM history')
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0]:
                    last_activity = result[0]
                    if last_activity < cutoff_time:
                        try:
                            os.remove(db_file)
                            removed_count += 1
                            print(f"Removed old session: {os.path.basename(db_file)}")
                        except OSError as e:
                            logger.warning(f"Could not remove {db_file}: {e}")
            except sqlite3.Error as e:
                logger.warning(f"Could not read {db_file}: {e}")
                # If we can't read it, it might be corrupted, so remove it
                try:
                    os.remove(db_file)
                    removed_count += 1
                    print(f"Removed corrupted session: {os.path.basename(db_file)}")
                except OSError:
                    pass
        
        return removed_count

class HistoryEntry:
    def __init__(self, command, directory, shell_id, timestamp=None, tty=None, pid=None):
        self.command = command
        self.directory = directory
        self.shell_id = shell_id
        self.timestamp = timestamp or time.time()
        self.tty = tty
        self.pid = pid
    
    def to_dict(self):
        return {
            'command': self.command,
            'directory': self.directory,
            'shell_id': self.shell_id,
            'timestamp': self.timestamp,
            'tty': self.tty,
            'pid': self.pid,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat()
        }

def get_or_create_shell_id():
    """Get or create shell identifier with error handling"""
    try:
        shell_info = get_shell_identifier()
        return shell_info['identifier']
    except Exception as e:
        logger.error(f"Could not get shell identifier: {e}")
        return f"unknown_{os.getpid()}"

def parse_bash_history():
    """Parse bash history and return list of commands with error handling"""
    home_dir = os.environ.get('HOME', '/')
    history_file = os.path.expanduser("~/.myhistory")
    
    if not os.path.exists(history_file):
        return []
    
    commands = []
    try:
        with open(history_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    commands.append(line)
    except (OSError, IOError, UnicodeDecodeError) as e:
        logger.error(f"Could not read history file {history_file}: {e}")
        return []
    
    return commands

def track_directory_changes(commands):
    """Track directory changes and return list of (command, directory) tuples with error handling"""
    current_dir = os.environ.get('HOME', '/')
    result = []
    
    for command in commands:
        # Update current directory based on cd/pushd commands
        if command.startswith('cd '):
            target = command[3:].strip()
            if target == '~' or target.startswith('~/'):
                target = os.path.expanduser(target)
            elif not target.startswith('/'):
                target = os.path.join(current_dir, target)
            
            try:
                if os.path.exists(target):
                    current_dir = os.path.realpath(target)
            except (OSError, ValueError) as e:
                logger.debug(f"Could not resolve path {target}: {e}")
                pass  # Invalid path, keep current directory
        
        elif command.startswith('pushd '):
            target = command[6:].strip()
            if target == '~' or target.startswith('~/'):
                target = os.path.expanduser(target)
            elif not target.startswith('/'):
                target = os.path.join(current_dir, target)
            
            try:
                if os.path.exists(target):
                    current_dir = os.path.realpath(target)
            except (OSError, ValueError) as e:
                logger.debug(f"Could not resolve path {target}: {e}")
                pass
        
        result.append((command, current_dir))
    
    return result

def display_entries(entries, show_shell=False, show_timestamp=False, show_scores=False):
    """Display history entries in a formatted way with error handling"""
    if not entries:
        print("No entries found.")
        return
    
    try:
        for i, item in enumerate(entries):
            if isinstance(item, tuple):
                entry, score = item
            else:
                entry = item
                score = None
            
            timestamp_str = datetime.fromtimestamp(entry.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            shell_short = entry.shell_id[:8] if show_shell else ""
            tty_info = f"({entry.tty})" if entry.tty else ""
            score_info = f"[{score:.2f}]" if show_scores and score is not None else ""
            
            if show_timestamp:
                print(f"[{timestamp_str}] {shell_short} {tty_info} {score_info} {entry.directory}")
            print(f"   {entry.command}")
            if show_timestamp:
                print()
    except Exception as e:
        logger.error(f"Error displaying entries: {e}")
        print("Error displaying history entries.")

def display_sidebar(db, width=50):
    """Display a sidebar with recent history panels"""
    try:
        # Get terminal width
        try:
            import shutil
            term_width = shutil.get_terminal_size().columns
        except:
            term_width = 80
        
        # Calculate sidebar width
        sidebar_width = min(width, term_width // 3)
        
        # Get recent data
        recent_global = db.get_recent_entries(8)
        current_dir = os.getcwd()
        recent_local = db.get_entries_by_directory(current_dir)[:6]
        
        # Create sidebar content
        sidebar = []
        sidebar.append("=" * sidebar_width)
        sidebar.append("📊 Recent History Sidebar")
        sidebar.append("=" * sidebar_width)
        
        # Global commands panel
        sidebar.append("")
        sidebar.append("🌍 Recent Global Commands")
        sidebar.append("-" * sidebar_width)
        if recent_global:
            for i, entry in enumerate(recent_global, 1):
                cmd = entry.command[:sidebar_width-10] + "..." if len(entry.command) > sidebar_width-10 else entry.command
                sidebar.append(f"{i:2d}. {cmd}")
        else:
            sidebar.append("No recent commands")
        
        # Local commands panel
        sidebar.append("")
        sidebar.append(f"📁 Recent in {os.path.basename(current_dir)}")
        sidebar.append("-" * sidebar_width)
        if recent_local:
            for i, entry in enumerate(recent_local, 1):
                cmd = entry.command[:sidebar_width-10] + "..." if len(entry.command) > sidebar_width-10 else entry.command
                sidebar.append(f"{i:2d}. {cmd}")
        else:
            sidebar.append("No commands in this dir")
        
        # Quick stats panel
        sidebar.append("")
        sidebar.append("📈 Quick Stats")
        sidebar.append("-" * sidebar_width)
        stats = db.get_stats()
        sidebar.append(f"Total: {stats['total_entries']}")
        sidebar.append(f"Directories: {stats['unique_directories']}")
        sidebar.append(f"Shells: {stats['unique_shells']}")
        
        # Top commands panel
        sidebar.append("")
        sidebar.append("🔥 Top Commands")
        sidebar.append("-" * sidebar_width)
        top_cmds = db.get_top_commands(5)
        for cmd, count in top_cmds:
            cmd_short = cmd[:sidebar_width-8] + "..." if len(cmd) > sidebar_width-8 else cmd
            sidebar.append(f"{cmd_short} ({count})")
        
        sidebar.append("")
        sidebar.append("=" * sidebar_width)
        sidebar.append("💡 Tip: Use 'hh --help' for more options")
        
        # Print sidebar
        for line in sidebar:
            print(line)
            
    except Exception as e:
        logger.error(f"Error displaying sidebar: {e}")
        print("Error displaying sidebar.")

def display_stats(db):
    """Display database statistics with error handling"""
    try:
        stats = db.get_stats()
        print("Database Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Unique directories: {stats['unique_directories']}")
        print(f"  Unique shells: {stats['unique_shells']}")
        print(f"  Unique TTYs: {stats['unique_ttys']}")
        
        if stats['date_range']:
            start_time, end_time = stats['date_range']
            start_date = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
            end_date = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  Date range: {start_date} to {end_date}")
        
        print("\nTop Directories:")
        for directory, count in db.get_top_directories(5):
            print(f"  {directory}: {count} commands")
        
        print("\nTop Commands:")
        for command, count in db.get_top_commands(5):
            # Truncate long commands
            cmd_display = command[:60] + "..." if len(command) > 60 else command
            print(f"  {cmd_display}: {count} times")
    except Exception as e:
        logger.error(f"Error displaying stats: {e}")
        print("Error displaying database statistics.")

def usage():
    print("Enhanced hhistory - Timeline + Directory + Session History (TTY+PID)")
    print()
    print("Usage:")
    print("  hh [options] [path]")
    print()
    print("Options:")
    print("  --timeline, -t           Show timeline view")
    print("  --shell, -s              Show shell information")
    print("  --recent, -r [N]         Show recent N commands (default: 50)")
    print("  --search, -q <query>     Search commands")
    print("  --fuzzy, -f <query>      Fuzzy search commands")
    print("  --sidebar                Show recent history sidebar")
    print("  --all, -a                Show all history")
    print("  --stats                  Show database statistics")
    print("  --cleanup [days]         Clean up old session databases")
    print("  --cleanup-dead           Clean up dead shell databases")
    print("  --help, -h               Show this help")
    print()
    print("Examples:")
    print("  hh .                     Show commands for current directory")
    print("  hh /path/to/dir          Show commands for specific directory")
    print("  hh --timeline            Show timeline of all commands")
    print("  hh --recent 20           Show 20 most recent commands")
    print("  hh --search 'git'        Search for commands containing 'git'")
    print("  hh --fuzzy 'git'         Fuzzy search for git-related commands")
    print("  hh --sidebar             Show recent history sidebar")
    print("  hh --stats               Show database statistics")
    print("  hh --cleanup 30          Clean up sessions older than 30 days")
    print("  hh --cleanup-dead        Clean up dead shell databases")
    sys.exit(2)

def main():
    parser = argparse.ArgumentParser(description='Enhanced contextual history (TTY+PID)')
    parser.add_argument('path', nargs='?', help='Directory path to show history for')
    parser.add_argument('--timeline', '-t', action='store_true', help='Show timeline view')
    parser.add_argument('--shell', '-s', action='store_true', help='Show shell information')
    parser.add_argument('--recent', '-r', type=int, nargs='?', const=50, metavar='N', help='Show recent N commands')
    parser.add_argument('--search', '-q', type=str, metavar='QUERY', help='Search commands')
    parser.add_argument('--fuzzy', '-f', type=str, metavar='QUERY', help='Fuzzy search commands')
    parser.add_argument('--sidebar', action='store_true', help='Show recent history sidebar')
    parser.add_argument('--all', '-a', action='store_true', help='Show all history')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--cleanup', type=int, nargs='?', const=30, metavar='DAYS', help='Clean up old session databases')
    parser.add_argument('--cleanup-dead', action='store_true', help='Clean up dead shell databases')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Enable debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize global history
    try:
        global_history = GlobalHistory()
    except Exception as e:
        logger.error(f"Could not initialize global history: {e}")
        print("Error: Could not initialize history system.")
        sys.exit(1)
    
    # Handle cleanup operations
    if args.cleanup_dead:
        try:
            removed = global_history.cleanup_dead_shells()
            print(f"Cleaned up {removed} dead shell databases")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            print("Error during cleanup operation.")
        return
    
    if args.cleanup is not None:
        try:
            removed = global_history.cleanup_old_sessions(args.cleanup)
            print(f"Cleaned up {removed} old session databases")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            print("Error during cleanup operation.")
        return
    
    # If no arguments, update history from current shell
    if len(sys.argv) == 1:
        try:
            shell_id = get_or_create_shell_id()
            session_db = SessionDB(shell_id)
            commands = parse_bash_history()
            command_dir_pairs = track_directory_changes(commands)
            
            # Add new entries to session database
            success_count = 0
            for command, directory in command_dir_pairs:
                if session_db.add_entry(command, directory):
                    success_count += 1
            
            if success_count > 0:
                print(f"Added {success_count} commands to history")
            
            # Show current directory history (merged from all sessions)
            current_dir = os.getcwd()
            entries = global_history.get_entries_by_directory(current_dir)
            print(f"History for: {current_dir}")
            display_entries(entries)
        except Exception as e:
            logger.error(f"Error updating history: {e}")
            print("Error: Could not update history.")
            sys.exit(1)
        return
    
    # Handle different query modes
    try:
        if args.sidebar:
            display_sidebar(global_history)
        
        elif args.stats:
            display_stats(global_history)
        
        elif args.timeline:
            entries = global_history.get_timeline()
            print("Timeline View:")
            display_entries(entries, show_shell=args.shell, show_timestamp=True)
        
        elif args.recent is not None:
            entries = global_history.get_recent_entries(args.recent)
            print(f"Recent {args.recent} commands:")
            display_entries(entries, show_shell=args.shell, show_timestamp=True)
        
        elif args.search:
            entries = global_history.search_commands(args.search)
            print(f"Search results for '{args.search}':")
            display_entries(entries, show_shell=args.shell, show_timestamp=True)
        
        elif args.fuzzy:
            entries = global_history.fuzzy_search_commands(args.fuzzy)
            print(f"Fuzzy search results for '{args.fuzzy}':")
            display_entries(entries, show_shell=args.shell, show_timestamp=True, show_scores=True)
        
        elif args.all:
            entries = global_history.get_recent_entries(1000)  # Get a lot of entries
            print("All History:")
            display_entries(entries, show_shell=args.shell, show_timestamp=True)
        
        elif args.path:
            # Show history for specific directory
            target_dir = os.path.realpath(args.path)
            entries = global_history.get_entries_by_directory(target_dir)
            print(f"History for: {target_dir}")
            display_entries(entries, show_shell=args.shell, show_timestamp=True)
        
        else:
            usage()
    except Exception as e:
        logger.error(f"Error during query: {e}")
        print("Error: Could not complete the requested operation.")
        sys.exit(1)

if __name__ == "__main__":
    main()

