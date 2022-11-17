import os
from wsgiref.simple_server import make_server

PORT = int(os.environ.get("PORT", "8080"))


def simple_app(environ, start_response):

    status = "200 OK"
    headers = [("Content-type", "text/plain; charset=utf-8")]

    start_response(status, headers)

    return [b"OK"]

with make_server("", PORT, simple_app) as httpd:
    print(f"Serving on port {PORT}...")
    httpd.serve_forever()
