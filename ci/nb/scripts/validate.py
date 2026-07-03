"""Validate affected notebook projects.

Checks that each project's main_file exists, validates .ipynb files as
valid notebook JSON, and compiles .py files to catch syntax errors.
"""

import json
import os
import py_compile

projects = json.load(open("affected_projects.json"))

for project in projects:
    root = project["project_path"]
    main_file = os.path.join(root, project["main_file"])

    if not os.path.exists(main_file):
        raise FileNotFoundError(f"Main file not found: {main_file}")

    if main_file.endswith(".ipynb"):
        with open(main_file) as fh:
            nb = json.load(fh)
        if "cells" not in nb:
            raise ValueError(f"Notebook missing cells array: {main_file}")
    elif main_file.endswith(".py"):
        py_compile.compile(main_file, doraise=True)
    else:
        raise ValueError(f"Unsupported main file type: {main_file}")

    main_file_abs = os.path.abspath(main_file)

    for base, _, files in os.walk(root):
        for name in files:
            full = os.path.join(base, name)
            if os.path.abspath(full) == main_file_abs:
                continue
            if name.endswith(".ipynb"):
                with open(full) as fh:
                    json.load(fh)
            elif name.endswith(".py"):
                py_compile.compile(full, doraise=True)

    print(f"Validated project: {project['project_name']}")
    print(f"  root: {root}")
    print(f"  main_file: {project['main_file']}")
