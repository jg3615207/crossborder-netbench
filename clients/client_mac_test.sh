#!/usr/bin/env bash
# ==============================================================================
# Cross-Border Sustained Throughput & Stability Benchmark (macOS Client)
# Designed for testing media upload performance, GFW throttling, and packet loss
# ==============================================================================

set -uo pipefail

if [ $# -lt 1 ]; then
    echo "======================================================================"
    echo " Usage:   $0 <HOST_IP_OR_DOMAIN> [PAYLOAD_SIZE_GB]"
    echo " Example: $0 203.0.113.42 2"
    echo " (Default payload size is 2GB if omitted)"
    echo "======================================================================"
    exit 1
fi

HOST="$1"
PAYLOAD_GB="${2:-2}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="./benchmark_report_${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

echo "======================================================================"
echo " Starting Network Benchmark: macOS Client -> $HOST"
echo " Report Folder: $OUTPUT_DIR"
echo " Timestamp:     $(date)"
echo "======================================================================"

# 1. Dependency Checks
for cmd in curl iperf3; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "[!] Error: '$cmd' is not installed. Run 'brew install $cmd' first."
        exit 1
    fi
done

HAS_MTR=true
if ! command -v mtr &> /dev/null; then
    echo "[!] Warning: 'mtr' is not installed. (Install via 'brew install mtr')"
    echo "    Skipping MTR routing test; falling back to traceroute/ping."
    HAS_MTR=false
fi

# 2. Pre-flight Connectivity & Health Check
echo -e "\n[Step 1/5] Checking basic connectivity to $HOST..."
if ! curl -s --connect-timeout 5 "http://$HOST:9000/" | grep -q "OK"; then
    echo "[!] Warning: Could not reach HTTP Upload Sink at http://$HOST:9000/"
    echo "    Make sure 'start_servers.bat' is running on the Windows host and port 9000 is open."
    read -p "    Continue anyway? (y/N) " confirm
    if [[ "$confirm" != [yY]* ]]; then
        exit 1
    fi
else
    echo "  [✓] HTTP Sink reachable on port 9000."
fi

# 3. Routing and Packet Loss (MTR / Traceroute)
echo -e "\n[Step 2/5] Running Packet Loss & Routing Analysis..."
if [ "$HAS_MTR" = true ]; then
    echo "  Running 5-minute (300 cycles) MTR analysis (requires sudo for raw ICMP)..."
    sudo mtr --report --report-cycles 300 --no-dns "$HOST" | tee "$OUTPUT_DIR/01_mtr_routing.txt"
else
    echo "  Running traceroute..."
    traceroute -w 2 -q 3 "$HOST" | tee "$OUTPUT_DIR/01_traceroute.txt"
    echo "  Running 100-ping packet loss test..."
    ping -c 100 -i 0.2 "$HOST" | tee "$OUTPUT_DIR/01_ping_loss.txt"
fi

# 4. iPerf3 Sustained Single Stream (5 Minutes)
echo -e "\n[Step 3/5] Running Sustained Single-Stream Upload Test (300s)..."
echo "  Note: This tests if ISP QoS throttles your TCP session after 30-60 seconds."
iperf3 -c "$HOST" -p 5201 -t 300 -i 5 \
       --logfile "$OUTPUT_DIR/02_iperf_single_stream.txt"
cat "$OUTPUT_DIR/02_iperf_single_stream.txt" | tail -n 12

# 5. iPerf3 Multi-Stream (4 Parallel Streams, 300s)
echo -e "\n[Step 4/5] Running Multi-Stream Upload Test (4 Parallel Streams, 300s)..."
echo "  Note: Tests whether multi-part uploads overcome single-stream packet loss limits."
iperf3 -c "$HOST" -p 5201 -P 4 -t 300 -i 5 \
       --logfile "$OUTPUT_DIR/03_iperf_multi_stream.txt"
cat "$OUTPUT_DIR/03_iperf_multi_stream.txt" | tail -n 15

# 6. Real-World HTTP Large Payload Upload
echo -e "\n[Step 5/5] Real-World Payload Upload (${PAYLOAD_GB}GB via HTTP)..."
PAYLOAD_FILE="/tmp/netbench_dummy_${PAYLOAD_GB}G.bin"
echo "  Generating ${PAYLOAD_GB}GB dummy payload..."
dd if=/dev/urandom of="$PAYLOAD_FILE" bs=1048576 count=$((PAYLOAD_GB * 1024)) status=progress

echo "  Uploading ${PAYLOAD_GB}GB payload to http://$HOST:9000/upload..."
curl -v -T "$PAYLOAD_FILE" \
     --speed-time 30 --speed-limit 1000 \
     -w "\n========================\nUpload Summary:\nHTTP Response: %{http_code}\nTime Taken:    %{time_total}s\nAverage Speed: %{speed_upload} B/s\n========================\n" \
     "http://$HOST:9000/upload" 2>&1 | tee "$OUTPUT_DIR/04_http_upload.log"

rm -f "$PAYLOAD_FILE"

# 7. Summary Report
echo -e "\n======================================================================"
echo " Benchmark Complete! Results saved in: $OUTPUT_DIR"
echo "======================================================================"
ls -lh "$OUTPUT_DIR"
