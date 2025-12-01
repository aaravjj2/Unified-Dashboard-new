# Create and activate a virtual environment, then install requirements
# Usage: from PowerShell prompt run: .\Dash\setup_venv.ps1
param(
    [string]$venvPath = "C:\Aarav\fin_env\Dash\.venv",
    [string]$requirements = "C:\Aarav\fin_env\requirements.txt"
)

Write-Host "Creating virtual environment at $venvPath"
python -m venv $venvPath
Write-Host "Activating virtual environment"
# Activate the venv for this session
& "$venvPath\Scripts\Activate.ps1"

if (Test-Path $requirements) {
    Write-Host "Installing requirements from $requirements"
    pip install -r $requirements
} else {
    Write-Host "requirements.txt not found at $requirements; you can pip install dash manually: pip install dash"
}

Write-Host "Done. To activate this venv in future sessions run: & '$venvPath\Scripts\Activate.ps1'"
