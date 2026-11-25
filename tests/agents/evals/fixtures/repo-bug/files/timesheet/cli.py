"""Command line: weekly and serve."""

import argparse

from . import report, server, storage


def main(argv=None):
    parser = argparse.ArgumentParser(prog="timesheet")
    commands = parser.add_subparsers(dest="command", required=True)
    weekly = commands.add_parser("weekly", help="print the minutes per project for each week")
    weekly.add_argument("file")
    serve = commands.add_parser("serve", help="serve the JSON API")
    serve.add_argument("--port", type=int, default=8100)
    args = parser.parse_args(argv)

    if args.command == "weekly":
        print(report.render(report.weekly_totals(storage.load_entries(args.file))))
    elif args.command == "serve":
        server.serve(args.port)
    return 0
