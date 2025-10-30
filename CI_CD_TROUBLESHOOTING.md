# CI/CD Troubleshooting Guide

This guide helps resolve common issues with GitHub Actions CI/CD pipeline for the LinkedIn Agent.

## Common CI/CD Issues and Solutions

### 1. Test Failures

#### Issue: `pytest: command not found`

**Cause:** pytest is not installed or not in PATH

**Solution:**
```yaml
# In .github/workflows/ci.yml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
```

**Verify locally:**
```bash
pip install pytest
pytest -v
```

#### Issue: `ModuleNotFoundError` during tests

**Cause:** Python path not configured correctly or missing `__init__.py` files

**Solution:**
- Ensure `tests/__init__.py` exists
- Add conftest.py with path configuration:

```python
# tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

**Verify locally:**
```bash
python -m pytest tests/ -v
```

#### Issue: Tests fail with missing environment variables

**Cause:** Required environment variables not set in test environment

**Solution:**
Add default test values in `tests/conftest.py`:

```python
import os
os.environ.setdefault("DRY_RUN", "true")
os.environ.setdefault("LINKEDIN_CLIENT_ID", "test_client_id")
os.environ.setdefault("GEMINI_API_KEY", "test_api_key")
```

### 2. Docker Build Failures

#### Issue: `ERROR [internal] load metadata for docker.io/library/python:3.11-slim`

**Cause:** Docker Hub rate limiting or network issues

**Solution:**
Add retry logic to workflow:

```yaml
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
  timeout-minutes: 30
```

**Local verification:**
```bash
docker build -t linkedinagent:test .
```

#### Issue: `COPY failed: file not found`

**Cause:** Files listed in Dockerfile don't exist or are in .dockerignore

**Solution:**
1. Check `.dockerignore` doesn't exclude required files
2. Verify all COPY commands reference existing files:

```dockerfile
# Dockerfile
COPY requirements.txt .
COPY . .
```

**Verify locally:**
```bash
docker build -t test-build .
```

#### Issue: `ERROR: failed to solve: failed to compute cache key`

**Cause:** Inconsistent file state or corrupted build cache

**Solution:**
```yaml
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    no-cache: true  # Add this to disable cache
    tags: ${{ steps.meta.outputs.tags }}
```

### 3. GitHub Container Registry (GHCR) Issues

#### Issue: `permission denied while trying to connect to the Docker daemon socket`

**Cause:** Insufficient permissions in workflow

**Solution:**
Ensure workflow has correct permissions:

```yaml
jobs:
  docker:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write  # Required for GHCR
```

#### Issue: `unauthorized: unauthenticated`

**Cause:** Authentication to GHCR failed

**Solution:**
Verify login step:

```yaml
- name: Login to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}  # Auto-provided by GitHub
```

#### Issue: `denied: installation not allowed to Write organization package`

**Cause:** Organization settings don't allow package writes

**Solution:**
1. Go to Organization Settings → Packages
2. Enable "Allow members to create and publish packages"
3. Or use personal repository instead of organization

### 4. Workflow Not Triggering

#### Issue: Workflow doesn't run on push

**Cause:** Wrong branch name or workflow disabled

**Solution:**
1. Check workflow triggers in `.github/workflows/ci.yml`:

```yaml
on:
  push:
    branches: [ main ]  # Ensure branch name matches
  pull_request:
    branches: [ main ]
```

2. Verify workflow is enabled:
   - Go to repository → Actions tab
   - Check if workflow is listed and enabled

#### Issue: Workflow runs but skips Docker job

**Cause:** Conditional not met

**Solution:**
Check job conditions:

```yaml
jobs:
  docker:
    needs: test
    if: github.ref == 'refs/heads/main'  # Only on main branch
```

### 5. Syntax and Compilation Errors

#### Issue: `python -m compileall` fails

**Cause:** Python syntax errors in code

**Solution:**
1. Run locally to identify file:
```bash
python -m compileall -q .
```

2. Fix syntax errors in reported files

3. Use linter to catch issues early:
```bash
pip install pylint
pylint src/
```

### 6. Dependency Installation Issues

#### Issue: `pip install` times out or fails

**Cause:** Network issues or package unavailable

**Solution:**
Add retry and timeout:

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt --timeout 100 --retries 3
```

#### Issue: Incompatible package versions

**Cause:** requirements.txt has conflicting versions

**Solution:**
1. Pin all versions in requirements.txt:
```
fastapi==0.104.1  # Not just fastapi
```

2. Test locally:
```bash
pip install -r requirements.txt
```

3. Update if needed:
```bash
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
```

## Debugging Workflows

### View Detailed Logs

1. Go to repository → Actions tab
2. Click on failed workflow run
3. Click on failed job
4. Expand each step to see logs

### Enable Debug Logging

Add repository secret:
1. Settings → Secrets → Actions
2. Add secret: `ACTIONS_STEP_DEBUG` = `true`
3. Re-run workflow to see detailed debug logs

### Download Logs

```bash
# Using GitHub CLI
gh run view <run-id> --log

# Or download from web UI
# Go to workflow run → click "..." → Download logs
```

## Local Testing Before Push

### Test Everything Locally

```bash
# 1. Syntax check
python -m compileall -q .

# 2. Run tests
pytest -v

# 3. Build Docker image
docker build -t linkedinagent:test .

# 4. Test Docker image
docker run --rm linkedinagent:test python -c "import src; print('OK')"

# 5. Test compose configuration
docker compose config

# 6. Full integration test
docker compose up -d
docker compose ps
docker compose logs
docker compose down
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Run tests before commit

echo "Running syntax check..."
python -m compileall -q . || exit 1

echo "Running tests..."
pytest -q || exit 1

echo "All checks passed!"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Monitoring CI/CD Health

### Set up Status Badges

Add to README.md:

```markdown
[![CI](https://github.com/DevKursat/linkedinAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/DevKursat/linkedinAgent/actions/workflows/ci.yml)
```

### Email Notifications

GitHub automatically sends emails for:
- Failed workflow runs
- Broken builds on main branch

Configure in: Settings → Notifications

## Best Practices

1. **Always test locally before pushing**
   ```bash
   ./scripts/run_ci_locally.sh  # If you create this script
   ```

2. **Use meaningful commit messages**
   ```bash
   git commit -m "fix: resolve pytest configuration issue"
   ```

3. **Pin action versions for stability**
   ```yaml
   uses: actions/checkout@v4  # Not @latest
   ```

4. **Keep workflows fast**
   - Use caching for dependencies
   - Parallelize independent jobs
   - Only build Docker on main branch

5. **Monitor workflow runs**
   - Check Actions tab regularly
   - Fix issues promptly
   - Review failed runs

## Getting Help

If issues persist:

1. **Check GitHub Status:** https://www.githubstatus.com/
2. **Review GitHub Actions docs:** https://docs.github.com/actions
3. **Open an issue:** Include:
   - Workflow run URL
   - Full error message
   - Steps to reproduce
   - Local test results

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Test fails | `pytest -v` locally first |
| Docker build fails | `docker build .` locally |
| Permission denied | Check `permissions:` in workflow |
| Workflow not running | Check branch name in `on:` |
| Module not found | Add `__init__.py` files |
| Env var missing | Set in `conftest.py` |
| Syntax error | Run `python -m compileall -q .` |
| Timeout | Increase `timeout-minutes:` |

## Example: Full Working CI Workflow

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Cache pip packages
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Syntax check
        run: python -m compileall -q .
        
      - name: Run tests
        run: pytest -v

  docker:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

This includes all best practices and should work reliably.
