#!/usr/bin/env python3
"""Helper CLI to update, verify and run the app locally."""
import argparse
import os
import subprocess
import sys


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd)


def cmd_update(args):
    # Git pull rebase with stash
    run(["git", "fetch", "--all"])
    run(["git", "stash", "--include-untracked"])  # ignore error if nothing to stash
    run(["git", "pull", "--rebase", "origin", "main"])  # update
    run(["git", "stash", "pop"])  # may fail if nothing to pop


def cmd_doctor(args):
    from src.diagnostics import doctor
    import json
    print(json.dumps(doctor(), indent=2, ensure_ascii=False))


def cmd_test(args):
    sys.exit(run([sys.executable, "test_installation.py"]))


def cmd_docker_up(args):
    run(["docker", "compose", "up", "-d", "--build"])  # local compose


def cmd_restart_worker(args):
    run(["docker", "compose", "restart", "worker"])


def cmd_set_dry_run(args):
    path = ".env"
    if not os.path.exists(path):
        print(".env not found; create it from .env.example")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = []
    found = False
    for line in lines:
        if line.startswith("DRY_RUN="):
            out.append(f"DRY_RUN={'true' if args.value else 'false'}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"DRY_RUN={'true' if args.value else 'false'}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("Updated DRY_RUN in .env ->", args.value)


def cmd_run_daily(args):
    from src.scheduler import run_daily_post
    run_daily_post()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("update").set_defaults(func=cmd_update)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("test").set_defaults(func=cmd_test)
    sub.add_parser("docker-up").set_defaults(func=cmd_docker_up)
    sub.add_parser("restart-worker").set_defaults(func=cmd_restart_worker)
    p = sub.add_parser("set-dry-run")
    p.add_argument("value", type=lambda s: s.lower() in ("1","true","yes","on"))
    p.set_defaults(func=cmd_set_dry_run)
    sub.add_parser("run-daily").set_defaults(func=cmd_run_daily)

    args = ap.parse_args()
    if not hasattr(args, "func"):
        ap.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
