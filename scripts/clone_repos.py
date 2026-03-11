#!/usr/bin/env python3
"""Clone repos from config.yaml.

Tries to fetch at the pinned SHA. Falls back to cloning the branch HEAD
if the server disables fetch-by-SHA (common on GitHub).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

CONFIG_SEARCH_PATHS = [
    Path("/app/config.yaml"),
    Path(__file__).resolve().parent.parent / "config.yaml",
]


def load_config():
    try:
        import yaml
    except ImportError:
        return {}

    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            return yaml.safe_load(path.read_text()) or {}
    return {}


def clone(url, ref, dest):
    """Clone a repo. Tries fetch-by-SHA, falls back to shallow clone."""
    # Try fetch by exact SHA (fast, minimal data)
    subprocess.run(["git", "init", str(dest)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(dest), "remote", "add", "origin", url],
        check=True, capture_output=True,
    )

    result = subprocess.run(
        ["git", "-C", str(dest), "fetch", "--depth", "1", "origin", ref],
        capture_output=True,
    )

    if result.returncode == 0:
        subprocess.run(
            ["git", "-C", str(dest), "checkout", "FETCH_HEAD"],
            check=True, capture_output=True,
        )
    else:
        # Server doesn't allow fetch-by-SHA, fall back to shallow clone
        shutil.rmtree(dest, ignore_errors=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True, capture_output=True,
        )

    result = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    sha = result.stdout.strip()
    shutil.rmtree(dest / ".git", ignore_errors=True)
    return sha


def clone_repos(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    config = load_config()
    commits = {}

    for repo in config.get("repos", []):
        name = repo["name"]
        ref = repo.get("ref", "HEAD")
        print(f"Cloning {name} @ {ref[:12]}...")
        commits[name] = clone(repo["url"], ref, data_dir / name)

    catalog = config.get("catalog", {})
    catalog_url = catalog.get("url", "")
    for env_name, env_data in catalog.get("environments", {}).items():
        ref = env_data.get("ref", env_data.get("branch", "HEAD"))
        dir_name = f"{catalog.get('repo', 'release-service-catalog')}-{env_name}"
        print(f"Cloning catalog/{env_name} @ {ref[:12]}...")
        commits[dir_name] = clone(catalog_url, ref, data_dir / dir_name)

    (data_dir / "commits.json").write_text(json.dumps(commits, indent=2))
    print(f"\nCloned {len(commits)} repo(s) to {data_dir}")
    for name, sha in commits.items():
        print(f"  {name}: {sha[:12]}")


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data")
    clone_repos(data_dir)


if __name__ == "__main__":
    main()
