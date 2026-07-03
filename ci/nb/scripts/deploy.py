"""Generate a TSV of affected projects with deployment targets.

Reads affected_projects.json and outputs one TSV row per project with
name, path, stage, and notebook project for the bash deploy loop.

Usage: python deploy.py
"""

import json
import os

projects = json.load(open("affected_projects.json"))
for p in projects:
    deploy = p.get("deploy", {})

    db = deploy.get("database", os.environ.get("DEFAULT_SNOWFLAKE_NOTEBOOK_DATABASE", ""))
    schema = deploy.get("schema", os.environ.get("DEFAULT_SNOWFLAKE_NOTEBOOK_SCHEMA", ""))
    prefix = f"{db}.{schema}" if db and schema else ""

    stage = deploy.get("stage")
    if stage and prefix:
        stage = f"{prefix}.{stage}"
    else:
        stage = os.environ["DEFAULT_SNOWFLAKE_NOTEBOOK_STAGE"]

    npo = deploy.get("notebook_project")
    if npo and prefix:
        npo = f"{prefix}.{npo}"
    else:
        npo = os.environ["DEFAULT_SNOWFLAKE_NOTEBOOK_NPO"]

    print("\t".join([p["project_name"], p["project_path"], stage, npo]))
