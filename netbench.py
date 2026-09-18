#!/usr/bin/env python3
"""
CrossBorder NetBench - All-in-One Network Benchmark Suite
Supports Windows, macOS, Linux, and Android.
Can run in HOST mode (receiver) or CLIENT mode (sender).
Zero external python dependencies required (pure standard library).
"""

import argparse
import http.server
import json
import os
import platform
import socket
import socketserver
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

# Prevent Windows console charmap UnicodeEncodeErrors
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

DEFAULT_HTTP_PORT = 9000
DEFAULT_IPERF_PORT = 5201

# =====================================================================
# HOST / SERVER IMPLEMENTATION
# =====================================================================

class UploadSinkHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        data = json.dumps({
            "status": "ready",
            "service": "CrossBorder-NetBench",
            "system": platform.platform(),
            "time": datetime.now().isoformat()
        }).encode('utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self):
        self._handle_upload()

    def do_POST(self):
        self._handle_upload()

    def _handle_upload(self):
        client_ip = self.client_address[0]
        timestamp = datetime.now().strftime('%H:%M:%S')
        content_length = self.headers.get('Content-Length')
        transfer_encoding = self.headers.get('Transfer-Encoding', '').lower()

        is_chunked = 'chunked' in transfer_encoding
        total_expected = int(content_length) if content_length and content_length.isdigit() else 0

        print(f"\n[{timestamp}] [+] Incoming payload upload from {client_ip}")
        if is_chunked:
            print(f"[{timestamp}]     Transfer: Chunked Stream")
        elif total_expected > 0:
            print(f"[{timestamp}]     Expected size: {total_expected / (1024*1024):.2f} MB ({total_expected:,} bytes)")
        else:
            print(f"[{timestamp}]     Transfer: Streaming (unbounded)")

        start_time = time.time()
        last_interval_time = start_time
        last_interval_bytes = 0
        total_bytes = 0
        chunk_size = 128 * 1024  # 128 KB buffer

        try:
            if is_chunked:
                while True:
                    line = self.rfile.readline().strip()
                    if not line:
                        break
                    chunk_len = int(line.split(b';')[0], 16)
                    if chunk_len == 0:
                        self.rfile.readline()
                        break
                    bytes_left = chunk_len
                    while bytes_left > 0:
                        buf = self.rfile.read(min(chunk_size, bytes_left))
                        if not buf:
                            raise ConnectionResetError("Client closed socket prematurely")
                        total_bytes += len(buf)
                        bytes_left -= len(buf)
                    self.rfile.readline()
            else:
                while total_bytes < total_expected or total_expected == 0:
                    remaining = (total_expected - total_bytes) if total_expected > 0 else chunk_size
                    buf = self.rfile.read(min(chunk_size, remaining))
                    if not buf:
                        break
                    total_bytes += len(buf)

                    now = time.time()
                    interval = now - last_interval_time
                    if interval >= 2.0:
                        interval_mbps = ((total_bytes - last_interval_bytes) * 8) / (interval * 1_000_000)
                        overall_mbps = (total_bytes * 8) / ((now - start_time) * 1_000_000)
                        pct = f"({(total_bytes/total_expected)*100:5.1f}%)" if total_expected else ""
                        sys.stdout.write(
                            f"\r[{datetime.now().strftime('%H:%M:%S')}] {total_bytes / (1024*1024):7.1f} MB {pct} | "
                            f"Inst: {interval_mbps:6.2f} Mbps | Avg: {overall_mbps:6.2f} Mbps "
                        )
                        sys.stdout.flush()
                        last_interval_time = now
                        last_interval_bytes = total_bytes

            duration = max(time.time() - start_time, 0.001)
            mbps = (total_bytes * 8) / (duration * 1_000_000)
            mbytes = total_bytes / (1024 * 1024)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [OK] Transfer Finished Successfully!")
            print(f"[{datetime.now().strftime('%H:%M:%S')}]     Total: {mbytes:.2f} MB in {duration:.2f}s | Avg Throughput: {mbps:.2f} Mbps ({mbytes/duration:.2f} MB/s)")

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Connection', 'close')
            resp = f"OK {total_bytes} bytes received in {duration:.2f}s ({mbps:.2f} Mbps)\n".encode('utf-8')
            self.send_header('Content-Length', str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            elapsed = time.time() - start_time
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [!] CONNECTION COLLAPSED after {elapsed:.1f}s ({total_bytes / (1024*1024):.2f} MB read). Details: {e}")
        except Exception as e:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [!] Transfer exception: {e}")

    def log_message(self, format, *args):
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

def get_network_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ':' not in ip and not ip.startswith('127.'):
                if ip not in ips:
                    ips.append(ip)
    except Exception:
        pass
    return ips

def get_public_ip():
    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "curl/7.88.1"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.read().decode('utf-8').strip()
    except Exception:
        return "Unknown/Offline"

def run_host_mode(args):
    print("=" * 70)
    print("  CrossBorder NetBench - HOST MODE (Destination Server)")
    print(f"  OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print("=" * 70)

    local_ips = get_network_ips()
    public_ip = get_public_ip()

    print("\n[Network Interfaces]")
    for ip in local_ips:
        print(f"  -> Local / VPN IP : {ip}")
    print(f"  -> Public IP      : {public_ip}")
    print(f"\nListening Ports:")
    print(f"  -> iPerf3 Server  : Port {args.iperf_port} (TCP/UDP)")
    print(f"  -> HTTP Sink      : Port {args.http_port} (TCP)")
    print("=" * 70)

    # Locate iPerf3 executable (checking PATH and WinGet default install location)
    import shutil
    import glob
    iperf_bin = shutil.which("iperf3")
    if not iperf_bin and platform.system() == "Windows":
        winget_pattern = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages", "*iperf*", "iperf3.exe")
        matches = glob.glob(winget_pattern)
        if matches:
            iperf_bin = matches[0]

    # Launch iPerf3 Server
    iperf_cmd = [iperf_bin or "iperf3", "-s", "-p", str(args.iperf_port), "-V"]
    iperf_proc = None
    try:
        iperf_proc = subprocess.Popen(iperf_cmd)
        print(f"[OK] iPerf3 server started (PID: {iperf_proc.pid})")
    except FileNotFoundError:
        print(f"[!] Warning: 'iperf3' executable was not found in PATH.")
        print(f"    Make sure iPerf3 is installed. (Windows: winget install ar51an.iPerf3 | Mac: brew install iperf3)")

    # Launch HTTP Sink
    try:
        http_server = ThreadedHTTPServer(('0.0.0.0', args.http_port), UploadSinkHandler)
        print(f"[OK] HTTP Upload Sink started on 0.0.0.0:{args.http_port}")
        print("\n[*] Host is ready and listening. Press Ctrl+C to terminate.\n")
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping host servers...")
    finally:
        if iperf_proc and iperf_proc.poll() is None:
            iperf_proc.terminate()
            iperf_proc.wait()
        print("[OK] All servers stopped.")

# =====================================================================
# CLIENT IMPLEMENTATION
# =====================================================================

class MemoryStreamReader:
    """Streams pseudo-random data directly from memory in chunks without creating disk files."""
    def __init__(self, total_bytes, chunk_size=128*1024):
        self.total_bytes = total_bytes
        self.bytes_sent = 0
        self.chunk_size = chunk_size
        self._pattern = os.urandom(chunk_size)

    def read(self, size=-1):
        if self.bytes_sent >= self.total_bytes:
            return b""
        remaining = self.total_bytes - self.bytes_sent
        to_read = min(self.chunk_size, remaining) if size < 0 else min(size, remaining)
        self.bytes_sent += to_read
        return self._pattern[:to_read]

def run_client_mode(args):
    target = args.target
    if not target:
        print("[!] Error: You must specify --target <HOST_IP_OR_DOMAIN>")
        sys.exit(1)

    payload_bytes = int(args.payload_gb * 1024 * 1024 * 1024)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = f"benchmark_report_{timestamp}"
    os.makedirs(report_dir, exist_ok=True)

    print("=" * 70)
    print("  CrossBorder NetBench - CLIENT BENCHMARK")
    print(f"  Target Host: {target}")
    print(f"  Payload Size: {args.payload_gb} GB ({payload_bytes:,} bytes)")
    print(f"  Report Dir:  {report_dir}")
    print("=" * 70)

    # 1. Health check
    print("\n[Step 1/4] Checking connectivity to Host HTTP Sink...")
    sink_url = f"http://{target}:{args.http_port}/"
    try:
        req = urllib.request.Request(sink_url, headers={"User-Agent": "NetBench-Client"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode('utf-8')
            print(f"  [OK] Host responded: {data.strip()}")
    except Exception as e:
        print(f"  [!] Warning: Could not connect to {sink_url}: {e}")
        print("      Make sure host servers are running and firewall allows port 9000.")
        cont = input("      Continue test anyway? (y/N): ").strip().lower()
        if cont != 'y':
            sys.exit(1)

    # 2. MTR / Traceroute
    print(f"\n[Step 2/4] Network Hop & Loss Analysis...")
    mtr_file = os.path.join(report_dir, "01_routing.txt")
    has_mtr = False
    try:
        subprocess.run(["mtr", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        has_mtr = True
    except FileNotFoundError:
        pass

    if has_mtr:
        print("  Running MTR (300 cycles / ~5 minutes)...")
        mtr_cmd = ["sudo", "mtr", "--report", "--report-cycles", "300", "--no-dns", target] if platform.system() != "Windows" else ["mtr", "-r", "-c", "300", target]
        try:
            with open(mtr_file, "w") as f:
                subprocess.run(mtr_cmd, stdout=f, check=True)
            print(f"  [OK] MTR report saved to {mtr_file}")
        except Exception as e:
            print(f"  [!] MTR execution notice: {e}")
    else:
        trace_cmd = ["tracert", "-d", target] if platform.system() == "Windows" else ["traceroute", "-n", target]
        print(f"  MTR not found; running standard traceroute...")
        try:
            with open(mtr_file, "w") as f:
                subprocess.run(trace_cmd, stdout=f)
            print(f"  [OK] Traceroute saved to {mtr_file}")
        except Exception as e:
            print(f"  [!] Traceroute failed: {e}")

    # 3. iPerf3 Sustained Throughput
    print(f"\n[Step 3/4] iPerf3 Sustained Bandwidth Benchmark ({args.duration}s)...")
    
    # 3A: Single Stream
    print(f"  - Test 3A: Single TCP stream (tests GFW queue drops and ISP rate limiting)...")
    iperf_single_file = os.path.join(report_dir, "02_iperf_single.txt")
    iperf_single_cmd = ["iperf3", "-c", target, "-p", str(args.iperf_port), "-t", str(args.duration), "-i", "5"]
    try:
        with open(iperf_single_file, "w") as f:
            proc = subprocess.Popen(iperf_single_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in proc.stdout:
                sys.stdout.write(line)
                f.write(line)
            proc.wait()
    except FileNotFoundError:
        print("  [!] iPerf3 client executable not found. Please install iperf3.")

    # 3B: Multi Stream
    print(f"\n  - Test 3B: 4 Parallel Streams (evaluates multi-part upload aggregation)...")
    iperf_multi_file = os.path.join(report_dir, "03_iperf_multi.txt")
    iperf_multi_cmd = ["iperf3", "-c", target, "-p", str(args.iperf_port), "-P", "4", "-t", str(min(args.duration, 180)), "-i", "5"]
    try:
        with open(iperf_multi_file, "w") as f:
            proc = subprocess.Popen(iperf_multi_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in proc.stdout:
                sys.stdout.write(line)
                f.write(line)
            proc.wait()
    except FileNotFoundError:
        pass

    # 4. Real-world in-memory HTTP stream upload
    print(f"\n[Step 4/4] Real-World Payload Upload ({args.payload_gb} GB via HTTP Stream)...")
    print(f"  (Streaming directly from RAM - 0 SSD write cycles)")
    upload_url = f"http://{target}:{args.http_port}/upload"
    streamer = MemoryStreamReader(payload_bytes)
    
    start_t = time.time()
    last_log_t = start_t
    last_log_bytes = 0

    try:
        req = urllib.request.Request(upload_url, data=streamer, method="POST", headers={
            "Content-Length": str(payload_bytes),
            "Content-Type": "application/octet-stream",
            "User-Agent": "NetBench-Client"
        })
        with urllib.request.urlopen(req, timeout=1200) as resp:
            resp_body = resp.read().decode('utf-8')
            total_time = max(time.time() - start_t, 0.001)
            mbps = (payload_bytes * 8) / (total_time * 1_000_000)
            mbytes = payload_bytes / (1024 * 1024)
            print(f"\n  [OK] Upload Completed: {mbytes:.2f} MB in {total_time:.2f}s (Avg: {mbps:.2f} Mbps / {mbytes/total_time:.2f} MB/s)")
            print(f"      Host Response: {resp_body.strip()}")
            
            with open(os.path.join(report_dir, "04_payload_result.txt"), "w") as f:
                f.write(f"Bytes: {payload_bytes}\nTime: {total_time}\nMbps: {mbps}\nHostResp: {resp_body}\n")
    except Exception as e:
        print(f"\n  [!] Upload failed or interrupted: {e}")

    print("\n" + "=" * 70)
    print(f" Benchmark Complete! Reports saved in: {report_dir}")
    print("=" * 70)

# =====================================================================
# MAIN ENTRYPOINT
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="CrossBorder NetBench - Unified Network Benchmark Suite")
    subparsers = parser.add_subparsers(dest="mode", help="Execution mode: 'host' or 'client'")

    # Host subparser
    host_parser = subparsers.add_parser("host", help="Run as Benchmark Host (Receiver)")
    host_parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT, help="Port for HTTP upload sink (default: 9000)")
    host_parser.add_argument("--iperf-port", type=int, default=DEFAULT_IPERF_PORT, help="Port for iPerf3 server (default: 5201)")

    # Client subparser
    client_parser = subparsers.add_parser("client", help="Run as Benchmark Client (Sender)")
    client_parser.add_argument("target_pos", nargs="?", default=None, help="Target host IP or domain (positional)")
    client_parser.add_argument("--target", "-t", type=str, default=None, help="Target host IP or domain")
    client_parser.add_argument("--payload-gb", "-g", type=float, default=2.0, help="Payload size in GB for real upload test (default: 2.0)")
    client_parser.add_argument("--duration", "-d", type=int, default=300, help="Duration in seconds for sustained iPerf3 test (default: 300)")
    client_parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT, help="Host HTTP port (default: 9000)")
    client_parser.add_argument("--iperf-port", type=int, default=DEFAULT_IPERF_PORT, help="Host iPerf3 port (default: 5201)")

    if len(sys.argv) == 1:
        # Interactive prompt if no arguments passed
        print("=" * 60)
        print(" CrossBorder NetBench - Interactive Launcher")
        print("=" * 60)
        print(" 1) Run as HOST (Receiver endpoint)")
        print(" 2) Run as CLIENT (Sender / Benchmark runner)")
        choice = input("\nSelect mode [1/2]: ").strip()
        if choice == '1':
            class Args:
                http_port = DEFAULT_HTTP_PORT
                iperf_port = DEFAULT_IPERF_PORT
            run_host_mode(Args())
            return
        elif choice == '2':
            target = input("Enter target host IP or domain: ").strip()
            class Args:
                target_ip = target
                http_port = DEFAULT_HTTP_PORT
                iperf_port = DEFAULT_IPERF_PORT
                payload_gb = 2.0
                duration = 300
            args = Args()
            args.target = target
            run_client_mode(args)
            return
        else:
            print("Invalid selection.")
            sys.exit(1)

    # Pre-process arguments to normalize `--client` -> `client`, `--host` -> `host`
    raw_args = sys.argv[1:]
    normalized_args = []
    mode_detected = None

    for a in raw_args:
        if a in ("--client", "-client", "client"):
            if not mode_detected:
                normalized_args.append("client")
                mode_detected = "client"
        elif a in ("--host", "-host", "host"):
            if not mode_detected:
                normalized_args.append("host")
                mode_detected = "host"
        else:
            normalized_args.append(a)

    # If user just ran `netbench 100.88.166.97`, default to client mode
    if not mode_detected and normalized_args:
        first = normalized_args[0]
        if not first.startswith("-"):
            normalized_args.insert(0, "client")

    args = parser.parse_args(normalized_args)
    if args.mode == "host":
        run_host_mode(args)
    elif args.mode == "client":
        # Resolve target from either positional or --target
        target = getattr(args, "target", None) or getattr(args, "target_pos", None)
        if not target:
            print("[!] Error: Target IP or domain required. Example: netbench client 100.88.166.97")
            sys.exit(1)
        args.target = target
        run_client_mode(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
