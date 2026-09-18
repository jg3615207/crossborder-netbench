# Run this script once in an Administrator PowerShell window to permit benchmark traffic
Write-Host "Configuring Windows Firewall for Network Benchmark..." -ForegroundColor Cyan

# 1. iPerf3 TCP & UDP
New-NetFirewallRule -DisplayName "NetworkBench-iPerf3-TCP" -Direction Inbound -Protocol TCP -LocalPort 5201 -Action Allow -Profile Any -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "NetworkBench-iPerf3-UDP" -Direction Inbound -Protocol UDP -LocalPort 5201 -Action Allow -Profile Any -ErrorAction SilentlyContinue

# 2. HTTP Upload Sink (Port 9000)
New-NetFirewallRule -DisplayName "NetworkBench-HTTP-Sink" -Direction Inbound -Protocol TCP -LocalPort 9000 -Action Allow -Profile Any -ErrorAction SilentlyContinue

# 3. ICMP Echo (Ping / MTR)
netsh advfirewall firewall add rule name="ICMP Allow incoming V4 echo request" protocol=icmpv4:8,any dir=in action=allow

Write-Host "[✓] Windows Firewall rules added successfully!" -ForegroundColor Green
Write-Host "    - TCP 5201 (iPerf3)"
Write-Host "    - UDP 5201 (iPerf3 UDP)"
Write-Host "    - TCP 9000 (HTTP Upload Sink)"
Write-Host "    - ICMP Echo (Ping / MTR)"
