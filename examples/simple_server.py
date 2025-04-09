#!/usr/bin/env python3

import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# Get port from environment variable or use default
PORT = int(os.environ.get('PORT', 8000))

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Send response
        content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Simple Test Server</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                h1 {{ color: #333; }}
                p {{ color: #666; }}
                .info {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Simple Test Server</h1>
                <p>This is a basic test server managed by Control Panel.</p>
                <div class="info">
                    <p><strong>Server Info:</strong></p>
                    <p>Running on port: {PORT}</p>
                    <p>Server time: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        self.wfile.write(content.encode())

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Starting test server on port {PORT}...")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")

if __name__ == '__main__':
    run_server()
