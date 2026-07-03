# Snowflake Connection Setup

This guide covers how to configure Snowflake CLI connections for the CI/CD pipeline. The pipeline uses the Snowflake CLI (`snow`) to deploy notebook projects and run smoke tests against DEV and PROD Snowflake accounts.

## How It Works

GitLab does not connect to Snowflake directly. The connection happens entirely within the CI **runner** (the machine that executes jobs):

1. Snowflake connection parameters are stored as GitLab CI/CD variables
2. When a pipeline runs, GitLab injects them as environment variables into the runner
3. The Snowflake CLI reads these environment variables automatically — no config file needed
4. The variables exist only for the duration of the job and never touch disk

The Snowflake CLI supports environment variables in the format `SNOWFLAKE_CONNECTIONS_<NAME>_<PARAM>`, which define named connections entirely in memory:

```
Pipeline job starts
  → GitLab injects SNOWFLAKE_CONNECTIONS_DEV_* env vars
  → script: snow sql --connection dev ...
  → snow CLI reads env vars, finds connection "dev"
  → authenticates to Snowflake DEV account via key-pair
  → job ends, env vars gone
```

No credentials are written to disk at any point.

## 1. Create a Snowflake Service Account

Create a dedicated service account in each Snowflake account (DEV and PROD) for CI/CD use:

```sql
-- Run this in each Snowflake account
USE ROLE SECURITYADMIN;

SET ci_role = 'CI_PIPELINE_ROLE';
SET ci_user = 'CI_PIPELINE_USER';

CREATE ROLE IF NOT EXISTS IDENTIFIER($ci_role);
CREATE USER IF NOT EXISTS IDENTIFIER($ci_user)
  DEFAULT_ROLE = $ci_role
  TYPE = SERVICE;
GRANT ROLE IDENTIFIER($ci_role) TO USER IDENTIFIER($ci_user);
```

Grant the role the minimum permissions needed for your workflows:

```sql
-- Notebook workflow permissions
GRANT USAGE ON DATABASE <database> TO ROLE IDENTIFIER($ci_role);
GRANT USAGE ON SCHEMA <database>.<schema> TO ROLE IDENTIFIER($ci_role);
GRANT CREATE STAGE ON SCHEMA <database>.<schema> TO ROLE IDENTIFIER($ci_role);
GRANT READ, WRITE ON STAGE <database>.<schema>.<stage> TO ROLE IDENTIFIER($ci_role);
GRANT CREATE NOTEBOOK PROJECT ON SCHEMA <database>.<schema> TO ROLE IDENTIFIER($ci_role);
```

> Adjust the database, schema, and stage names to match your manifest (`notebook_manifest.yml`) or `DEFAULT_SNOWFLAKE_NOTEBOOK_*` CI/CD variables.

## 2. Generate Key Pairs

Generate a separate key pair for each environment:

```bash
# DEV key pair
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key_dev.p8 -nocrypt
openssl rsa -in rsa_key_dev.p8 -pubout -out rsa_key_dev.pub

# PROD key pair
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key_prod.p8 -nocrypt
openssl rsa -in rsa_key_prod.p8 -pubout -out rsa_key_prod.pub
```

Assign the public keys in each Snowflake account:

```sql
-- Run in DEV account
ALTER USER IDENTIFIER($ci_user) SET RSA_PUBLIC_KEY='<contents of rsa_key_dev.pub, without header/footer lines>';

-- Run in PROD account
ALTER USER IDENTIFIER($ci_user) SET RSA_PUBLIC_KEY='<contents of rsa_key_prod.pub, without header/footer lines>';
```

> After assigning the keys and adding them to GitLab (step 3), delete the local key files. They should not be stored anywhere else.

## 3. Add CI/CD Variables in GitLab

Go to **Settings > CI/CD > Variables** and add the following.

The variable names below follow the Snowflake CLI's required naming convention: `SNOWFLAKE_CONNECTIONS_<NAME>_<PARAM>`. The Snowflake CLI automatically reads any environment variable matching this pattern and uses it to configure named connections — no config file is needed. These are not GitLab built-in variables; GitLab simply stores them and injects them as environment variables into the runner, where the Snowflake CLI picks them up.

### DEV connection (`SNOWFLAKE_CONNECTIONS_DEV_*`)

| Variable | Value | Protected | Masked |
|---|---|---|---|
| `SNOWFLAKE_CONNECTIONS_DEV_ACCOUNT` | DEV account identifier (e.g. `org-account_dev`) | Yes | No |
| `SNOWFLAKE_CONNECTIONS_DEV_USER` | DEV service account username | Yes | No |
| `SNOWFLAKE_CONNECTIONS_DEV_ROLE` | DEV CI role (e.g. `CI_PIPELINE_ROLE`) | Yes | No |
| `SNOWFLAKE_CONNECTIONS_DEV_WAREHOUSE` | DEV warehouse for queries | Yes | No |
| `SNOWFLAKE_CONNECTIONS_DEV_AUTHENTICATOR` | `SNOWFLAKE_JWT` | Yes | No |
| `SNOWFLAKE_CONNECTIONS_DEV_PRIVATE_KEY_FILE` | Contents of `rsa_key_dev.p8` (full PEM including header/footer) — set type to **File** | Yes | No |

### PROD connection (`SNOWFLAKE_CONNECTIONS_PROD_*`)

| Variable | Value | Protected | Masked |
|---|---|---|---|
| `SNOWFLAKE_CONNECTIONS_PROD_ACCOUNT` | PROD account identifier (e.g. `org-account_prod`) | Yes | No |
| `SNOWFLAKE_CONNECTIONS_PROD_USER` | PROD service account username | Yes | No |
| `SNOWFLAKE_CONNECTIONS_PROD_ROLE` | PROD CI role (e.g. `CI_PIPELINE_ROLE`) | Yes | No |
| `SNOWFLAKE_CONNECTIONS_PROD_WAREHOUSE` | PROD warehouse for queries | Yes | No |
| `SNOWFLAKE_CONNECTIONS_PROD_AUTHENTICATOR` | `SNOWFLAKE_JWT` | Yes | No |
| `SNOWFLAKE_CONNECTIONS_PROD_PRIVATE_KEY_FILE` | Contents of `rsa_key_prod.p8` (full PEM including header/footer) — set type to **File** | Yes | No |

### Connection name references

| Variable | Value | Protected | Masked |
|---|---|---|---|
| `SNOWFLAKE_CONNECTION_DEV` | `dev` | Yes | No |
| `SNOWFLAKE_CONNECTION_PROD` | `prod` | Yes | No |

These are passed to scripts as arguments and map to `--connection dev` / `--connection prod` in `snow` CLI commands.

* **Protected:** ensures variables are only available on protected branches (`dev` and `main`)
* **`PRIVATE_KEY_FILE`:** set the variable type to **File** in GitLab. GitLab writes the PEM content to a temp file and sets the variable to the file path. The Snowflake CLI reads the key from that path. The temp file is cleaned up when the job ends.

## 4. Authentication

The pipeline authenticates to Snowflake using **key-pair authentication with JWT (JSON Web Tokens)**. The authenticator value `SNOWFLAKE_JWT` in the connection variables enables this method.

### How it works

1. During setup (step 2), you generate an RSA key pair — a private key and a public key
2. The public key is registered with the Snowflake service account user (`ALTER USER ... SET RSA_PUBLIC_KEY=...`)
3. The private key is stored as a GitLab CI/CD **File** variable (`PRIVATE_KEY_FILE`)
4. At runtime, GitLab writes the key to a temp file and the Snowflake CLI reads it to generate a short-lived JWT token
5. The JWT is sent to Snowflake, which verifies the signature against the stored public key
6. If the signature matches, the connection is authenticated

### Why it's secure

* **No passwords** — there is no password to leak, rotate, or accidentally commit. Authentication relies on cryptographic key pairs instead
* **Ephemeral file** — the private key is written to a temp file by GitLab for the duration of the job only. It is automatically cleaned up when the job ends
* **Short-lived tokens** — the JWT generated from the private key is valid for a brief window. Even if intercepted, it expires quickly
* **Asymmetric cryptography** — the public key stored in Snowflake cannot be used to authenticate. Only the holder of the private key can generate valid JWTs
* **Not exposed in logs** — the variable value in logs is the temp file path, not the key content itself
* **Protected variables** — GitLab only injects the credentials on protected branches (`dev` and `main`), so rogue jobs on feature branches cannot access them

## 5. How the Pipeline Uses Connections

The pipeline scripts receive the connection name as an argument and pass it to `snow`:

| Job | Connection variable | What it does |
|---|---|---|
| `nb_deploy_to_dev` | `$SNOWFLAKE_CONNECTION_DEV` | Creates stages, uploads files, creates/updates Notebook Projects in DEV |
| `nb_execute_in_dev` | `$SNOWFLAKE_CONNECTION_DEV` | Executes notebooks in DEV as smoke tests |
| `nb_deploy_to_prod` | `$SNOWFLAKE_CONNECTION_PROD` | Creates stages, uploads files, creates/updates Notebook Projects in PROD |

The `snow` CLI resolves `--connection dev` by reading the `SNOWFLAKE_CONNECTIONS_DEV_*` environment variables. No `config.toml` file is involved.

The job `before_script` only needs to install the CLI:

```yaml
before_script:
  - pip install --upgrade snowflake-cli
  - snow --version
```

## 6. Verify the Setup

Test the connection in a pipeline job:

1. Create a feature branch and add a temporary test job:
   ```yaml
   test_snowflake:
     before_script:
       - pip install --upgrade snowflake-cli
     script:
       - snow sql --connection dev -q "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE(), CURRENT_WAREHOUSE();"
       - snow sql --connection prod -q "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE(), CURRENT_WAREHOUSE();"
   ```
2. Push and trigger the pipeline
3. Confirm both connections authenticate and return the expected account, role, and warehouse
4. Remove the test job after verification