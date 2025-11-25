"""
Unit tests for CacheManager

Tests thread-safety, atomic writes, TTL validation, and cache operations.
"""

import pytest
import os
import json
import time
import tempfile
import threading
from pathlib import Path
from financial_dashboard.utils.cache_manager import CacheManager


@pytest.fixture
def temp_cache_file():
    """Create a temporary cache file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
    temp_tmp = temp_path + '.tmp'
    if os.path.exists(temp_tmp):
        os.remove(temp_tmp)


@pytest.fixture
def memory_cache():
    """Create a fresh memory cache dict."""
    return {}


def test_cache_manager_initialization(temp_cache_file, memory_cache):
    """Test CacheManager initializes correctly."""
    cm = CacheManager(temp_cache_file, memory_cache, ttl_seconds=60)
    assert cm.cache_file_path == temp_cache_file
    assert cm.ttl_seconds == 60
    assert cm._lock is not None


def test_save_and_load_disk(temp_cache_file, memory_cache):
    """Test atomic disk save and load."""
    cm = CacheManager(temp_cache_file, memory_cache, ttl_seconds=300)
    
    test_data = {
        'detailed': [
            {'ticker': 'AAPL', 'price': 150.0},
            {'ticker': 'MSFT', 'price': 300.0}
        ],
        'summary': 'Test data'
    }
    
    # Save to disk
    success = cm.save_to_disk(test_data)
    assert success is True
    assert os.path.exists(temp_cache_file)
    
    # Verify temp file was removed (atomic write complete)
    temp_tmp = temp_cache_file + '.tmp'
    assert not os.path.exists(temp_tmp)
    
    # Load from disk
    loaded = cm.load_from_disk()
    assert 'detailed' in loaded
    assert len(loaded['detailed']) == 2
    assert loaded['detailed'][0]['ticker'] == 'AAPL'


def test_cache_freshness(temp_cache_file, memory_cache):
    """Test TTL and freshness checks."""
    cm = CacheManager(temp_cache_file, memory_cache, ttl_seconds=2)
    
    test_data = {'detailed': [{'ticker': 'AAPL'}], 'generated_at': time.time()}
    memory_cache['results'] = test_data
    memory_cache['loaded_at'] = time.time()
    
    # Should be fresh immediately
    assert cm.is_cache_fresh() is True
    
    # Wait for TTL to expire
    time.sleep(2.5)
    
    # Should be stale now
    assert cm.is_cache_fresh() is False


def test_update_cache_atomic(temp_cache_file, memory_cache):
    """Test that cache updates are atomic (memory + disk)."""
    cm = CacheManager(temp_cache_file, memory_cache, ttl_seconds=300)
    
    test_data = {
        'detailed': [{'ticker': 'GOOGL', 'price': 2800.0}],
        'summary': 'Updated data'
    }
    
    success = cm.update_cache(test_data)
    assert success is True
    
    # Check memory cache was updated
    assert 'results' in memory_cache
    assert memory_cache['results']['detailed'][0]['ticker'] == 'GOOGL'
    
    # Check disk cache was updated
    with open(temp_cache_file, 'r') as f:
        disk_data = json.load(f)
    assert disk_data['detailed'][0]['ticker'] == 'GOOGL'


def test_get_operations(temp_cache_file, memory_cache):
    """Test cache get operations."""
    cm = CacheManager(temp_cache_file, memory_cache, ttl_seconds=300)
    
    memory_cache['test_key'] = 'test_value'
    memory_cache['results'] = {'data': 'sample'}
    
    # Get specific key
    assert cm.get('test_key') == 'test_value'
    
    # Get all cache
    all_cache = cm.get()
    assert 'test_key' in all_cache
    assert 'results' in all_cache
    
    # Get non-existent key
    assert cm.get('nonexistent') == {}


def test_thread_safety(temp_cache_file, memory_cache):
    """Test that CacheManager operations are thread-safe."""
    cm = CacheManager(temp_cache_file, memory_cache, ttl_seconds=300)
    
    errors = []
    
    def writer_thread(thread_id):
        try:
            for i in range(10):
                data = {
                    'detailed': [{'thread': thread_id, 'iteration': i}],
                    'timestamp': time.time()
                }
                cm.update_cache(data)
                time.sleep(0.01)
        except Exception as e:
            errors.append(e)
    
    # Run 5 concurrent writer threads
    threads = []
    for i in range(5):
        t = threading.Thread(target=writer_thread, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Should complete without errors
    assert len(errors) == 0
    
    # Cache file should exist and be valid JSON
    assert os.path.exists(temp_cache_file)
    with open(temp_cache_file, 'r') as f:
        final_data = json.load(f)
    
    assert 'detailed' in final_data
    assert '_cache_metadata' in final_data


def test_corrupted_cache_recovery(temp_cache_file, memory_cache):
    """Test recovery from corrupted cache file."""
    cm = CacheManager(temp_cache_file, memory_cache, ttl_seconds=300)
    
    # Write corrupted JSON
    with open(temp_cache_file, 'w') as f:
        f.write("{invalid json content")
    
    # Should return empty dict without crashing
    loaded = cm.load_from_disk()
    assert loaded == {}


def test_get_cache_info(temp_cache_file, memory_cache):
    """Test cache info retrieval."""
    cm = CacheManager(temp_cache_file, memory_cache, ttl_seconds=300)
    
    test_data = {'detailed': [{'ticker': 'AAPL'}], 'generated_at': time.time()}
    cm.update_cache(test_data)
    
    info = cm.get_cache_info()
    assert 'age_seconds' in info
    assert 'is_fresh' in info
    assert 'ttl_seconds' in info
    assert info['ttl_seconds'] == 300


def test_missing_cache_directory_creation(memory_cache):
    """Test that CacheManager creates missing cache directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, 'nested', 'cache', 'test.json')
        
        cm = CacheManager(cache_path, memory_cache, ttl_seconds=300)
        
        # Directory should be created
        assert os.path.exists(os.path.dirname(cache_path))
        
        # Should be able to save
        test_data = {'detailed': [{'test': 'data'}]}
        success = cm.save_to_disk(test_data)
        assert success is True
        assert os.path.exists(cache_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
