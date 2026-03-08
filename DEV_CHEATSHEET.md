# Developer Cheatsheet — Market Analyser AI

A practical reference for day-to-day development on this project.
Covers Git, Python environment, local testing, AWS log extraction, and CI/CD pipeline interactions.

---

## Table of Contents
1. [Python Environment](#1-python-environment)
2. [Running the Backend Locally](#2-running-the-backend-locally)
3. [Running Tests](#3-running-tests)
4. [Git — Daily Workflow](#4-git--daily-workflow)
5. [Git — Inspection & History](#5-git--inspection--history)
6. [Git — Undoing Changes](#6-git--undoing-changes)
7. [Git — Branches & Merges](#7-git--branches--merges)
8. [AWS — Extracting Lambda Logs](#8-aws--extracting-lambda-logs)
9. [AWS — Direct Lambda Invocation](#9-aws--direct-lambda-invocation)
10. [AWS — S3 & DynamoDB Inspection](#10-aws--s3--dynamodb-inspection)
11. [CI/CD Pipeline](#11-cicd-pipeline)
12. [Useful One-Liners](#12-useful-one-liners)

---

## 1. Python Environment

The backend uses a virtual environment located at `backend/venv`.

```powershell
# Activate the virtual environment (Windows PowerShell)
.\backend\venv\Scripts\Activate.ps1

# Or just reference the venv Python directly (no activation needed)
.\backend\venv\Scripts\python.exe <script.py>

# Install a new package
.\backend\venv\Scripts\pip.exe install <package>

# List installed packages
.\backend\venv\Scripts\pip.exe list

# Freeze current packages to requirements.txt
.\backend\venv\Scripts\pip.exe freeze > backend\requirements.txt

# Check if a specific module imports correctly (quick smoke test)
.\backend\venv\Scripts\python.exe -c "from app.notifier import send_alerts; print('OK')"
```

> **Tip:** Always use the venv Python to run tests and scripts so you get the project's
> exact dependency versions, not whatever Python is installed system-wide.

---

## 2. Running the Backend Locally

```powershell
# Start FastAPI dev server (auto-reloads on file changes)
.\backend\venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
# (run from the backend/ directory)

# Or via python -m
.\backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API will be available at:
- `http://localhost:8000/api/analyze`  — full market analysis
- `http://localhost:8000/api/health`   — health check
- `http://localhost:8000/docs`         — interactive Swagger UI

```powershell
# Quick health check from another terminal
curl http://localhost:8000/api/health
```

---

## 3. Running Tests

All tests live in `backend/tests/`.

```powershell
# Run the full test suite
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v

# Run a single test file
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_signal_fixes_mar2026.py -v

# Run tests matching a keyword (substring of test name)
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -k "candle" -v

# Run tests and stop on first failure
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -x

# Run tests and show local variables on failure (very useful for debugging)
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v --tb=short

# Show coverage summary (requires pytest-cov)
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ --cov=app --cov-report=term-missing

# Run from the backend directory (so imports resolve correctly)
cd backend
..\backend\venv\Scripts\python.exe -m pytest tests/ -v
```

> **Pattern:** Always run imports first (`python -c "from app.X import Y"`), then run
> tests. If the import fails, the test file error is a syntax/import problem, not a
> logic problem.

---

## 4. Git — Daily Workflow

```powershell
# Check what branch you are on and what has changed
git status

# See unstaged diffs (what you changed but haven't staged yet)
git diff

# See staged diffs (what will go into the next commit)
git diff --staged

# Stage specific files
git add backend/app/notifier.py backend/app/main.py

# Stage ALL changed files (use carefully — review with git status first)
git add .

# Commit with a message
git commit -m "fix: short descriptive message"

# Push the current branch to GitHub
git push origin develop

# Pull latest changes from GitHub (fetch + merge)
git pull origin develop

# Pull with rebase (cleaner history — avoids extra merge commits)
git pull --rebase origin develop
```

### Commit Message Conventions

Use a short prefix so the history is scannable:

| Prefix | Meaning |
|--------|---------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `test:` | Adding or updating tests |
| `refactor:` | Code restructure, no behaviour change |
| `docs:` | Documentation only |
| `chore:` | Build/deploy/config changes |

Example:
```
feat: replace template geo narrative with contextual data-rich summary
fix: candle analyzer numpy bool cast bug (is_bullish identity check)
test: add 31 regression tests for signal-blocking bug fixes
```

---

## 5. Git — Inspection & History

```powershell
# Show recent commits (compact, one line each)
git log --oneline -20

# Show commits with changed file names
git log --oneline --name-status -10

# Show full diff for a specific commit
git show <commit-hash>

# Show only the files changed in a commit
git show --name-only <commit-hash>

# Search commit messages for a keyword
git log --oneline --grep="benchmark"

# Search for when a specific string was added/removed in code
git log -S "is_weekend_market_close" --oneline

# Show who last changed each line of a file (blame)
git blame backend/app/notifier.py

# Compare two branches
git diff develop..main --name-only

# Show the full diff between two branches
git diff develop..main

# Show commit graph across branches
git log --oneline --graph --all --decorate -20
```

---

## 6. Git — Undoing Changes

```powershell
# Discard ALL unstaged changes in a file (destructive — cannot undo)
git checkout -- backend/app/notifier.py

# Discard ALL unstaged changes in ALL files
git checkout -- .

# Unstage a file (moves it back to unstaged, keeps your edits)
git restore --staged backend/app/notifier.py

# Undo the last commit but KEEP the changes as unstaged edits
git reset --soft HEAD~1

# Undo the last commit and DISCARD the changes (destructive)
git reset --hard HEAD~1

# Create a new "undo" commit that reverses a past commit (safe — keeps history)
git revert <commit-hash>
# Example: revert the last commit
git revert HEAD

# Stash your current work-in-progress (save without committing)
git stash
# Get it back
git stash pop
# See what's stashed
git stash list

# Cherry-pick a single commit from another branch into current branch
git cherry-pick <commit-hash>
```

> **Rule of thumb:** If changes are already pushed to GitHub, prefer `git revert` over
> `git reset --hard`. Revert adds a new "undo" commit rather than rewriting history,
> which is safer when others may have pulled the code.

---

## 7. Git — Branches & Merges

```powershell
# List all local branches
git branch

# List all remote branches
git branch -r

# Create and switch to a new branch
git checkout -b feature/my-feature

# Switch to an existing branch
git checkout develop

# Merge a feature branch into develop
git checkout develop
git merge feature/my-feature

# Delete a local branch (after merging)
git branch -d feature/my-feature

# Delete a remote branch
git push origin --delete feature/my-feature

# Rebase your feature branch onto the latest develop
# (cleaner than merge — replays your commits on top of develop)
git checkout feature/my-feature
git rebase develop

# See which branches have been merged into develop
git branch --merged develop
```

---

## 8. AWS — Extracting Lambda Logs

The backend runs as an AWS Lambda function. Logs go to CloudWatch.

### Using AWS CLI

```powershell
# List all log groups (find the Lambda log group name)
aws logs describe-log-groups --query "logGroups[*].logGroupName" --output table

# List recent log streams for a Lambda function
aws logs describe-log-streams \
  --log-group-name "/aws/lambda/market-analyser-dev" \
  --order-by LastEventTime \
  --descending \
  --max-items 5

# Get the last N log events from a specific stream
aws logs get-log-events \
  --log-group-name "/aws/lambda/market-analyser-dev" \
  --log-stream-name "2026/03/08/[$LATEST]abc123" \
  --limit 100

# Filter logs for ERROR across the whole group (last 1 hour)
aws logs filter-log-events \
  --log-group-name "/aws/lambda/market-analyser-dev" \
  --filter-pattern "ERROR" \
  --start-time $(python -c "import time; print(int((time.time()-3600)*1000))")

# Filter for a specific symbol or keyword
aws logs filter-log-events \
  --log-group-name "/aws/lambda/market-analyser-dev" \
  --filter-pattern "WTI" \
  --start-time $(python -c "import time; print(int((time.time()-1800)*1000))")

# Tail logs in real-time (requires AWS CLI v2)
aws logs tail /aws/lambda/market-analyser-dev --follow
```

### Using AWS Console (Browser)

1. Open **CloudWatch → Log groups**
2. Find `/aws/lambda/<function-name>`
3. Click the latest log stream
4. Use **Filter events** box to search for `ERROR` or a symbol name like `WTI`

### Parsing timestamps
AWS CloudWatch timestamps are Unix milliseconds. Convert to human-readable:
```powershell
python -c "from datetime import datetime, timezone; print(datetime.fromtimestamp(1709856000/1000, tz=timezone.utc))"
```

---

## 9. AWS — Direct Lambda Invocation

Sometimes you want to trigger the Lambda directly (bypass API Gateway) to test it.

```powershell
# Invoke the Lambda synchronously and capture the output
aws lambda invoke \
  --function-name market-analyser-dev \
  --payload '{"httpMethod":"GET","path":"/api/health","queryStringParameters":{}}' \
  --cli-binary-format raw-in-base64-out \
  output.json
cat output.json

# Invoke with a specific user context
aws lambda invoke \
  --function-name market-analyser-dev \
  --payload '{"httpMethod":"GET","path":"/api/analyze","queryStringParameters":{"mode":"SHORT_TERM"}}' \
  --cli-binary-format raw-in-base64-out \
  output.json
```

---

## 10. AWS — S3 & DynamoDB Inspection

### S3 (config files, journal backups)

```powershell
# List all buckets
aws s3 ls

# List contents of the config bucket
aws s3 ls s3://<bucket-name>/

# List user-specific config files
aws s3 ls s3://<bucket-name>/users/

# Download a user's config file to inspect it
aws s3 cp s3://<bucket-name>/users/<user-id>/instruments.yaml ./local_instruments.yaml
cat local_instruments.yaml

# Upload a corrected config file
aws s3 cp ./local_instruments.yaml s3://<bucket-name>/users/<user-id>/instruments.yaml
```

### DynamoDB (analysis cache, trade journal, alert keys)

```powershell
# List all tables
aws dynamodb list-tables

# Describe a table (see schema, indexes)
aws dynamodb describe-table --table-name market-analyser-dev

# Scan up to 5 items from a table
aws dynamodb scan --table-name market-analyser-dev --max-items 5

# Get a specific item by primary key
aws dynamodb get-item \
  --table-name market-analyser-dev \
  --key '{"pk": {"S": "user#global_default"}, "sk": {"S": "analysis#SHORT_TERM"}}'

# Query items for a specific user
aws dynamodb query \
  --table-name market-analyser-dev \
  --key-condition-expression "pk = :uid" \
  --expression-attribute-values '{":uid": {"S": "user#global_default"}}'
```

---

## 11. CI/CD Pipeline

The project uses **GitHub Actions** for CI/CD. Pushing to the `develop` branch triggers the pipeline.

### Trigger a deployment
```powershell
# Push to develop → triggers GitHub Actions → deploys to DEV environment
git push origin develop

# Push to main → triggers GitHub Actions → deploys to PRODUCTION
git push origin main
```

### Monitor pipeline status

1. Go to `https://github.com/rnsivakumar76/market_analyser_ai/actions`
2. Click the latest workflow run
3. Expand steps to see build/deploy logs

### Workflow file location
```
.github/workflows/deploy.yml    # Main CI/CD pipeline definition
```

### Common pipeline steps (what happens on push)

```
1. Checkout code
2. Set up Python 3.x
3. Install backend dependencies (pip install -r requirements.txt)
4. Run tests (pytest)
5. Build Angular frontend (ng build --configuration production)
6. Package Lambda (zip backend code)
7. Deploy Lambda via AWS CLI or Terraform
8. Deploy frontend to S3 + invalidate CloudFront cache
```

### Force-rerun a failed pipeline
On GitHub Actions page: click the failed run → **Re-run all jobs**

---

## 12. Useful One-Liners

### Quick validation before pushing

```powershell
# 1. Check the module imports without errors
.\backend\venv\Scripts\python.exe -c "from app.main import app; print('main OK')"
.\backend\venv\Scripts\python.exe -c "from app.notifier import send_alerts; print('notifier OK')"
.\backend\venv\Scripts\python.exe -c "from app.analyzers.geo_risk_analyzer import analyze_geopolitical_risk; print('geo OK')"

# 2. Run just the regression tests for recent fixes
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_signal_fixes_mar2026.py -v

# 3. Check what files you are about to commit
git diff --staged --name-only

# 4. See the last 5 commits on the current branch
git log --oneline -5
```

### Searching the codebase

```powershell
# Find all files containing a string (recursive grep)
grep -r "is_weekend_market_close" backend/

# Find Python files containing a string
grep -r "send_expert_alert" backend/ --include="*.py"

# Find a file by name
find backend/ -name "notifier.py"

# Show all Python files modified in the last git commit
git show --name-only HEAD | grep "\.py$"
```

### AWS credential check

```powershell
# Confirm which AWS identity is active (which account / role)
aws sts get-caller-identity

# List Lambda functions in the account
aws lambda list-functions --query "Functions[*].FunctionName" --output table
```

### Environment variables (Lambda runtime)

The Lambda function reads these env vars at runtime:
```
TELEGRAM_BOT_TOKEN      Telegram bot token for alerts
TELEGRAM_CHAT_ID        Target chat/group ID for alerts
DYNAMODB_TABLE          DynamoDB table name
CONFIG_S3_BUCKET        S3 bucket for user configs
TWELVEDATA_API_KEY      Market data API key
ENVIRONMENT             'dev' or 'production'
```

You can check current Lambda env vars:
```powershell
aws lambda get-function-configuration \
  --function-name market-analyser-dev \
  --query "Environment.Variables"
```

---

## Quick Reference Card

| Action | Command |
|--------|---------|
| Activate venv | `.\backend\venv\Scripts\Activate.ps1` |
| Run all tests | `.\venv\Scripts\python.exe -m pytest tests/ -v` |
| Run one test file | `.\venv\Scripts\python.exe -m pytest tests/test_signal_fixes_mar2026.py -v` |
| Start dev server | `uvicorn app.main:app --reload` |
| Stage + commit | `git add <files> && git commit -m "prefix: message"` |
| Push to dev | `git push origin develop` |
| Undo last commit (keep edits) | `git reset --soft HEAD~1` |
| Safe revert pushed commit | `git revert HEAD` |
| Tail Lambda logs | `aws logs tail /aws/lambda/<fn> --follow` |
| Filter logs for errors | `aws logs filter-log-events --log-group-name ... --filter-pattern "ERROR"` |
| Check AWS identity | `aws sts get-caller-identity` |

---

*Last updated: Mar 2026 — Market Analyser AI project*
