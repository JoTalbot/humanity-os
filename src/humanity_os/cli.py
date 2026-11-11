"""Command-line entry point; intentionally loopback-only until authentication exists."""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="humanity-os")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("The 0.1 API has no authentication; only loopback binding is allowed.")
    import uvicorn
    uvicorn.run("humanity_os.app:app", host=args.host, port=args.port, reload=False)

if __name__ == "__main__":
    main()
