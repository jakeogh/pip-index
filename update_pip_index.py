#!/usr/bin/env python3
"""
Update pip index with a new package version.

This script updates the custom pip index hosted on GitHub Pages to include
a new version of a package, pointing to GitHub's automatic tarball URL.

Usage:
    update_pip_index.py PACKAGE_NAME VERSION COMMIT_HASH [--index-repo PATH]

Example:
    update_pip_index.py eprint 0.0.1760909962 abc123def456 --index-repo ~/.myapps/pip-index

The script:
1. Updates simple/{package}/index.html with the new version
2. Updates simple/index.html to include the package if not listed
3. Does NOT commit - caller should commit/push
"""

import argparse
import re
from pathlib import Path


def create_package_index_html(package_name, versions_data):
    """
    Create the index.html for a specific package.

    Args:
        package_name: Name of the package
        versions_data: List of tuples (version, commit_hash, github_user, github_repo)

    Returns:
        str: HTML content
    """
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Links for {package}</title>
</head>
<body>
    <h1>Links for {package}</h1>
""".format(package=package_name)

    for version, commit_hash, github_user, github_repo in versions_data:
        tarball_url = f"https://github.com/{github_user}/{github_repo}/archive/{commit_hash}.tar.gz"
        link_url = f"{tarball_url}#egg={package_name}-{version}"
        link_text = f"{package_name}-{version}"
        html += f'    <a href="{link_url}">{link_text}</a><br>\n'

    html += """</body>
</html>
"""
    return html


def create_root_index_html(packages):
    """
    Create the root simple/index.html listing all packages.

    Args:
        packages: List of package names

    Returns:
        str: HTML content
    """
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Simple Index</title>
</head>
<body>
    <h1>Simple Index</h1>
"""

    for package in sorted(packages):
        html += f'    <a href="{package}/">{package}</a><br>\n'

    html += """</body>
</html>
"""
    return html


def load_existing_versions(package_dir):
    """
    Load existing versions from a package's index.html.

    Returns:
        List of tuples (version, commit_hash, github_user, github_repo)
    """
    index_file = package_dir / "index.html"
    if not index_file.exists():
        return []

    versions = []
    content = index_file.read_text()

    pattern = r'href="https://github\.com/([^/]+)/([^/]+)/archive/([^"#]+)\.tar\.gz(?:#egg=[^"]+)?">([^<]+)</a>'

    for match in re.finditer(pattern, content):
        github_user = match.group(1)
        github_repo = match.group(2)
        commit_hash = match.group(3)
        link_text = match.group(4)

        if link_text.endswith('.tar.gz'):
            version = link_text.replace(".tar.gz", "").split("-", 1)[1]
        else:
            version = link_text.split("-", 1)[1] if "-" in link_text else link_text

        versions.append((version, commit_hash, github_user, github_repo))

    return versions


def update_index(index_repo, package_name, version, commit_hash, github_user, github_repo):
    """
    Update the pip index with a new package version.

    Args:
        index_repo: Path to the pip-index repository
        package_name: Name of the package
        version: Version string
        commit_hash: Git commit hash
        github_user: GitHub username
        github_repo: GitHub repository name
    """
    index_repo = Path(index_repo)
    simple_dir = index_repo / "simple"
    package_dir = simple_dir / package_name

    package_dir.mkdir(parents=True, exist_ok=True)

    versions = load_existing_versions(package_dir)

    new_version = (version, commit_hash, github_user, github_repo)

    versions = [v for v in versions if v[0] != version]
    versions.append(new_version)

    versions.sort(key=lambda x: x[0])

    package_html = create_package_index_html(package_name, versions)
    (package_dir / "index.html").write_text(package_html)

    print(f"Updated {package_name} index: {len(versions)} version(s)")

    update_root_index(simple_dir)


def update_root_index(simple_dir):
    """
    Update the root simple/index.html with all packages.
    """
    packages = []
    for item in simple_dir.iterdir():
        if item.is_dir() and item.name != ".git":
            packages.append(item.name)

    root_html = create_root_index_html(packages)
    (simple_dir / "index.html").write_text(root_html)

    print(f"Updated root index: {len(packages)} package(s)")


def main():
    parser = argparse.ArgumentParser(description="Update pip index with a new package version")
    parser.add_argument("package", help="Package name")
    parser.add_argument("version", help="Package version")
    parser.add_argument("commit", help="Git commit hash")
    parser.add_argument("--index-repo", default=str(Path.home() / "_myapps" / "pip-index"), help="Path to pip-index repository")
    parser.add_argument("--github-user", default="jakeogh", help="GitHub username")
    parser.add_argument("--github-repo", help="GitHub repo name (default: same as package name)")

    args = parser.parse_args()

    github_repo = args.github_repo or args.package

    update_index(args.index_repo, args.package, args.version, args.commit, args.github_user, github_repo)

    print(f"\nTo publish changes:")
    print(f"  cd {args.index_repo}")
    print(f"  git add simple/")
    print(f"  git commit -m 'Update {args.package} to {args.version}'")
    print(f"  git push")


if __name__ == "__main__":
    main()
