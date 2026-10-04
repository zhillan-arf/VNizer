import argparse


def main():
    parser = argparse.ArgumentParser(description="Run VNizer.")
    parser.add_argument("command", choices=["serve", "worker"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        from .app import create_app
        uvicorn.run(create_app(), host=args.host, port=args.port)
    else:
        from .worker import main as worker_main
        worker_main()
