"""Detect changed notebook files and resolve them to manifest projects.

Diffs the commit, filters to notebooks/, cross-references against the
manifest, and writes affected_projects.json for downstream stages.

Changeset strategy:
- Added/modified files must belong to a registered project (strict)
- Deleted files inside a project trigger redeployment (strict)
- Deleted files outside any project are silently ignored (lenient)
"""

import json
import os
import subprocess
import sys
import yaml

before = os.environ["CI_COMMIT_BEFORE_SHA"]
after = os.environ["CI_COMMIT_SHA"]
manifest_file = os.environ["NOTEBOOK_MANIFEST_FILE"]

with open(manifest_file) as f:
    manifest = yaml.safe_load(f)

non_deleted = subprocess.check_output(
    ["git", "diff", "--name-only", "--diff-filter=d", before, after],
    text=True
).splitlines()

deleted = subprocess.check_output(
    ["git", "diff", "--name-only", "--diff-filter=D", before, after],
    text=True
).splitlines()

non_deleted_notebooks = [p for p in non_deleted if p.startswith("notebooks/")]
deleted_notebooks = [p for p in deleted if p.startswith("notebooks/")]

matched = []
unmatched = []
ignored_deletions = []
manifest_changed = False


def match_project(path):
    for project in manifest["projects"]:
        root = project["project_path"].rstrip("/") + "/"
        if path.startswith(root) or path == project["project_path"]:
            return project
    return None


for path in non_deleted_notebooks:
    if path == manifest_file:
        manifest_changed = True
        continue
    project = match_project(path)
    if project:
        matched.append(project)
    else:
        unmatched.append(path)

for path in deleted_notebooks:
    if path == manifest_file:
        manifest_changed = True
        continue
    project = match_project(path)
    if project:
        matched.append(project)
    else:
        ignored_deletions.append(path)

dedup = []
seen = set()
for p in matched:
    if p["project_name"] not in seen:
        dedup.append(p)
        seen.add(p["project_name"])

if unmatched:
    print("Notebook changes found but not mapped in manifest:")
    for p in unmatched:
        print("  -", p)
    sys.exit(1)

with open("affected_projects.json", "w") as f:
    json.dump(dedup, f, indent=2)

if non_deleted_notebooks:
    print("Added/modified files:")
    for p in non_deleted_notebooks:
        print("  -", p)

if deleted_notebooks:
    print("Deleted files:")
    for p in deleted_notebooks:
        print("  -", p)

if ignored_deletions:
    print("Ignored deletions (not in any project):")
    for p in ignored_deletions:
        print("  -", p)

if manifest_changed:
    print(f"Manifest changed: {manifest_file}")

print(f"Affected projects: {len(dedup)}")
