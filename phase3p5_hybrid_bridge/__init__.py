"""
Phase 3.5 Hybrid Bridge Package
================================

Unified data exchange and caching between offline analytics and Azure stubs.

Modules:
- data_bridge: Contracts, caching, storage, sync
- integrity_checks: Hash validation, schema diff
- diagnostics: Test suite and validation
"""

__version__ = "3.5.0"

# Export main components
from .data_bridge.data_contracts import (
    ContractType,
    PortfolioAnalyticsContract,
    ExplainabilityContract,
    ForecastContract,
    create_contract,
    validate_contract,
    get_contract_hash
)

from .data_bridge.cache_router import (
    CacheRouter,
    get_global_router,
    get_data,
    store_data,
    sync_to_cloud,
    get_cache_stats
)

from .data_bridge.hybrid_storage_manager import (
    HybridStorageManager,
    get_global_manager,
    save_analytics_bundle,
    load_analytics_bundle,
    list_bundles
)

from .data_bridge.sync_scheduler import (
    SyncScheduler,
    get_global_scheduler,
    sync_manual,
    start_auto_sync,
    stop_auto_sync,
    get_sync_stats
)

from .integrity_checks.data_hash_validator import (
    DataHashValidator,
    get_global_validator,
    validate_file,
    validate_manifest,
    compute_hash
)

from .integrity_checks.schema_diff_checker import (
    SchemaDiffChecker,
    get_global_checker,
    compare_schemas,
    compare_all_schemas,
    generate_report
)


__all__ = [
    # Version
    "__version__",
    
    # Data Contracts
    "ContractType",
    "PortfolioAnalyticsContract",
    "ExplainabilityContract",
    "ForecastContract",
    "create_contract",
    "validate_contract",
    "get_contract_hash",
    
    # Cache Router
    "CacheRouter",
    "get_global_router",
    "get_data",
    "store_data",
    "sync_to_cloud",
    "get_cache_stats",
    
    # Storage Manager
    "HybridStorageManager",
    "get_global_manager",
    "save_analytics_bundle",
    "load_analytics_bundle",
    "list_bundles",
    
    # Sync Scheduler
    "SyncScheduler",
    "get_global_scheduler",
    "sync_manual",
    "start_auto_sync",
    "stop_auto_sync",
    "get_sync_stats",
    
    # Hash Validator
    "DataHashValidator",
    "get_global_validator",
    "validate_file",
    "validate_manifest",
    "compute_hash",
    
    # Schema Diff
    "SchemaDiffChecker",
    "get_global_checker",
    "compare_schemas",
    "compare_all_schemas",
    "generate_report",
]
