#!/usr/bin/env python3
"""
Regenerate the entire pip index by scanning all repos with .pip_index marker.

This script:
1. Finds all repos in MYAPPS_DIR that have .pip_index marker
2. Reads their pyproject.toml to get package name and version
3. Gets their current git commit hash
4. Gets their GitHub user/org from git remote
5. Calls update_pip_index.py to add them to the index

Usage:
    ./regenerate_pip_index.py
"""

import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


MYAPPS_DIR = Path.home() / "_myapps"
PIP_INDEX_REPO = MYAPPS_DIR / "pip-index"
UPDATE_SCRIPT = PIP_INDEX_REPO / "update_pip_index.py"
GITHUB_USER = "jakeogh"


def get_github_info(repo_path):
    """
    Get GitHub user/org and repo name from git remote.

    Returns:
        tuple: (github_user, github_repo) or (None, None)
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None, None

        remote_url = result.stdout.strip()

        pattern = r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$"
        match = re.search(pattern, remote_url)

        if match:
            github_user = match.group(1)
            github_repo = match.group(2)
            return github_user, github_repo

        print(f"WARNING: Could not parse remote URL: {remote_url}", file=sys.stderr)
        return None, None

    except subprocess.TimeoutExpired:
        print(f"WARNING: Timeout getting remote for {repo_path.name}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(
            f"WARNING: Error getting remote for {repo_path.name}: {e}", file=sys.stderr
        )
        return None, None


def get_git_commit(repo_path):
    """Get the current git commit hash for a repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def read_package_info(repo_path):
    """
    Read package name and version from pyproject.toml.

    Returns:
        tuple: (package_name, version) or (None, None)
    """
    pyproject_path = repo_path / "pyproject.toml"

    if not pyproject_path.exists():
        return None, None

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})
        return project.get("name"), project.get("version")
    except Exception as e:
        print(f"WARNING: Could not read {pyproject_path}: {e}", file=sys.stderr)
        return None, None


def find_repos_with_pip_index():
    """
    Find all repositories with .pip_index marker file.

    Returns:
        List of tuples: (repo_path, package_name, version, commit_hash)
    """
    repos = []

    if not MYAPPS_DIR.exists():
        print(f"ERROR: {MYAPPS_DIR} does not exist", file=sys.stderr)
        return repos

    for item in MYAPPS_DIR.iterdir():
        if not item.is_dir():
            continue

        # Skip special directories
        if item.name.startswith(".") or item.name == "pip-index":
            continue

        # Check for .pip_index marker
        if not (item / ".pip_index").exists():
            continue

        # Get package info
        package_name, version = read_package_info(item)
        if not package_name or not version:
            print(f"Skipping {item.name}: no package name or version", file=sys.stderr)
            continue

        # Get commit hash
        commit_hash = get_git_commit(item)
        if not commit_hash:
            print(f"Skipping {item.name}: not a git repo", file=sys.stderr)
            continue

        repos.append((item, package_name, version, commit_hash))
        print(f"Found: {package_name} {version} ({commit_hash[:8]})")

    return repos


def regenerate_index():
    """Regenerate the entire pip index."""
    if not UPDATE_SCRIPT.exists():
        print(f"ERROR: {UPDATE_SCRIPT} not found", file=sys.stderr)
        sys.exit(1)

    print("Finding repositories with .pip_index marker...")
    repos = find_repos_with_pip_index()

    if not repos:
        print("No repositories found with .pip_index marker")
        sys.exit(0)

    print(f"\nFound {len(repos)} repositories")
    print("\nRegenerating index...")

    for repo_path, package_name, version, commit_hash in sorted(
        repos, key=lambda x: x[1]
    ):
        print(f"\nAdding {package_name} {version}...")

        # Get GitHub user and repo from git remote
        github_user, github_repo = get_github_info(repo_path)

        if not github_user or not github_repo:
            print(
                f"WARNING: Could not determine GitHub info for {package_name}, using defaults",
                file=sys.stderr,
            )
            github_user = GITHUB_USER
            github_repo = repo_path.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(UPDATE_SCRIPT),
                    package_name,
                    version,
                    commit_hash,
                    "--index-repo",
                    str(PIP_INDEX_REPO),
                    "--github-user",
                    github_user,
                    "--github-repo",
                    github_repo,
                ],
                capture_output=True,
                text=True,
                timeout=10,  # 10 second timeout
            )
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"ERROR: Script returned {result.returncode}", file=sys.stderr)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
        except subprocess.TimeoutExpired:
            print(
                f"ERROR: Timeout adding {package_name} (update_pip_index.py hung)",
                file=sys.stderr,
            )
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to add {package_name}: {e}", file=sys.stderr)
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)

    print("\n" + "=" * 60)
    print("✓ Index regeneration complete!")
    print("\nNext steps:")
    print(f"  cd {PIP_INDEX_REPO}")
    print(f"  git add simple/")
    print(f"  git commit -m 'Regenerate index with fixed URLs'")
    print(f"  git push")


def main():
    print(f"MYAPPS_DIR: {MYAPPS_DIR}")
    print(f"PIP_INDEX_REPO: {PIP_INDEX_REPO}")
    print()

    regenerate_index()


def get_git_commit(repo_path):
    """Get the current git commit hash for a repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def read_package_info(repo_path):
    """
    Read package name and version from pyproject.toml.

    Returns:
        tuple: (package_name, version) or (None, None)
    """
    pyproject_path = repo_path / "pyproject.toml"

    if not pyproject_path.exists():
        return None, None

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})
        return project.get("name"), project.get("version")
    except Exception as e:
        print(f"WARNING: Could not read {pyproject_path}: {e}", file=sys.stderr)
        return None, None


def find_repos_with_pip_index():
    """
    Find all repositories with .pip_index marker file.

    Returns:
        List of tuples: (repo_path, package_name, version, commit_hash)
    """
    repos = []

    if not MYAPPS_DIR.exists():
        print(f"ERROR: {MYAPPS_DIR} does not exist", file=sys.stderr)
        return repos

    for item in MYAPPS_DIR.iterdir():
        if not item.is_dir():
            continue

        # Skip special directories
        if item.name.startswith(".") or item.name == "pip-index":
            continue

        # Check for .pip_index marker
        if not (item / ".pip_index").exists():
            continue

        # Get package info
        package_name, version = read_package_info(item)
        if not package_name or not version:
            print(f"Skipping {item.name}: no package name or version", file=sys.stderr)
            continue

        # Get commit hash
        commit_hash = get_git_commit(item)
        if not commit_hash:
            print(f"Skipping {item.name}: not a git repo", file=sys.stderr)
            continue

        repos.append((item, package_name, version, commit_hash))
        print(f"Found: {package_name} {version} ({commit_hash[:8]})")

    return repos


def regenerate_index():
    """Regenerate the entire pip index."""
    if not UPDATE_SCRIPT.exists():
        print(f"ERROR: {UPDATE_SCRIPT} not found", file=sys.stderr)
        sys.exit(1)

    print("Finding repositories with .pip_index marker...")
    repos = find_repos_with_pip_index()

    if not repos:
        print("No repositories found with .pip_index marker")
        sys.exit(0)

    print(f"\nFound {len(repos)} repositories")
    print("\nRegenerating index...")

    for repo_path, package_name, version, commit_hash in sorted(
        repos, key=lambda x: x[1]
    ):
        print(f"\nAdding {package_name} {version}...")

        # Get GitHub user and repo from git remote
        github_user, github_repo = get_github_info(repo_path)

        if not github_user or not github_repo:
            print(
                f"WARNING: Could not determine GitHub info for {package_name}, using defaults",
                file=sys.stderr,
            )
            github_user = GITHUB_USER
            github_repo = repo_path.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(UPDATE_SCRIPT),
                    package_name,
                    version,
                    commit_hash,
                    "--index-repo",
                    str(PIP_INDEX_REPO),
                    "--github-user",
                    github_user,
                    "--github-repo",
                    github_repo,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to add {package_name}: {e}", file=sys.stderr)
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)

    print("\n" + "=" * 60)
    print("✓ Index regeneration complete!")
    print("\nNext steps:")
    print(f"  cd {PIP_INDEX_REPO}")
    print(f"  git add simple/")
    print(f"  git commit -m 'Regenerate index with fixed URLs'")
    print(f"  git push")


def main():
    print(f"MYAPPS_DIR: {MYAPPS_DIR}")
    print(f"PIP_INDEX_REPO: {PIP_INDEX_REPO}")
    print()

    regenerate_index()


if __name__ == "__main__":
    main()
