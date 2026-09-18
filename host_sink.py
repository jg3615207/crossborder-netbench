import http.server
import socketserver
import time
import sys
from datetime import datetime

PORT = 9000

class UploadSinkHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        msg = f"OK - Network Benchmark Upload Sink is Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n".encode('utf-8')
        self.send_header('Content-Length', str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

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

        print(f"\n[{timestamp}] [+] Incoming upload connection from {client_ip}")
        if is_chunked:
            print(f"[{timestamp}]     Mode: Chunked Transfer Encoding")
        elif total_expected > 0:
            print(f"[{timestamp}]     Expected size: {total_expected / (1024*1024):.2f} MB ({total_expected:,} bytes)")
        else:
            print(f"[{timestamp}]     Size: Stream (unspecified length)")

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
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [✓] Transfer Completed successfully!")
            print(f"[{datetime.now().strftime('%H:%M:%S')}]     Transferred: {mbytes:.2f} MB in {duration:.2f}s (Avg: {mbps:.2f} Mbps / {mbytes/duration:.2f} MB/s)")

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Connection', 'close')
            resp = f"OK {total_bytes} bytes received in {duration:.2f}s ({mbps:.2f} Mbps)\n".encode('utf-8')
            self.send_header('Content-Length', str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            elapsed = time.time() - start_time
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [!] CONNECTION COLLAPSED / DROPPED after {elapsed:.1f}s ({total_bytes / (1024*1024):.2f} MB read). Reason: {e}")
        except Exception as e:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [!] Error during transfer: {e}")

    def log_message(self, format, *args):
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

def main():
    print("=" * 65)
    print(" Network Benchmark HTTP Payload Sink Server")
    print(f" Listening on: 0.0.0.0:{PORT} (All network interfaces)")
    print(" Endpoints:")
    print(f"   - GET  http://<HOST_IP>:{PORT}/       -> Health check")
    print(f"   - POST http://<HOST_IP>:{PORT}/upload -> Real-world upload test")
    print(f"   - PUT  http://<HOST_IP>:{PORT}/upload -> Real-world upload test")
    print("=" * 65)
    
    server = ThreadedHTTPServer(('0.0.0.0', PORT), UploadSinkHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping Upload Sink Server.")
        server.shutdown()

if __name__ == "__main__":
    main()
