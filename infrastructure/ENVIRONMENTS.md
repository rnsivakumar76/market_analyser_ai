# 🌿 Dev/Prod Environment Guide

## Branch Strategy

```
main (production)  ←── PR merge ──── develop (DEV/staging)
                                        │
                                        ├── feature/dynamo-migration
                                        ├── feature/new-alerts
                                        └── bugfix/price-fix
```

### Daily Workflow

```bash
# 1. Start work from develop
git checkout develop
git pull origin develop
git checkout -b feature/my-new-feature

# 2. Work on feature, commit as you go
git add -A && git commit -m "feat: my changes"

# 3. Push and create PR → develop
git push -u origin feature/my-new-feature
# → Go to GitHub and create PR targeting `develop`

# 4. Merge PR → auto-deploys to DEV environment
# 5. Test in DEV. When ready, create PR from `develop` → `main`
# 6. Approve PR → auto-deploys to PRODUCTION
```

## AWS Resources per Environment

| Resource | DEV | PRODUCTION |
|---|---|---|
| Lambda | `market-analyser-api` (dev workspace) | `market-analyser-api` (prod workspace) |
| DynamoDB | `nexus-dev` | `nexus-production` |
| S3 Frontend | `market-analyser-frontend-dev-*` | `market-analyser-frontend-*` |
| API Gateway | Dev stage | Prod stage |

## GitHub Setup Required

### 1. Create `dev` GitHub Environment
- Go to **Settings → Environments → New environment**
- Name: `dev`
- No approval required (auto-deploy on push to `develop`)

### 2. Production Environment (already exists)
- Keep **Required reviewers** enabled for `production`
- This prevents accidental prod deployments

## Terraform Workspaces

```bash
# View current workspace
cd infrastructure/terraform
terraform workspace list

# Switch between environments
terraform workspace select dev
terraform workspace select prod
```

## DynamoDB Table Design

Single-table pattern with `PK` + `SK`:

```
PK                  SK                           Data
──────────────────  ───────────────────────────  ─────────────────
USER#sivakumar      PROFILE                      {name, email, theme}
USER#sivakumar      SETTINGS                     {mode, params}
USER#sivakumar      TRADE#2026-02-25#uuid         {symbol, pnl}
USER#sivakumar      INSTRUMENT#XAU                {name, added_at}
USER#sivakumar      ALERT_RULE#uuid               {type, enabled}
```

## Cost: $0/month

Both environments stay within AWS Free Tier:
- Lambda: 1M requests/month shared
- DynamoDB: 25 GB + 25 RCU/WCU (always free)
- S3: 5 GB free
- API Gateway: 1M calls/month free
