"""
Azure ML Lab - Configuration & Authentication

Handles Azure ML workspace connection, authentication, and configuration.
Phase 4: Real Azure ML integration with secure credential handling.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from financial_dashboard.utils.azure_guard import guard as enforce_azure_guard

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

class AzureMLConfig:
    """Azure ML workspace configuration with secure credential handling."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Azure ML Workspace details (from environment or .env)
        self.subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID', '')
        self.resource_group = os.getenv('AZURE_RESOURCE_GROUP', 'unified-dashboard-rg')
        self.workspace_name = os.getenv('AZURE_ML_WORKSPACE_NAME', 'unified-dashboard-ml')
        
        # Azure Authentication
        self.tenant_id = os.getenv('AZURE_TENANT_ID', '')
        self.client_id = os.getenv('AZURE_CLIENT_ID', '')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET', '')
        
        # ML Endpoint configuration
        self.endpoint_name = os.getenv('AZURE_ML_ENDPOINT_NAME', 'portfolio-prediction-v1')
        self.endpoint_url = os.getenv('AZURE_ML_ENDPOINT_URL', '')
        self.api_key = os.getenv('AZURE_ML_API_KEY', '')
        
        # Feature flags
        self.use_mock_fallback = os.getenv('AZURE_ML_USE_MOCK', 'true').lower() == 'true'
        self.enable_caching = os.getenv('AZURE_ML_ENABLE_CACHE', 'true').lower() == 'true'
        self.cache_ttl_seconds = int(os.getenv('AZURE_ML_CACHE_TTL', '3600'))
        
        # Logging
        self.debug_mode = os.getenv('AZURE_ML_DEBUG', 'false').lower() == 'true'
        
        logger.info(f"Azure ML Config initialized: workspace={self.workspace_name}, mock_fallback={self.use_mock_fallback}")
    
    def is_configured(self) -> bool:
        """
        Check if Azure ML credentials are properly configured.
        
        Returns:
            bool: True if all required credentials are present
        """
        required_fields = [
            self.subscription_id,
            self.resource_group,
            self.workspace_name
        ]
        
        # For service principal auth
        if self.client_id and self.client_secret:
            return all(required_fields) and bool(self.tenant_id)
        
        # For endpoint-based auth
        if self.endpoint_url and self.api_key:
            return True
        
        # If nothing is configured, we'll use mock mode
        logger.warning("⚠️ Azure ML credentials not fully configured - using mock mode")
        return False
    
    def get_status(self) -> Dict:
        """
        Get configuration status for diagnostics.
        
        Returns:
            dict: Configuration status and availability
        """
        return {
            'configured': self.is_configured(),
            'mock_mode': self.use_mock_fallback or not self.is_configured(),
            'workspace_name': self.workspace_name if self.workspace_name else 'NOT_SET',
            'endpoint_name': self.endpoint_name if self.endpoint_name else 'NOT_SET',
            'has_subscription_id': bool(self.subscription_id),
            'has_endpoint_url': bool(self.endpoint_url),
            'has_api_key': bool(self.api_key),
            'caching_enabled': self.enable_caching,
            'cache_ttl': self.cache_ttl_seconds,
            'debug_mode': self.debug_mode
        }


# =============================================================================
# AUTHENTICATION
# =============================================================================

def authenticate_azure_ml(config: AzureMLConfig) -> Tuple[Optional[object], Optional[str]]:
    """
    Authenticate to Azure ML workspace using available credentials.
    
    Phase 4: Attempts multiple authentication methods in order:
    1. Service Principal (if client_id/client_secret provided)
    2. Default Azure Credential (for local dev with Azure CLI)
    3. Falls back to mock mode if no credentials available
    
    Args:
        config: AzureMLConfig instance
    
    Returns:
        tuple: (MLClient or None, error_message or None)
    """
    try:
        enforce_azure_guard(
            action="azure_ml_lab.authenticate",
            metadata={'workspace': config.workspace_name}
        )
    except RuntimeError as guard_error:
        logger.warning("Azure ML authentication blocked: %s", guard_error)
        return None, str(guard_error)

    if not config.is_configured():
        logger.warning("Azure ML not configured - using mock mode")
        return None, "Azure ML credentials not configured"
    
    try:
        # Phase 4: Import Azure ML SDK only if configured
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential, ClientSecretCredential
        
        # Method 1: Service Principal (production)
        if config.client_id and config.client_secret and config.tenant_id:
            logger.info("Authenticating with Service Principal...")
            credential = ClientSecretCredential(
                tenant_id=config.tenant_id,
                client_id=config.client_id,
                client_secret=config.client_secret
            )
            
            ml_client = MLClient(
                credential=credential,
                subscription_id=config.subscription_id,
                resource_group_name=config.resource_group,
                workspace_name=config.workspace_name
            )
            
            # Test connection
            workspace = ml_client.workspaces.get(config.workspace_name)
            logger.info(f"✅ Connected to Azure ML workspace: {workspace.name}")
            return ml_client, None
        
        # Method 2: Default Azure Credential (local dev)
        logger.info("Authenticating with DefaultAzureCredential...")
        credential = DefaultAzureCredential()
        
        ml_client = MLClient(
            credential=credential,
            subscription_id=config.subscription_id,
            resource_group_name=config.resource_group,
            workspace_name=config.workspace_name
        )
        
        # Test connection
        workspace = ml_client.workspaces.get(config.workspace_name)
        logger.info(f"✅ Connected to Azure ML workspace: {workspace.name}")
        return ml_client, None
    
    except ImportError as e:
        error_msg = f"Azure ML SDK not installed: {e}"
        logger.warning(error_msg)
        return None, error_msg
    
    except Exception as e:
        error_msg = f"Azure ML authentication failed: {e}"
        logger.error(error_msg)
        return None, error_msg


# =============================================================================
# HELLO WORLD TEST
# =============================================================================

def test_azure_ml_connection(config: AzureMLConfig) -> Dict:
    """
    Test Azure ML connection with a simple "Hello World" validation.
    
    Args:
        config: AzureMLConfig instance
    
    Returns:
        dict: Test results with status and details
    """
    logger.info("🔍 Testing Azure ML connection...")
    
    result = {
        'status': 'unknown',
        'message': '',
        'workspace_info': {},
        'timestamp': None
    }

    try:
        enforce_azure_guard(
            action="azure_ml_lab.test_connection",
            metadata={'workspace': config.workspace_name}
        )
    except RuntimeError as guard_error:
        result['status'] = 'blocked'
        result['message'] = str(guard_error)
        logger.warning("Azure ML connection test blocked: %s", guard_error)
        return result
    
    # Check configuration
    if not config.is_configured():
        result['status'] = 'mock_mode'
        result['message'] = 'Azure ML not configured - using mock mode'
        logger.warning(result['message'])
        return result
    
    # Attempt authentication
    ml_client, error = authenticate_azure_ml(config)
    
    if ml_client is None:
        result['status'] = 'error'
        result['message'] = error or 'Authentication failed'
        logger.error(f"❌ {result['message']}")
        return result
    
    # Test workspace access
    try:
        workspace = ml_client.workspaces.get(config.workspace_name)
        
        result['status'] = 'success'
        result['message'] = f'Successfully connected to {workspace.name}'
        result['workspace_info'] = {
            'name': workspace.name,
            'resource_group': workspace.resource_group,
            'location': workspace.location,
            'description': workspace.description or 'N/A'
        }
        result['timestamp'] = workspace.provisioning_state
        
        logger.info(f"✅ {result['message']}")
        logger.info(f"   Location: {workspace.location}")
        logger.info(f"   State: {workspace.provisioning_state}")
        
        # Test endpoint availability (if configured)
        if config.endpoint_url:
            try:
                endpoint = ml_client.online_endpoints.get(name=config.endpoint_name)
                result['endpoint_info'] = {
                    'name': endpoint.name,
                    'scoring_uri': endpoint.scoring_uri,
                    'state': endpoint.provisioning_state
                }
                logger.info(f"✅ Endpoint '{config.endpoint_name}' available")
            except Exception as e:
                logger.warning(f"⚠️ Endpoint '{config.endpoint_name}' not found: {e}")
                result['endpoint_info'] = {'error': str(e)}
        
        return result
    
    except Exception as e:
        result['status'] = 'error'
        result['message'] = f'Workspace access failed: {e}'
        logger.error(f"❌ {result['message']}")
        return result


# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

# Create global config instance
azure_ml_config = AzureMLConfig()

logger.info("✓ Azure ML configuration module loaded")
