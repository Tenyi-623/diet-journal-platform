"""Start/stop this project's LAN Web API and durable worker independently of a terminal."""

import argparse, os, signal, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data/runtime"
PY = ROOT / "backend/.venv/bin/python"
COMMANDS = {
    "api": [
        str(PY),
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--limit-concurrency",
        "40",
    ],
    "worker": [str(PY), "-m", "backend.app.worker"],
}


def alive(name):
    file = RUN / f"{name}.pid"
    if not file.exists():
        return None
    pid = int(file.read_text())
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
        if ("backend.main:app" if name == "api" else "backend.app.worker") not in cmd:
            return None
        if Path(f"/proc/{pid}/cwd").resolve() != ROOT:
            return None
        return pid
    except FileNotFoundError:
        return None


def main():
    action = argparse.ArgumentParser()
    action.add_argument("command", choices=["start", "stop", "restart", "status"])
    args = action.parse_args()
    RUN.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.command in ["stop", "restart"]:
        for name in COMMANDS:
            pid = alive(name)
            if pid:
                os.kill(pid, signal.SIGTERM)
                for _ in range(50):
                    if not alive(name):
                        break
                    time.sleep(0.1)
                if alive(name):
                    raise SystemExit(f"{name} did not stop; inspect before retrying")
            (RUN / f"{name}.pid").unlink(missing_ok=True)
    if args.command in ["start", "restart"]:
        if not (ROOT / "frontend/dist/index.html").exists():
            raise SystemExit("Build frontend first: bash scripts/build_frontend.sh")
        for name, command in COMMANDS.items():
            if alive(name):
                continue
            with (RUN / f"{name}.log").open("ab") as out:
                p = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=out,
                    stderr=out,
                    start_new_session=True,
                )
            (RUN / f"{name}.pid").write_text(str(p.pid))
            time.sleep(0.6)
            if p.poll() is not None:
                raise SystemExit(f"{name} failed; inspect data/runtime/{name}.log")
    for name in COMMANDS:
        print(f"{name}: " + ("running" if alive(name) else "stopped"))
    if args.command in ["start", "restart", "status"]:
        from scripts.lan import show_addresses
        show_addresses()


if __name__ == "__main__":
    main()
