# Self-elevate to Administrator if not already elevated
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[*] Requesting Administrator privileges to configure Windows Firewall..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CrossBorder NetBench - Windows All-in-One Installer           " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Install / Verify iPerf3
Write-Host "`n[1/3] Checking iPerf3..." -ForegroundColor Yellow
$iperf = Get-Command iperf3 -ErrorAction SilentlyContinue
if (-not $iperf) {
    Write-Host "Installing iPerf3 via winget..." -ForegroundColor Cyan
    winget install --id ar51an.iPerf3 --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "[✓] iPerf3 is already installed: $($iperf.Source)" -ForegroundColor Green
}

# 2. Configure Windows Firewall
Write-Host "`n[2/3] Configuring Windows Firewall Rules..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "NetBench-iPerf3-TCP" -Direction Inbound -Protocol TCP -LocalPort 5201 -Action Allow -Profile Any -ErrorAction SilentlyContinue | Out-Null
New-NetFirewallRule -DisplayName "NetBench-iPerf3-UDP" -Direction Inbound -Protocol UDP -LocalPort 5201 -Action Allow -Profile Any -ErrorAction SilentlyContinue | Out-Null
New-NetFirewallRule -DisplayName "NetBench-HTTP-Sink" -Direction Inbound -Protocol TCP -LocalPort 9000 -Action Allow -Profile Any -ErrorAction SilentlyContinue | Out-Null
netsh advfirewall firewall add rule name="ICMP Allow incoming V4 echo request" protocol=icmpv4:8,any dir=in action=allow | Out-Null
Write-Host "[✓] Firewall rules configured (Port 5201, 9000, ICMP Echo allowed)." -ForegroundColor Green

# 3. Check Python
Write-Host "`n[3/3] Checking Python..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    Write-Host "[✓] Python is available: $($py.Source)" -ForegroundColor Green
} else {
    Write-Host "[!] Python is not in PATH. Please install Python from https://python.org or winget install Python.Python.3.11" -ForegroundColor Red
}

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " [✓] Installation complete! You can now run:" -ForegroundColor Green
Write-Host "     .\netbench.bat --host               (to run as server)" -ForegroundColor White
Write-Host "     .\netbench.bat --client <TARGET_IP> (to run benchmark)" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Press any key to close..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
