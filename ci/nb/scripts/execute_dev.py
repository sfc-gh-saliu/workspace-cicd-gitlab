"""Generate EXECUTE NOTEBOOK PROJECT SQL files for DEV execution.

Reads affected_projects.json and creates one .sql file per project
containing the full EXECUTE NOTEBOOK PROJECT statement with all
required and optional parameters. Writes execute_projects.txt with
the list of project names for the bash execution loop.
"""

import json
import os

projects = json.load(open("affected_projects.json"))
names = []
for p in projects:
    name = p["project_name"]
    deploy = p.get("deploy", {})
    execute = p.get("execute", {})

    db = deploy.get("database", os.environ.get("DEFAULT_SNOWFLAKE_NOTEBOOK_DATABASE", ""))
    schema = deploy.get("schema", os.environ.get("DEFAULT_SNOWFLAKE_NOTEBOOK_SCHEMA", ""))
    prefix = f"{db}.{schema}" if db and schema else ""

    npo = deploy.get("notebook_project")
    if npo and prefix:
        npo = f"{prefix}.{npo}"
    else:
        npo = os.environ["DEFAULT_SNOWFLAKE_NOTEBOOK_NPO"]

    parts = [
        "EXECUTE NOTEBOOK PROJECT {}".format(npo),
        "  MAIN_FILE = '{}'".format(p["main_file"]),
        "  COMPUTE_POOL = '{}'".format(
            execute.get("compute_pool", os.environ["DEFAULT_SNOWFLAKE_NOTEBOOK_COMPUTE_POOL"])),
        "  QUERY_WAREHOUSE = '{}'".format(
            execute.get("query_warehouse", os.environ["DEFAULT_SNOWFLAKE_NOTEBOOK_QUERY_WAREHOUSE"])),
        "  RUNTIME = '{}'".format(
            execute.get("runtime", os.environ.get("DEFAULT_SNOWFLAKE_NOTEBOOK_RUNTIME", "V2.5-CPU-PY3.12"))),
    ]

    args = execute.get("arguments", "")
    if args:
        parts.append("  ARGUMENTS = '{}'".format(args))

    req = execute.get("requirements_file", os.environ.get("DEFAULT_SNOWFLAKE_NOTEBOOK_REQUIREMENTS_FILE", ""))
    if req:
        parts.append("  REQUIREMENTS_FILE = '{}'".format(req))

    artifact_repos = execute.get("artifact_repositories", [])
    if artifact_repos:
        repos_str = ", ".join(artifact_repos) if isinstance(artifact_repos, list) else artifact_repos
        parts.append("  ARTIFACT_REPOSITORIES = ({})".format(repos_str))

    eai = execute.get("external_access_integrations", [])
    if eai:
        eai_str = ", ".join(eai) if isinstance(eai, list) else eai
        parts.append("  EXTERNAL_ACCESS_INTEGRATIONS = ({})".format(eai_str))

    secrets = execute.get("secrets", [])
    if secrets:
        secrets_str = ", ".join(secrets) if isinstance(secrets, list) else secrets
        parts.append("  SECRETS = ({})".format(secrets_str))

    sql = "\n".join(parts) + ";"
    with open("execute_{}.sql".format(name), "w") as f:
        f.write(sql)
    names.append(name)

with open("execute_projects.txt", "w") as f:
    f.write("\n".join(names))
