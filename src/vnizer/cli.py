import argparse


def main():
    parser = argparse.ArgumentParser(description="Run VNizer.")
    parser.add_argument("command", choices=["serve", "worker", "backup", "restore"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--destination")
    parser.add_argument("--source")
    args = parser.parse_args()
    if args.command in ("backup", "restore"):
        from .backup import backup, restore
        from .config import Config
        if not args.destination or (args.command == "restore" and not args.source):
            parser.error("Use --destination, and use --source for restore.")
        if args.command == "backup":
            print(backup(Config.from_env().data_root, args.destination))
        else:
            print(restore(args.source, args.destination))
        return
    if args.command == "serve":
        import uvicorn

        from .app import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port)
    else:
        from .worker import main as worker_main
        worker_main()
