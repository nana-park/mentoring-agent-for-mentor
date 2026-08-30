"""Command-line entry point. Parsing --help does not connect to external services."""
import argparse
import asyncio


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mentoring CRM Pipeline")
    parser.add_argument("--mode", choices=["auto", "batch", "direct"], default="auto")
    parser.add_argument("--payload", help="JSON payload file for direct mode")
    args = parser.parse_args(argv)
    if args.mode == "direct" and not args.payload:
        parser.error("--payload is required for direct mode")
    from mentoring.pipeline import run_pipeline
    asyncio.run(run_pipeline(args.mode, payload=args.payload))


if __name__ == "__main__":
    main()
