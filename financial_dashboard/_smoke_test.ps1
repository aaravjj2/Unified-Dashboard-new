# Simple smoke tests for the local Dash dashboard
# Saves layout and custom.css for inspection

$port = $env:DASH_PORT
if (-not $port) { $port = 8050 }
$root = "http://127.0.0.1:$port/"
$layout = "http://127.0.0.1:$port/_dash-layout"
$deps = "http://127.0.0.1:$port/_dash-dependencies"
$css = "http://127.0.0.1:$port/assets/custom.css"
$trends = "http://127.0.0.1:$port/"

function SafeInvoke {
    param(
        [string]$uri,
        [string]$outfile
    )
    try {
        $r = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 5
        if ($outfile -and $null -ne $r.Content) { $r.Content | Out-File -FilePath $outfile -Encoding utf8 }
        return @{ok=$true; status=$r.StatusCode; len=($r.Content.Length)}
    } catch {
        return @{ok=$false; error=$_.Exception.Message}
    }
}

$result = SafeInvoke $root
if ($result.ok) { Write-Output ("ROOT: " + $result.status) } else { Write-Output ("ROOT ERR: " + $result.error) }

$result = SafeInvoke $layout ('c:/Aarav/fin_env/Dash/_dash_layout_latest.json')
if ($result.ok) { Write-Output ("LAYOUT: " + $result.len) } else { Write-Output ("LAYOUT ERR: " + $result.error) }

$result = SafeInvoke $deps
if ($result.ok) { Write-Output ("DEPS: " + $result.status) } else { Write-Output ("DEPS ERR: " + $result.error) }

$result = SafeInvoke $css ('c:/Aarav/fin_env/Dash/_assets_custom.css')
if ($result.ok) { Write-Output ("CSS: " + $result.len) } else { Write-Output ("CSS ERR: " + $result.error) }

$result = SafeInvoke $trends
if ($result.ok) { Write-Output ("TRENDS ROOT: " + $result.status) } else { Write-Output ("TRENDS_ROOT ERR: " + $result.error) }

Write-Output "Smoke tests complete. Saved files (if any): _dash_layout_latest.json, _assets_custom.css"
