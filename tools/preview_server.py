#!/usr/bin/env python3
"""Local preview server with caching disabled for reliable Arena refreshes."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma','no-cache')
        self.send_header('Expires','0')
        super().end_headers()

ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()
