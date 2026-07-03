# DCM Workflow

Triggered by changes to `dcm-projects/**/*`.

```mermaid
flowchart TD
    MR["MR Created"] --> Review["Code Review & Approval"]
    Review --> MergeDev["Merge to dev"]
    MergeDev --> Validate["stage: validate\njob: dcm_validate"]
    Validate --> DeployDev["stage: deploy_dev\njob: dcm_deploy_to_dev"]
    DeployDev --> DeployProd["stage: deploy_prod\njob: dcm_deploy_to_prod"]
    DeployProd -->|success| Promote["stage: promote\njob: promote_to_main"]
    Validate -->|failure| Rollback["stage: rollback\njob: rollback_dev"]
    DeployDev -->|failure| Rollback
    DeployProd -->|failure| Rollback
```
