"""Tiny static file server for local preview. Reads the port from the PORT
environment variable (falling back to 8420) so multiple preview sessions
can each get their own port instead of clashing on a hardcoded one."""

import http.server
import os
import socketserver

port = int(os.environ.get("PORT", 8420))
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", port), Handler) as httpd:
    httpd.serve_forever()
