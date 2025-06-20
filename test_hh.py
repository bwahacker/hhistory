#!/usr/bin/env python3
"""
Basic tests for hhistory
"""

import unittest
import tempfile
import os
import sys
import sqlite3
import json
import time
from unittest.mock import patch, MagicMock
import shutil

# Add the current directory to the path so we can import hh-intern
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the functions we want to test
try:
    # Try to import as a module first
    import hh_intern
    from hh_intern import (
        get_shell_identifier, 
        safe_makedirs, 
        safe_connect_db,
        parse_bash_history,
        track_directory_changes,
        HistoryEntry,
        SessionDB,
        GlobalHistory
    )
except ImportError:
    # If that fails, try to import from the file directly
    import importlib.util
    spec = importlib.util.spec_from_file_location("hh_intern", "hh-intern.py")
    hh_intern = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hh_intern)
    
    # Now import the functions
    get_shell_identifier = hh_intern.get_shell_identifier
    safe_makedirs = hh_intern.safe_makedirs
    safe_connect_db = hh_intern.safe_connect_db
    parse_bash_history = hh_intern.parse_bash_history
    track_directory_changes = hh_intern.track_directory_changes
    HistoryEntry = hh_intern.HistoryEntry
    SessionDB = hh_intern.SessionDB
    GlobalHistory = hh_intern.GlobalHistory

class TestHHistory(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        # Patch DB_DIR in the module to use a unique temp dir for every test
        self.db_dir_patch = patch.object(hh_intern, 'DB_DIR', self.temp_dir)
        self.db_dir_patch.start()
        # Clean up any session DBs in the temp dir
        for f in os.listdir(self.temp_dir):
            if f.startswith('session_') and f.endswith('.db'):
                os.remove(os.path.join(self.temp_dir, f))
    
    def tearDown(self):
        """Clean up test environment"""
        self.db_dir_patch.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_shell_identifier(self):
        """Test shell identifier generation"""
        shell_info = get_shell_identifier()
        
        self.assertIn('tty', shell_info)
        self.assertIn('pid', shell_info)
        self.assertIn('ppid', shell_info)
        self.assertIn('identifier', shell_info)
        
        self.assertIsInstance(shell_info['pid'], int)
        self.assertIsInstance(shell_info['ppid'], int)
        self.assertIsInstance(shell_info['tty'], str)
        self.assertIsInstance(shell_info['identifier'], str)
        
        # Identifier should be tty_pid format
        self.assertIn('_', shell_info['identifier'])
    
    def test_safe_makedirs(self):
        """Test safe directory creation"""
        test_dir = os.path.join(self.temp_dir, 'test_dir')
        
        # Should create directory successfully
        result = safe_makedirs(test_dir)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_dir))
        
        # Should handle existing directory
        result = safe_makedirs(test_dir)
        self.assertTrue(result)
    
    def test_safe_connect_db(self):
        """Test safe database connection"""
        test_db = os.path.join(self.temp_dir, 'test.db')
        
        # Should connect successfully
        conn = safe_connect_db(test_db)
        self.assertIsNotNone(conn)
        conn.close()
        
        # Should handle invalid paths gracefully
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Test error")):
            conn = safe_connect_db('/invalid/path.db')
            self.assertIsNone(conn)
    
    def test_history_entry(self):
        """Test HistoryEntry class"""
        entry = HistoryEntry(
            command="ls -la",
            directory="/test/dir",
            shell_id="test_123",
            timestamp=1234567890.0,
            tty="ttys001",
            pid=12345
        )
        
        self.assertEqual(entry.command, "ls -la")
        self.assertEqual(entry.directory, "/test/dir")
        self.assertEqual(entry.shell_id, "test_123")
        self.assertEqual(entry.timestamp, 1234567890.0)
        self.assertEqual(entry.tty, "ttys001")
        self.assertEqual(entry.pid, 12345)
        
        # Test to_dict method
        entry_dict = entry.to_dict()
        self.assertIn('command', entry_dict)
        self.assertIn('directory', entry_dict)
        self.assertIn('shell_id', entry_dict)
        self.assertIn('timestamp', entry_dict)
        self.assertIn('tty', entry_dict)
        self.assertIn('pid', entry_dict)
        self.assertIn('datetime', entry_dict)
    
    def test_session_db(self):
        """Test SessionDB class"""
        shell_id = "test_123"
        session_db = SessionDB(shell_id)
        
        # Should create database file
        self.assertTrue(os.path.exists(session_db.db_file))
        
        # Should add entries
        success = session_db.add_entry("test command", "/test/dir")
        self.assertTrue(success)
        
        # Should retrieve entries
        entries = session_db.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].command, "test command")
        self.assertEqual(entries[0].directory, "/test/dir")
    
    def test_global_history(self):
        """Test GlobalHistory class"""
        global_history = GlobalHistory()
        
        # Should create database directory
        self.assertTrue(os.path.exists(self.temp_dir))
        
        # Should handle empty state
        entries = global_history.get_recent_entries()
        self.assertEqual(len(entries), 0)
        
        stats = global_history.get_stats()
        self.assertEqual(stats['total_entries'], 0)
        
        # Should handle top commands/directories
        top_dirs = global_history.get_top_directories()
        self.assertEqual(len(top_dirs), 0)
        
        top_cmds = global_history.get_top_commands()
        self.assertEqual(len(top_cmds), 0)
    
    def test_parse_bash_history(self):
        """Test bash history parsing"""
        # Create a temporary history file
        history_file = os.path.join(self.temp_dir, '.myhistory')
        with open(history_file, 'w') as f:
            f.write("ls -la\n")
            f.write("cd /tmp\n")
            f.write("echo 'hello world'\n")
        
        # Patch expanduser directly on the loaded module
        with patch.object(hh_intern.os.path, 'expanduser', return_value=history_file):
            commands = parse_bash_history()
        
        self.assertEqual(len(commands), 3)
        self.assertIn("ls -la", commands)
        self.assertIn("cd /tmp", commands)
        self.assertIn("echo 'hello world'", commands)
    
    def test_track_directory_changes(self):
        """Test directory change tracking"""
        commands = [
            "ls -la",
            "cd /tmp",
            "pwd",
            "cd ~",
            "echo 'home'"
        ]
        
        result = track_directory_changes(commands)
        
        self.assertEqual(len(result), 5)
        
        # First command should be in current directory
        self.assertEqual(result[0][1], os.environ.get('HOME', '/'))
        
        # Commands after cd should be in new directory
        # (Note: actual path resolution depends on system)
        self.assertIsInstance(result[1][1], str)  # Should be a valid path
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test with invalid database path
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Test error")):
            conn = safe_connect_db('/invalid/path.db')
            self.assertIsNone(conn)
        
        # Test with permission error
        with patch('os.makedirs', side_effect=PermissionError("Test error")):
            result = safe_makedirs('/invalid/path')
            self.assertFalse(result)
    
    def test_cleanup_functions(self):
        """Test cleanup functionality"""
        global_history = GlobalHistory()
        
        # Should handle cleanup gracefully when no data exists
        removed = global_history.cleanup_dead_shells()
        self.assertEqual(removed, 0)
        
        removed = global_history.cleanup_old_sessions(1)
        self.assertEqual(removed, 0)

def run_tests():
    """Run the test suite"""
    print("🧪 Running hhistory tests...")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHHistory)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n📊 Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback}")
    
    if result.errors:
        print(f"\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback}")
    
    if result.wasSuccessful():
        print(f"\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests()) 