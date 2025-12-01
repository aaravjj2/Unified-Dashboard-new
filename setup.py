from setuptools import setup, find_packages

setup(
    name='unified-dashboard',
    version='0.0.1',
    description='Unified Financial Dashboard',
    packages=find_packages(include=['financial_dashboard', 'financial_dashboard.*']),
    include_package_data=True,
)
