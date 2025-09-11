import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Change to frontend directory
frontend_dir = Path(__file__).parent / "frontend"
os.chdir(frontend_dir)

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

Handler = MyHTTPRequestHandler

print(f"🌐 Starting frontend server on http://localhost:{PORT}")
print(f"📁 Serving from: {frontend_dir}")
print(f"🔗 Backend API running on: http://localhost:8000")
print(f"📚 API Docs available at: http://localhost:8000/docs")
print("\n🚀 Opening browser...")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"✅ Frontend server started! Visit http://localhost:{PORT}")
    
    # Open browser automatically
    webbrowser.open(f'http://localhost:{PORT}')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
