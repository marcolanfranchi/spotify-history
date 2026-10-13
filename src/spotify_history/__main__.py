"""Command-line entry point: python -m spotify_history <fetch|email|export|enrich|migrate>."""
import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(prog="spotify_history")
    parser.add_argument(
        "command",
        choices=["fetch", "email", "export", "enrich", "migrate"],
        help="fetch: pull recent plays; email: send the daily summary; "
             "export: write plays.csv (+ S3); enrich: fill in artist genres / album details "
             "from the API; migrate: create/upgrade the database",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="export only: also upload plays.csv to S3 (needs S3_BUCKET). "
             "Never uploads unless this flag is given.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="enrich only: maximum number of API calls this run (default 50)",
    )
    parser.add_argument(
        "--only", choices=["artists", "albums"],
        help="enrich only: restrict to one entity type",
    )
    args = parser.parse_args(argv)
    if args.upload and args.command != "export":
        parser.error("--upload only applies to the export command")
    if args.command != "enrich" and (args.only or args.limit is not None):
        parser.error("--limit and --only only apply to the enrich command")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    # imported lazily so e.g. `migrate` doesn't need Spotify credentials.
    # Only export and enrich report a meaningful exit code.
    if args.command == "fetch":
        from spotify_history.jobs.fetch import run as fetch_run

        fetch_run()
    elif args.command == "email":
        from spotify_history.jobs.daily_email import run as email_run

        email_run()
    elif args.command == "export":
        from spotify_history.jobs.export import run as export_run

        return export_run(upload=args.upload) or 0
    elif args.command == "enrich":
        from spotify_history.jobs.enrich import run as enrich_run

        return enrich_run(limit=args.limit or 50, only=args.only) or 0
    else:
        from spotify_history.db.migrate import migrate

        migrate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
