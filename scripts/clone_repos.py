#!/usr/bin/env python3
"""Clone repos at pinned SHAs from config.yaml.

For standard repos: clones at the pinned ref.
For catalog: clones each environment (development/staging/production) at its pinned ref.
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


def load_config() -> dict:
    try:
        import yaml
    except ImportError:
        return {}

    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            return yaml.safe_load(path.read_text()) or {}
    return {}


def clone_at_ref(url: str, ref: str, dest: Path) -> str:
    """Clone a repo and checkout a specific commit. Returns the actual SHA."""
    subprocess.run(
        ["git", "clone", "--no-checkout", url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(dest), "checkout", ref],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    sha = result.stdout.strip()
    shutil.rmtree(dest / ".git", ignore_errors=True)
    return sha


def clone_repos(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    config = load_config()
    commits: dict[str, str] = {}

    # Clone standard repos at pinned ref
    for repo in config.get("repos", []):
        name = repo["name"]
        url = repo["url"]
        ref = repo.get("ref", "HEAD")
        dest = data_dir / name

        print(f"Cloning {name} @ {ref[:12]}...")
        commits[name] = clone_at_ref(url, ref, dest)

    # Clone catalog per environment
    catalog = config.get("catalog", {})
    catalog_url = catalog.get("url", "")
    for env_name, env_data in catalog.get("environments", {}).items():
        ref = env_data.get("ref", env_data.get("branch", "HEAD"))
        dir_name = f"{catalog.get('repo', 'release-service-catalog')}-{env_name}"
        dest = data_dir / dir_name

        print(f"Cloning catalog/{env_name} @ {ref[:12]}...")
        commits[dir_name] = clone_at_ref(catalog_url, ref, dest)

    (data_dir / "commits.json").write_text(json.dumps(commits, indent=2))
    print(f"\nCloned {len(commits)} repo(s) to {data_dir}")
    for name, sha in commits.items():
        print(f"  {name}: {sha[:12]}")


def main() -> None:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/data")
    clone_repos(data_dir)


if __name__ == "__main__":
    main()
