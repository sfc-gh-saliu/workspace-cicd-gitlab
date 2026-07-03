# CI Bot Setup

This guide covers how to create and configure the CI bot using a **Project Access Token**. The pipeline uses this bot to promote `dev` to `main` and rollback `dev` on failure.

## 1. Create a Project Access Token

1. Go to **Settings > Access Tokens** in your project
2. Create a new token:
   * **Token name:** `ci-pipeline-bot`
   * **Role:** Developer (push access to protected branches is granted separately in step 2)
   * **Scopes:** select `write_repository`
   * **Expiration:** set per your security policy (rotate before it expires)
3. Click **Create project access token**
4. Copy the **token value** — this is the only time it is shown

> GitLab automatically creates a bot user associated with the token. This bot user is added to the project as a member with the role you selected. No separate user creation or member invitation is needed.
>
> To find the bot username: go to **Manage > Members** — the bot appears as a member with the token name. Its username follows the format `project_{project_id}_bot_{random_string}`.
>
> **Note:** For Git over HTTPS, GitLab does not validate the username — any non-blank value works. The pipeline uses `GITLAB_CI_BOT_USER` as a convention, but you can set it to any value (e.g. `gitlab-ci-bot`).

## 2. Configure Protected Branch Access

The bot must be allowed to push to both protected branches:

### For `main`:
1. Go to **Settings > Repository > Protected branches**
2. Find the `main` branch (or the value of `MAIN_BRANCH` in `ci/variables.yml`)
3. **Allowed to merge:** No one
4. **Allowed to push and merge:** No one, then add the bot user as the only exception
5. **Allow force push:** disabled
6. **Require code owner approval:** enabled

> No human can push or merge to `main`. The bot performs a fast-forward push (`git push origin dev:main`) during the promote stage — this requires push access only, not merge access. Protected branches cannot be deleted by default in GitLab.

### For `dev`:
1. Find the `dev` branch (or the value of `DEV_BRANCH` in `ci/variables.yml`)
2. **Allowed to merge:** Developers and above (so team members can merge MRs)
3. **Allowed to push and merge:** No one, then add the bot user as the only exception
4. **Allow force push:** enabled (required for rollback — the bot uses `git push --force` to reset `dev`)
5. **Require code owner approval:** enabled (enforces `CODEOWNERS` rules on every MR)

> Developers merge MRs into `dev`, but cannot push directly. The bot pushes only during rollback (`git push --force origin main:dev`).

## 3. Add CI/CD Variables

Go to **Settings > CI/CD > Variables** and add the following:

| Variable | Value | Protected | Masked | Description |
|---|---|---|---|---|
| `GITLAB_CI_BOT_USER` | any non-blank value (e.g. `gitlab-ci-bot`) | Yes | No | Username for git remote HTTPS auth (not validated by GitLab) |
| `GITLAB_CI_BOT_TOKEN` | *(the token value from step 1)* | Yes | Yes | Project access token for git remote authentication |

* **Protected:** ensures the variables are only available to pipelines running on protected branches (`dev` and `main`)
* **Masked:** hides the token value from job logs

> These variables are used in `ci/promote.yml` and `ci/rollback.yml` to construct the authenticated remote URL:
> ```
> https://${GITLAB_CI_BOT_USER}:${GITLAB_CI_BOT_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git
> ```

## 4. Configure Pipeline Settings

Go to **Settings > CI/CD > General pipelines** and enable **Auto-cancel redundant pipelines**. This cancels older running pipelines when a newer commit is pushed to `dev`.

### Auto-cancel redundant pipelines

This works together with the `interruptible: true` flag on workflow stages and `resource_group` on promote/rollback jobs to prevent race conditions. See the [Concurrency Control](../README.md#concurrency-control) section in README for details.

## 5. Pipeline Failure Notifications

### Option A: GitLab built-in email notifications (per user)

Each team member can enable pipeline failure emails from their own settings:

1. Go to **User Settings > Notifications**
2. Find the project and set notification level to **Custom**
3. Enable **Failed pipeline**

This sends an email to the user when a pipeline they triggered (via merge) fails.

### Option B: Project-level notification emails

To notify a group/team email address on every failure:

1. Go to **Settings > Integrations > Pipeline status emails**
2. Add recipient email addresses (comma-separated)
3. Check **Notify only broken pipelines**
4. Save

### Option C: Slack / Microsoft Teams notifications

For chat-based notifications:

1. Go to **Settings > Integrations**
2. Select **Slack notifications** or **Microsoft Teams notifications**
3. Enable the integration and configure:
   * **Webhook URL:** from your Slack/Teams channel
   * **Trigger:** check **Pipeline** events
   * **Notify only broken pipelines:** recommended
4. Save

### Option D: CI job-level notification (custom email in pipeline)

Add a notification job directly in the pipeline for full control. Add this to `ci/no-deployment.yml` or create a separate `ci/notify.yml`:

```yaml
notify_on_failure:
  stage: rollback
  when: on_failure
  variables:
    GIT_STRATEGY: none
  before_script: []
  script:
    - |
      echo "Pipeline #${CI_PIPELINE_ID} failed on branch ${DEV_BRANCH}"
      echo "Commit: ${CI_COMMIT_SHA}"
      echo "Author: ${CI_COMMIT_AUTHOR}"
      echo "See: ${CI_PIPELINE_URL}"

      # Send email via SMTP (requires mailx or curl + SMTP relay)
      # echo "Pipeline ${CI_PIPELINE_URL} failed" | mail -s "CI Failure: ${CI_PROJECT_NAME}" team@example.com

      # Or use curl with a webhook (Slack, Teams, PagerDuty, etc.)
      # curl -X POST -H 'Content-type: application/json' \
      #   --data "{\"text\":\"Pipeline failed: ${CI_PIPELINE_URL}\"}" \
      #   "$SLACK_WEBHOOK_URL"
```

> Option B (project-level emails) is recommended as the simplest approach that requires no pipeline changes.

## 6. Verify the Setup

After completing all steps, verify with a test:

1. Create a feature branch with a small change (e.g. edit a comment in a file)
2. Open an MR targeting `dev`, get approval, and merge
3. Watch the pipeline — confirm:
   * Pipeline triggers on the `dev` branch
   * Promote job succeeds and `main` is updated
   * The project access token bot appears as the author of the push to `main`

To test rollback, temporarily introduce a failing step (e.g. `exit 1` in a script) and confirm `dev` is reset to `main` after failure.

## Variable Reference

All variables used by the CI bot, and where they are defined:

| Variable | Defined in | Purpose |
|---|---|---|
| `MAIN_BRANCH` | `ci/variables.yml` | Target branch for promote |
| `DEV_BRANCH` | `ci/variables.yml` | Trigger branch and rollback target |
| `CI_BOT_EMAIL` | `ci/variables.yml` | Git commit email for bot pushes |
| `CI_BOT_NAME` | `ci/variables.yml` | Git commit author name for bot pushes |
| `GITLAB_CI_BOT_USER` | GitLab CI/CD Variables | Bot username for HTTPS auth |
| `GITLAB_CI_BOT_TOKEN` | GitLab CI/CD Variables | Bot token for HTTPS auth (masked) |
| `CI_SERVER_HOST` | GitLab predefined | Hostname of the GitLab instance |
| `CI_PROJECT_PATH` | GitLab predefined | Full path of the project (e.g. `group/repo`) |
| `CI_COMMIT_SHA` | GitLab predefined | Current commit SHA |
