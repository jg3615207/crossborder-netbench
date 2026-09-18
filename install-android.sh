#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# CrossBorder NetBench - Android Setup (Termux)
# ==============================================================================

set -eo pipefail

echo "================================================================"
echo "  CrossBorder NetBench - Android Termux Setup"
echo "================================================================"

pkg update -y
pkg install -y python iperf3 curl tracepath termux-tools

chmod +x ./netbench.sh ./netbench.py 2>/dev/null || true

echo -e "\n================================================================"
echo " [✓] Termux dependencies installed!"
echo "     Run: python netbench.py client --target <HOST_IP>"
echo "================================================================"
