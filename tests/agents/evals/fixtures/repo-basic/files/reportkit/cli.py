"""Command line: report, serve and greet."""

import argparse

from . import __version__, greeting, report, server, storage


def main(argv=None):
    parser = argparse.ArgumentParser(prog="reportkit")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    report_command = commands.add_parser("report", help="print the report for a CSV file")
    report_command.add_argument("file")
    serve_command = commands.add_parser("serve", help="serve the reports page")
    serve_command.add_argument("--port", type=int, default=8000)
    greet_command = commands.add_parser("greet", help="print a greeting")
    greet_command.add_argument("name")
    args = parser.parse_args(argv)

    if args.command == "report":
        print(report.render_table(report.build_lines(storage.load_rows(args.file))))
    elif args.command == "serve":
        server.serve(args.port)
    elif args.command == "greet":
        print(greeting.greet(args.name))
    return 0
