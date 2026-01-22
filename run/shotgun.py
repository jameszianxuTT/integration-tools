#!/usr/bin/env python3
"""
Uplift Shotgun Tool

Purpose:
    Trigger remote GitHub Actions in tt-xla and tt-forge-onnx using the HEAD SHA
    of a specified tt-mlir branch as mlir_override.

Usage:
    python run/shotgun.py <mlir-uplift-branch> [--tt-xla] [--tt-forge-onnx] [--dry-run]
    # or
    python run/shotgun.py --mlir-uplift-branch <branch> [--tt-xla] [--tt-forge-onnx] [--dry-run]

Behavior:
    - Clones or checks out tt-mlir via SSH, switches to the provided branch, resolves HEAD SHA.
    - If neither --tt-xla nor --tt-forge-onnx is specified, both are triggered (with a warning).
    - Always prints the constructed gh command; with --dry-run, commands are not executed.
    - After triggering, prints the URL of the most recent workflow run (best effort).

Workflows:
    - tt-xla: .github/workflows/manual-test.yml (test_suite=mlir-uplift-qualification.json)
    - tt-forge-onnx: .github/workflows/on-pr.yml

Requirements:
    - GitHub CLI (gh) installed and authenticated for the tenstorrent org.
    - SSH access to git@github.com:tenstorrent/tt-mlir.git
"""

import argparse
import os
import subprocess
import sys
# ANSI colors
COLOR = {
    "header": "\033[1;36m",   # bold cyan
    "cmd": "\033[2;37m",      # dim gray
    "url": "\033[1;33m",      # bold yellow
    "reset": "\033[0m",
}


REPO_SSH = {
    "tt-mlir": "git@github.com:tenstorrent/tt-mlir.git",
}

# GitHub repositories (owner/repo)
GH_REPOS = {
    "tt-xla": "tenstorrent/tt-xla",
    # tt-forge-fe renamed to tt-forge-onnx
    "tt-forge-onnx": "tenstorrent/tt-forge-onnx",
}


def run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def ensure_gh_cli() -> None:
    try:
        run(["gh", "--version"], check=True)
    except Exception:
        print("Error: GitHub CLI (gh) not found. Please install and authenticate 'gh'.", file=sys.stderr)
        sys.exit(1)


def clone_or_checkout_tt_mlir(branch: str) -> str:
    """
    Ensure tt-mlir exists locally and is on the requested branch. Returns absolute repo path.
    """
    repo_dir = os.path.abspath(os.path.join(os.getcwd(), "tt-mlir"))
    if not os.path.isdir(repo_dir):
        print(f"Cloning tt-mlir via SSH to {repo_dir}...")
        run(["git", "clone", REPO_SSH["tt-mlir"], repo_dir])

    # Fetch and checkout branch
    print(f"\n{COLOR['header']}==> Checking out tt-mlir branch '{branch}'...{COLOR['reset']}")
    try:
        run(["git", "fetch", "origin"], cwd=repo_dir)
        # Try checkout, create local tracking if needed
        rc = run(["git", "rev-parse", f"origin/{branch}"], cwd=repo_dir, check=False)
        if rc.returncode == 0:
            run(["git", "checkout", branch], cwd=repo_dir)
            run(["git", "reset", "--hard", f"origin/{branch}"], cwd=repo_dir)
        else:
            # fallback: try local branch
            run(["git", "checkout", branch], cwd=repo_dir)
            run(["git", "pull"], cwd=repo_dir)
    except subprocess.CalledProcessError as e:
        print(f"Failed to checkout branch '{branch}' in tt-mlir: {e.stderr}", file=sys.stderr)
        sys.exit(1)

    return repo_dir


def get_head_sha(repo_dir: str) -> str:
    res = run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
    sha = res.stdout.strip()
    if len(sha) != 40:
        print("Failed to determine HEAD SHA for tt-mlir", file=sys.stderr)
        sys.exit(1)
    return sha


def _format_cmd(cmd: list[str]) -> str:
    return " ".join(subprocess.list2cmdline([c]) for c in cmd)


def _print_run_url(repo: str, workflow: str) -> None:
    """Attempt to locate and print the latest run URL for a workflow in a repo."""
    try:
        # Use gh run list to fetch the latest runs for this workflow
        # gh run list -R <repo> --workflow <workflow> --limit 1 --json url -q '.[0].url'
        res = run([
            "gh", "run", "list",
            "-R", repo,
            "--workflow", workflow,
            "--limit", "1",
            "--json", "url",
        ], check=False)
        # Output is JSON like: [{"url":"https://..."}]
        import json
        data = json.loads(res.stdout or "[]")
        if isinstance(data, list) and data:
            url = data[0].get("url")
            if url:
                print(f"{COLOR['url']}Workflow run URL: {url}{COLOR['reset']}")
                return
    except Exception:
        pass
    print(f"{COLOR['url']}Workflow run URL: (unavailable){COLOR['reset']}")


def trigger_tt_xla(mlir_sha: str, dry_run: bool = False) -> None:
    """
    Trigger tt-xla manual-test.yml with test_suite mlir-uplift-qualification.json and mlir_override.
    """
    repo = GH_REPOS["tt-xla"]
    print(f"\n{COLOR['header']}==> Triggering tt-xla (manual-test.yml) with mlir_override={mlir_sha}...{COLOR['reset']}")
    # gh workflow run manual-test.yml -R tenstorrent/tt-xla -f test_suite=mlir-uplift-qualification.json -f mlir_override=<sha>
    cmd = [
        "gh", "workflow", "run", "manual-test.yml",
        "-R", repo,
        "-f", "test_suite=mlir-uplift-qualification.json",
        "-f", f"mlir_override={mlir_sha}"
    ]
    print(f"{COLOR['cmd']}   GH command: {_format_cmd(cmd)}{COLOR['reset']}")
    if not dry_run:
        run(cmd)
        _print_run_url(repo, "manual-test.yml")


def trigger_tt_forge_onnx_workflow(mlir_sha: str, dry_run: bool = False) -> None:
    """
    Trigger tt-forge-onnx on-pr.yml with mlir_override.
    """
    repo = GH_REPOS["tt-forge-onnx"]
    print(f"\n{COLOR['header']}==> Triggering tt-forge-onnx (on-pr.yml) with mlir_override={mlir_sha}...{COLOR['reset']}")
    # gh workflow run on-pr.yml -R tenstorrent/tt-forge-onnx -f mlir_override=<sha>
    cmd = [
        "gh", "workflow", "run", "on-pr.yml",
        "-R", repo,
        "-f", f"mlir_override={mlir_sha}"
    ]
    print(f"{COLOR['cmd']}   GH command: {_format_cmd(cmd)}{COLOR['reset']}")
    if not dry_run:
        run(cmd)
        _print_run_url(repo, "on-pr.yml")


def main() -> None:
    parser = argparse.ArgumentParser(description="Shotgun uplift tool to trigger FE workflows with a tt-mlir override.")
    # Positional branch argument (implied), with optional flag override
    parser.add_argument(
        "branch",
        nargs="?",
        help="tt-mlir branch to checkout and read HEAD SHA from (positional)"
    )
    parser.add_argument(
        "--mlir-uplift-branch",
        dest="branch_flag",
        help="tt-mlir branch to checkout and read HEAD SHA from (flag)"
    )
    parser.add_argument(
        "--tt-xla",
        action="store_true",
        help="Trigger tt-xla manual-test.yml with mlir-uplift-qualification.json"
    )
    parser.add_argument(
        "--tt-forge-onnx",
        action="store_true",
        help="Trigger tt-forge-onnx on-pr.yml"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print gh commands but do not execute them"
    )

    args = parser.parse_args()

    # Resolve branch from positional or flag
    branch = args.branch_flag or args.branch
    if not branch:
        print("Missing mlir uplift branch. Provide positional <branch> or --mlir-uplift-branch.", file=sys.stderr)
        sys.exit(2)

    # If neither target passed, run both and warn
    if not (args.tt_xla or args.tt_forge_onnx):
        print("Warning: no targets specified; triggering both tt-xla and tt-forge-onnx.")
        args.tt_xla = True
        args.tt_forge_onnx = True

    ensure_gh_cli()

    # Prepare tt-mlir repo
    repo_dir = clone_or_checkout_tt_mlir(branch)
    mlir_sha = get_head_sha(repo_dir)
    print(f"\n{COLOR['header']}Resolved tt-mlir HEAD on '{branch}': {mlir_sha}{COLOR['reset']}")

    # Trigger selected workflows
    if args.tt_xla:
        trigger_tt_xla(mlir_sha, dry_run=args.dry_run)
    if args.tt_forge_onnx:
        trigger_tt_forge_onnx_workflow(mlir_sha, dry_run=args.dry_run)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
