<#
.SYNOPSIS
  Start/stop/status the Market Trends and Unified Dashboard Python servers together.

.DESCRIPTION
  This helper starts the two Dash-based servers used in development:
    - Dash/market_trends_dash.py (the full Trends app)
    - Dash/market_dashboard.py (the unified dashboard that embeds/tunnels tabs)

  It supports three actions: start, stop, status. When starting it will spawn
  both Python processes (using a venv python by default), save PIDs to a JSON
  file in the logs directory, and print the PIDs so you can attach to logs or
  open the apps. Use the 'stop' action to terminate both processes.

USAGE
  # start both servers (default paths assume the repository layout used during dev)
  .\run_all.ps1 -Action start

  # stop previously started servers
  .\run_all.ps1 -Action stop

  # show status
  .\run_all.ps1 -Action status

PARAMETERS
  -Action: start | stop | status (default: start)
  -VenvPython: Full path to python.exe to use to run the servers (defaults to venv used in this project)
  -TrendsScript, -DashboardScript: Paths to the two scripts to run
  -LogDir: directory to store PID file and optional logs

NOTES
  - This script starts processes detached from the current shell. Logs are not
    redirected by default; if you want logs, run the server commands manually or
    adapt the script to redirect output.
  - The default venv python path is an inferred path used during development;
    override with -VenvPython if you use a different environment.
#>

param(
  [ValidateSet('start','stop','status')]
  [string]$Action = 'start',
  [string]$VenvPython = 'C:/Aarav/fin_env/Gradio/.venv/Scripts/python.exe',
  [string]$TrendsScript = 'c:/Aarav/fin_env/Dash/market_trends_dash.py',
  [string]$DashboardScript = 'c:/Aarav/fin_env/Dash/market_dashboard.py',
  [string]$LogDir = 'c:/Aarav/fin_env/Dash/logs',
  [switch]$StartTrends
)

if(-not (Test-Path $LogDir)){
  New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$PidFile = Join-Path $LogDir 'run_all_pids.json'

# inline helper for saving and loading PIDs (avoid custom function names that trip analyzers)
function _SavePidFile($arr){ $arr | ConvertTo-Json -Depth 5 | Set-Content -Path $PidFile -Encoding UTF8 }
function _LoadPidFile(){ if(Test-Path $PidFile){ Get-Content $PidFile -Raw | ConvertFrom-Json } else { @() } }

switch($Action){
    'start' {
        if(Test-Path $PidFile){ Write-Host "PID file exists at $PidFile. Run `-Action stop` first or remove the file to start fresh."; exit 1 }

        # verify python
        if(-not (Test-Path $VenvPython)){
            Write-Host "Warning: specified Python not found at $VenvPython. Falling back to 'python' on PATH." -ForegroundColor Yellow
            $VenvPython = 'python'
        }

        $procs = @()

    if($StartTrends){
      Write-Host "Starting Trends server: $TrendsScript"
      $p1 = Start-Process -FilePath $VenvPython -ArgumentList @("$TrendsScript") -WorkingDirectory (Split-Path $TrendsScript) -PassThru
      $procs += @{ name = 'trends'; pid = $p1.Id; started = (Get-Date).ToString('o') }
      Start-Sleep -Milliseconds 300
    } else {
      Write-Host "Skipping separate Trends process (embedding Trends as a native tab in the dashboard). Use -StartTrends to run it separately."
    }

    Write-Host "Starting Unified dashboard: $DashboardScript"
    $p2 = Start-Process -FilePath $VenvPython -ArgumentList @("$DashboardScript") -WorkingDirectory (Split-Path $DashboardScript) -PassThru
    $procs += @{ name = 'dashboard'; pid = $p2.Id; started = (Get-Date).ToString('o') }

  _SavePidFile $procs
        Write-Host "Started processes. PID file written to: $PidFile"
        $procs | ForEach-Object { Write-Host " - $($_.name): PID $($_.pid)" }
    }
  'stop' {
  $items = _LoadPidFile
        if(-not $items -or $items.Count -eq 0){ Write-Host "No PID file or no processes recorded."; exit 0 }
        foreach($it in $items){
            try{
                Write-Host "Stopping $($it.name) (pid $($it.pid))"
                Stop-Process -Id $it.pid -Force -ErrorAction SilentlyContinue
            } catch { }
        }
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        Write-Host "Stopped recorded processes and removed PID file."
    }
  'status' {
  $items = _LoadPidFile
        if(-not $items -or $items.Count -eq 0){ Write-Host "No PID file ($PidFile) found."; exit 0 }
        foreach($it in $items){
            $p = Get-Process -Id $it.pid -ErrorAction SilentlyContinue
            if($p){ Write-Host "$($it.name): RUNNING (pid $($it.pid))" }
            else { Write-Host "$($it.name): NOT RUNNING (pid $($it.pid))" -ForegroundColor Yellow }
        }
    }
}

# end
