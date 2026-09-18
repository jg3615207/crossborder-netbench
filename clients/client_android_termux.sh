#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Android Benchmark Script (Termux)
# ==============================================================================

set -uo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: bash $0 <HOST_IP>"
    exit 1
fi

HOST="$1"

echo "======================================================================"
echo " Android Sustained Network Benchmark -> $HOST"
echo "======================================================================"

# Acquire wakelock so screen timeout does not throttle radio
if command -v termux-wake-lock &> /dev/null; then
    echo "[*] Acquiring Termux wake lock (keeps CPU and network active)..."
    termux-wake-lock
fi

trap 'command -v termux-wake-unlock &> /dev/null && termux-wake-unlock' EXIT

# Check tools
for cmd in curl iperf3; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "[!] Installing $cmd via pkg..."
        pkg install -y "$cmd"
    fi
done

# Step 1: Health check
echo -e "\n[1/4] Checking HTTP Sink..."
curl -s --connect-timeout 5 "http://$HOST:9000/" || {
    echo "[!] Cannot reach host at http://$HOST:9000. Check IP and firewall."
    exit 1
}

# Step 2: Single-stream sustained test (300s)
echo -e "\n[2/4] Running 5-Minute Single-Stream Sustained Upload (iPerf3)..."
iperf3 -c "$HOST" -p 5201 -t 300 -i 5

# Step 3: Multi-stream test (4 streams, 120s)
echo -e "\n[3/4] Running Multi-Stream Upload (4 Streams, 120s)..."
iperf3 -c "$HOST" -p 5201 -P 4 -t 120 -i 5

# Step 4: Real-world upload payload (500MB on mobile storage)
echo -e "\n[4/4] Running 500MB Real-world HTTP Upload..."
TEST_FILE="./dummy_500m.bin"
dd if=/dev/urandom of="$TEST_FILE" bs=1M count=500
curl -T "$TEST_FILE" "http://$HOST:9000/upload" -w "\nResult: %{http_code} | Speed: %{speed_upload} B/s | Time: %{time_total}s\n"
rm -f "$TEST_FILE"

echo -e "\n[✓] Android benchmark completed!"
