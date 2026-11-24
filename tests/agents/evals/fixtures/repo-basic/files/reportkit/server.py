"""The reports page (/reports) and its JSON form (/api/reports)."""

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import report, storage

DATA_FILE = "data/sample.csv"


def page(lines):
    head = "".join(f"<th>{html.escape(name)}</th>" for name in report.COLUMNS)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in report.as_cells(line)) + "</tr>"
        for line in lines
    )
    return f"<!doctype html><title>Reports</title><h1>Reports</h1><table><tr>{head}</tr>{body}</table>"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        lines = report.build_lines(storage.load_rows(DATA_FILE))
        if self.path == "/reports":
            self.reply(200, "text/html; charset=utf-8", page(lines))
        elif self.path == "/api/reports":
            data = [dict(zip(report.COLUMNS, report.as_cells(line))) for line in lines]
            self.reply(200, "application/json", json.dumps(data))
        else:
            self.reply(404, "text/plain", "not found")

    def reply(self, status, kind, text):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(port):
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
