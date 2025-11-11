#!/usr/bin/env python3
"""
Simple HTTP server to serve the landing page.
Use this while the full application dependencies are installing.
"""
import http.server
import socketserver
import os

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/static/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

os.chdir('/home/user/networking-ai')

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    🤖 AI Talent-Hiring Platform - Landing Page Ready!       ║
║                                                              ║
║    🌐 Open in your browser: http://localhost:{PORT}        ║
║                                                              ║
║    📱 On Mac, you can also use:                             ║
║       • curl http://localhost:{PORT}/api/health             ║
║       • Open http://localhost:{PORT} in Safari/Chrome       ║
║                                                              ║
║    Press Ctrl+C to stop the server                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    httpd.serve_forever()
