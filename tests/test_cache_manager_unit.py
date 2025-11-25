"""
Unit Tests for Cache Manager

Tests individual methods of CacheManager with specific scenarios.
Requirements: 6.1, 6.2, 6.3, 6.5
"""

import pytest
import tempfile
import os
import json
import time
import threading
from datetime import datetime, timedelta
from financial_dashboard.utils.cache_manager import CacheManager


class TestCacheManagerUnit:
    """Unit tests for CacheManager"""
    
    def test_load_from_disk_with_valid_json(self):
        """Test load_from_disk with valid JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
            test_data = {
                'detailed': [{'ticker': 'AAPL', 'current_price': 150.0}],
                'tickers': ['AAPL']
            }
            json.dump(test_data, f)
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            loaded = cache_manager.load_from_disk()
            
            assert loaded == test_data
            assert loaded['detailed'][0]['ticker'] == 'AAPL'
            assert loaded['detailed'][0]['current_price'] == 150.0
        
        finally:
            os.remove(cache_file)
    
    def test_load_from_disk_with_missing_file(self):
        """Test load_from_disk with missing file returns empty dict"""
        cache_file = '/tmp/nonexistent_cache_file_12345.json'
        
        memory_cache = {}
        cache_manager = CacheManager(cache_file, memory_cache)
        
        loaded = cache_manager.load_from_disk()
        
        assert loaded == {}
    
    def test_load_from_disk_with_corrupted_json(self):
        """Test load_from_disk with corrupted JSON handles gracefully"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
            f.write('{ invalid json content }}}')
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            loaded = cache_manager.load_from_disk()
            
            assert loaded == {}
        
        finally:
            os.remove(cache_file)
    
    def test_save_to_disk_creates_file_with_correct_structure(self):
        """Test save_to_disk creates file with correct structure"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            test_data = {
                'detailed': [{'ticker': 'MSFT', 'current_price': 300.0}],
                'tickers': ['MSFT']
            }
            
            success = cache_manager.save_to_disk(test_data)
            
            assert success is True
            assert os.path.exists(cache_file)
            
            # Verify file content
            with open(cache_file, 'r') as f:
                saved_data = json.load(f)
            
            assert 'detailed' in saved_data
            assert 'tickers' in saved_data
            assert 'generated_at' in saved_data  # Timestamp should be added
            assert saved_data['detailed'][0]['ticker'] == 'MSFT'
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_save_to_disk_atomic_write(self):
        """Test save_to_disk uses atomic write (no partial writes)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            # Write initial data
            data1 = {'detailed': [{'ticker': 'A'}], 'tickers': ['A']}
            cache_manager.save_to_disk(data1)
            
            # Write new data
            data2 = {'detailed': [{'ticker': 'B'}], 'tickers': ['B']}
            cache_manager.save_to_disk(data2)
            
            # Verify only latest data is present (no corruption)
            loaded = cache_manager.load_from_disk()
            assert loaded['detailed'][0]['ticker'] == 'B'
            assert len(loaded['detailed']) == 1
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_is_cache_fresh_with_various_timestamps(self):
        """Test is_cache_fresh with various timestamps"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        # Delete the temp file so we start with no cache
        os.remove(cache_file)
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            # Test with no cache
            assert cache_manager.is_cache_fresh(300) is False
            
            # Save data (creates timestamp)
            cache_manager.save_to_disk({'detailed': [], 'tickers': []})
            
            # Should be fresh immediately
            assert cache_manager.is_cache_fresh(300) is True
            
            # Should be stale with very short TTL
            assert cache_manager.is_cache_fresh(0) is False
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_get_cache_timestamp_sources(self):
        """Test get_cache_timestamp tries multiple sources"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        # Delete the temp file so we start with no cache
        os.remove(cache_file)
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            # No cache - should return None
            assert cache_manager.get_cache_timestamp() is None
            
            # Save to disk - should get timestamp from _memory_loaded_at (set by save_to_disk)
            cache_manager.save_to_disk({'detailed': [], 'tickers': []})
            timestamp1 = cache_manager.get_cache_timestamp()
            assert timestamp1 is not None
            assert isinstance(timestamp1, float)
            
            # Wait a bit and save again - timestamp should update
            time.sleep(0.1)
            cache_manager.save_to_disk({'detailed': [{'ticker': 'TEST'}], 'tickers': ['TEST']})
            timestamp2 = cache_manager.get_cache_timestamp()
            assert timestamp2 > timestamp1  # Should be newer
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_update_cache_syncs_memory_and_disk(self):
        """Test update_cache updates both memory and disk"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            test_data = {
                'detailed': [{'ticker': 'GOOGL', 'current_price': 140.0}],
                'tickers': ['GOOGL']
            }
            
            success = cache_manager.update_cache(test_data)
            
            assert success is True
            
            # Verify memory cache
            assert 'results' in memory_cache
            assert memory_cache['results']['detailed'][0]['ticker'] == 'GOOGL'
            assert 'loaded_at' in memory_cache
            
            # Verify disk cache
            loaded = cache_manager.load_from_disk()
            assert loaded['detailed'][0]['ticker'] == 'GOOGL'
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_clear_cache_removes_both_memory_and_disk(self):
        """Test clear_cache removes both memory and disk cache"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            # Add data to both caches
            test_data = {'detailed': [{'ticker': 'TSLA'}], 'tickers': ['TSLA']}
            cache_manager.update_cache(test_data)
            
            assert 'results' in memory_cache
            assert os.path.exists(cache_file)
            
            # Clear cache
            success = cache_manager.clear_cache()
            
            assert success is True
            assert 'results' not in memory_cache
            assert not os.path.exists(cache_file)
        
        finally:
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except:
                    pass
    
    def test_thread_safety_concurrent_reads(self):
        """Test thread safety with concurrent reads"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            # Save initial data
            cache_manager.save_to_disk({'detailed': [{'ticker': 'NVDA'}], 'tickers': ['NVDA']})
            
            results = []
            errors = []
            
            def read_cache():
                try:
                    for _ in range(10):
                        data = cache_manager.load_from_disk()
                        results.append(data)
                except Exception as e:
                    errors.append(e)
            
            # Create multiple threads
            threads = [threading.Thread(target=read_cache) for _ in range(5)]
            
            # Start all threads
            for t in threads:
                t.start()
            
            # Wait for completion
            for t in threads:
                t.join()
            
            # Verify no errors
            assert len(errors) == 0
            assert len(results) == 50  # 5 threads * 10 reads each
            
            # Verify all reads got valid data
            for data in results:
                assert 'detailed' in data
                assert data['detailed'][0]['ticker'] == 'NVDA'
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_thread_safety_concurrent_writes(self):
        """Test thread safety with concurrent writes"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            errors = []
            
            def write_cache(ticker):
                try:
                    for i in range(5):
                        data = {'detailed': [{'ticker': ticker, 'id': i}], 'tickers': [ticker]}
                        cache_manager.save_to_disk(data)
                except Exception as e:
                    errors.append(e)
            
            # Create multiple threads writing different data
            threads = [
                threading.Thread(target=write_cache, args=(f'TICK{i}',))
                for i in range(3)
            ]
            
            # Start all threads
            for t in threads:
                t.start()
            
            # Wait for completion
            for t in threads:
                t.join()
            
            # Verify no errors (atomic writes prevent corruption)
            assert len(errors) == 0
            
            # Verify file is valid JSON (not corrupted)
            loaded = cache_manager.load_from_disk()
            assert 'detailed' in loaded
            assert 'tickers' in loaded
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_get_cache_info(self):
        """Test get_cache_info returns correct metadata"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        # Delete the temp file so we start with no cache
        os.remove(cache_file)
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            # Get info with no cache
            info = cache_manager.get_cache_info()
            assert info['path'] == cache_file
            assert info['file_exists'] is False
            assert info['timestamp'] is None
            assert info['is_fresh'] is False
            
            # Add cache
            cache_manager.update_cache({
                'detailed': [{'ticker': 'AMD'}, {'ticker': 'INTC'}],
                'tickers': ['AMD', 'INTC']
            })
            
            # Get info with cache
            info = cache_manager.get_cache_info()
            assert info['file_exists'] is True
            assert info['timestamp'] is not None
            assert info['is_fresh'] is True
            assert info['memory_cache_present'] is True
            assert info['record_count'] == 2
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
