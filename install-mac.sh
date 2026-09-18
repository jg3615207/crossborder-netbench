#!/usr/bin/env bash
# ==============================================================================
# CrossBorder NetBench - macOS All-in-One Installer
# ==============================================================================

set -eo pipefail

echo "================================================================"
echo "  CrossBorder NetBench - macOS Setup"
echo "================================================================"

# 1. Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "[!] Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "[✓] Homebrew is installed."
fi

# 2. Install dependencies
echo -e "\n[*] Installing required network tools (iperf3, mtr, curl, python3)..."
brew install iperf3 mtr curl python3

# 3. Permissions for MTR
echo -e "\n[*] MTR requires raw socket privileges to trace routes without sudo prompts:"
MTR_BIN=$(brew --prefix)/sbin/mtr
if [ -f "$MTR_BIN" ]; then
    sudo chown root:wheel "$MTR_BIN" || true
    sudo chmod u+s "$MTR_BIN" || true
fi

# 4. Make scripts executable
chmod +x ./netbench.sh ./netbench.py 2>/dev/null || true

echo -e "\n================================================================"
echo " [✓] Installation complete! You can run:"
echo "     ./netbench.sh --host               (to run as destination server)"
echo "     ./netbench.sh --client <TARGET_IP> (to run benchmark)"
echo "================================================================"
