"""A small JSON server over the routes. The X-User header names the caller."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from . import handlers, routes, storage


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def dispatch(self):
            handler, params = routes.resolve(self.command, self.path)
            if handler is None:
                return self.reply(404, {"error": "no route"})
            query = {key: values[0] for key, values in parse_qs(urlsplit(self.path).query).items()}
            request = handlers.Request(user=self.headers.get("X-User", ""), params=params, query=query)
            status, body = handler(store, request)
            self.reply(status, body)

        do_GET = do_POST = do_DELETE = dispatch

        def reply(self, status, body):
            data = b"" if body is None else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def serve(port, data_file="data/entries.csv"):
    store = handlers.Store(storage.load_entries(data_file))
    HTTPServer(("127.0.0.1", port), make_handler(store)).serve_forever()
