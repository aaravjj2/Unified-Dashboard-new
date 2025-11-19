"""
Azure Contracts Module

Defines standard contracts, schemas, and stub clients for Azure ML integration.
"""

from phase4_hybrid_stubs.azure_contracts.azure_contract_definitions import (
    ContractInputSpec,
    ContractOutputSpec,
    ModelType,
    ForecastHorizon,
    contract_to_json,
    validate_contract,
    create_mock_input,
    create_mock_output
)

from phase4_hybrid_stubs.azure_contracts.azure_io_schema import (
    load_schema,
    validate_payload,
    IOSchemaVersion
)

from phase4_hybrid_stubs.azure_contracts.azure_stub_clients import (
    AzureMLStubClient,
    AzureBlobStubClient,
    AzureMonitorStubClient
)

__all__ = [
    'ContractInputSpec',
    'ContractOutputSpec',
    'ModelType',
    'ForecastHorizon',
    'contract_to_json',
    'validate_contract',
    'create_mock_input',
    'create_mock_output',
    'load_schema',
    'validate_payload',
    'IOSchemaVersion',
    'AzureMLStubClient',
    'AzureBlobStubClient',
    'AzureMonitorStubClient'
]
