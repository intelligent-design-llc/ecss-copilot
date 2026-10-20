import os

import uvicorn


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"ECSS Copilot running on http://{host}:{port}  (advisory only - no ITAR/EAR-controlled data)")
    uvicorn.run("ecss_copilot.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
