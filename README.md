# CrossBorder NetBench 🚀

A comprehensive, cross-platform network benchmark suite specifically engineered to test **cross-border internet speed, sustained stability, ISP rate-limiting, and GFW packet loss** for large media uploads (e.g. from China to overseas destinations).

---

## Key Features

1. **Host & Client in One Tool**: Any machine (Windows, macOS, Linux, Android) can act as the overseas receiver (`host`) or the benchmark runner (`client`).
2. **Sustained Throughput Benchmark**: Uses `iPerf3` for sustained 5–10 minute tests (single TCP stream vs. 4 parallel streams) to detect ISP rate-limiting thresholds and TCP congestion collapse.
3. **Hop-by-Hop Loss Diagnostics**: Automated MTR / traceroute discovering where latency spikes and packet loss occur (typically at international border gateways).
4. **Real-World In-Memory Streaming Uploads**: Uploads custom payloads (1GB–5GB) directly from memory over HTTP. Eliminates SSD write bottlenecks and tests the exact protocol characteristics of large media uploads.
5. **Zero Python Dependencies**: Works out-of-the-box using the Python 3 standard library.

---

## Quick Start Guide

### 1. Windows Setup

#### Automated Install
Right-click `install-win.ps1` -> **Run with PowerShell (as Administrator)**:
- Installs `iPerf3` via winget (if not already installed)
- Automatically adds Windows Firewall rules for Port `5201` (TCP/UDP), Port `9000` (TCP), and ICMP Echo (Ping/MTR)

#### Running on Windows:
```cmd
# Run as Destination Host (Receiver)
netbench.bat host

# Run as Benchmark Client (Sender)
netbench.bat client --target <HOST_IP> --payload-gb 2 --duration 300
```

---

### 2. macOS Setup

#### Automated Install
Open Terminal in the project directory and run:
```bash
chmod +x install-mac.sh
./install-mac.sh
```
- Installs `iperf3`, `mtr`, `curl`, and `python3` via Homebrew
- Configures raw socket privileges for MTR

#### Running on macOS:
```bash
# Run as Destination Host (Receiver)
./netbench.sh host

# Run as Benchmark Client (Sender)
./netbench.sh client --target <HOST_IP> --payload-gb 2 --duration 300
```

---

### 3. Android (Termux) Setup

1. Install **Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/).
2. Run setup:
   ```bash
   bash install-android.sh
   ```
3. Run benchmark:
   ```bash
   python netbench.py client --target <HOST_IP> --payload-gb 0.5
   ```
   *(Termux automatically holds an Android wake-lock to prevent CPU sleep / radio power savings from throttling the test)*.

---

## Diagnostic Matrix

| Symptom / Pattern | Root Cause | Solution |
| :--- | :--- | :--- |
| **Initial 30s high speed, then drops to 2–5 Mbps** | Chinese ISP QoS rate-limiting sustained single TCP connections. | Use parallel multi-part chunked uploads or an enterprise IPLC/IEPL line. |
| **MTR packet loss spikes at border hops** | International border gateway saturation & active queue drops. | Switch host TCP congestion control algorithm to **BBR** instead of CUBIC. |
| **"Sawtooth" upload speed pattern** | High packet drop rate causes TCP window collapse and RTO timeouts. | Adopt **HTTP/3 (QUIC)** or concurrent multi-part S3 chunk uploads. |
| **Multi-stream is 10x faster than single-stream** | Latency × packet loss caps single TCP window bandwidth-delay product. | Enable parallel chunked uploading (4–8 streams). |

---

## File Structure

```
CrossBorder-NetBench/
├── netbench.py           # Universal host/client Python engine (Zero dependencies)
├── netbench.bat          # Windows launcher
├── netbench.sh           # macOS / Linux launcher
├── install-win.ps1       # 1-Click Windows installer & firewall configuration
├── install-mac.sh        # 1-Click macOS installer (Homebrew)
├── install-android.sh    # 1-Click Android Termux installer
├── setup_firewall.ps1    # Dedicated Windows firewall rule script
├── README.md             # Documentation
└── clients/              # Standalone shell scripts for clients
    ├── client_mac_test.sh
    └── client_android_termux.sh
```
