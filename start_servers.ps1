# Requires PowerShell 5.1 or Core
$Host.UI.RawUI.WindowTitle = "Network Benchmark Host - iPerf3 & Upload Sink"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   Starting Network Benchmark Host (Overseas Endpoint)         " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Detect IPs
Write-Host "`n[1] Detecting Network Interfaces..." -ForegroundColor Yellow
$LocalIPs = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.254\.' } | Select-Object -ExpandProperty IPAddress
Write-Host "    Local / LAN / VPN IPs:" -ForegroundColor Green
foreach ($ip in $LocalIPs) {
    Write-Host "      -> $ip" -ForegroundColor White
}

try {
    $PublicIP = (Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 3).Trim()
    Write-Host "    Public IP (if directly exposed): $PublicIP" -ForegroundColor Green
} catch {
    Write-Host "    Public IP: [Could not query or offline]" -ForegroundColor Gray
}

# 2. Check iPerf3
Write-Host "`n[2] Checking iPerf3..." -ForegroundColor Yellow
$iperfPath = (Get-Command iperf3 -ErrorAction SilentlyContinue).Source
if (-not $iperfPath) {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $iperfPath = (Get-Command iperf3 -ErrorAction SilentlyContinue).Source
}

if (-not $iperfPath) {
    Write-Host "    [!] iPerf3 not found in PATH! Attempting to locate winget install..." -ForegroundColor Red
} else {
    Write-Host "    [✓] Found iPerf3 at: $iperfPath" -ForegroundColor Green
}

# 3. Check Python
Write-Host "`n[3] Checking Python..." -ForegroundColor Yellow
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    Write-Host "    [!] Python not found in PATH!" -ForegroundColor Red
} else {
    Write-Host "    [✓] Found Python at: $pythonPath" -ForegroundColor Green
}

Write-Host "`n----------------------------------------------------------------"
Write-Host " Firewall note: Ensure inbound TCP 5201 (iPerf3), TCP 9000 (Sink)," -ForegroundColor Gray
Write-Host " and ICMP Echo (Ping) are allowed on your Windows / cloud firewall." -ForegroundColor Gray
Write-Host "----------------------------------------------------------------`n"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$SinkScript = Join-Path $ScriptDir "host_sink.py"

Write-Host "[*] Launching iPerf3 Server on port 5201..." -ForegroundColor Cyan
$iperfProcess = Start-Process -FilePath "iperf3.exe" -ArgumentList "-s", "-p", "5201", "-V" -PassThru -NoNewWindow

Write-Host "[*] Launching HTTP Upload Sink Server on port 9000..." -ForegroundColor Cyan
Write-Host "    Press Ctrl+C to terminate both servers at any time.`n" -ForegroundColor Yellow

try {
    & python "$SinkScript"
} finally {
    Write-Host "`n[*] Shutting down iPerf3..." -ForegroundColor DarkYellow
    if ($iperfProcess -and -not $iperfProcess.HasExited) {
        Stop-Process -Id $iperfProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[✓] Benchmark servers stopped." -ForegroundColor Green
}
