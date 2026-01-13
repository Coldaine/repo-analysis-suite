---
doc_type: guide
subsystem: tools
version: 1.0.0
status: active
owners: pmacl
last_reviewed: 2025-12-27
---

# Graphite CLI Guide

Graphite (`gt`) is a CLI tool for managing stacked pull requests on GitHub. This guide covers installation, core workflow, and troubleshooting.

## What is Stacking?

Traditional PR workflow:
```
main ← Feature PR (500 lines, hard to review)
```

Stacked PR workflow:
```
main ← PR1: Add API (100 lines)
     ← PR2: Update frontend (150 lines)
     ← PR3: Add tests (100 lines)
     ← PR4: Update docs (50 lines)
```

Each PR is small, focused, and reviewable. PRs merge in order, automatically rebasing the stack.

---

## Installation

```bash
# Install via npm
npm install -g @withgraphite/graphite-cli

# Or via Homebrew (macOS)
brew install withgraphite/tap/graphite

# Verify installation
gt --version
```

### Authentication

```bash
# Get auth token from: https://app.graphite.com/settings/cli
gt auth --token <your-token>
```

### Initialize Repository

```bash
cd your-repo
gt init
```

---

## Core Concepts

| Term | Definition |
|------|------------|
| **Stack** | A sequence of PRs, each building on its parent |
| **Trunk** | The base branch stacks merge into (usually `main`) |
| **Downstack** | PRs below the current one (ancestors) |
| **Upstack** | PRs above the current one (descendants) |

---

## Core Workflow

### 1. Create Your First Branch

```bash
# Start from trunk
gt checkout main

# Make changes...
vim src/api.py

# Create branch with changes
gt create -m "feat: add user API endpoint"
```

The `gt create` command:
- Creates a new branch
- Stages all changes
- Commits with your message
- Tracks the branch in Graphite's stack

### 2. Stack Another PR

```bash
# Make more changes (still on previous branch)
vim src/frontend.js

# Stack a new branch on top
gt create -m "feat: add user frontend component"
```

### 3. Submit the Stack

```bash
# Submit current branch and all downstack branches
gt submit

# Or submit the entire stack (including upstack)
gt submit --stack
# Shorthand: gt ss
```

Options:
- `--draft`: Create PRs as drafts
- `--no-edit`: Skip interactive prompts
- `--ai`: Auto-generate PR titles/descriptions
- `--dry-run`: Preview without creating PRs

### 4. View Your Stack

```bash
gt log
```

Example output:
```
◉ feat/add-docs (current)
│ PR #45 - Add documentation
│
◉ feat/add-tests
│ PR #44 - Add test coverage
│
◉ feat/add-frontend
│ PR #43 - Add frontend component
│
◉ feat/add-api
│ PR #42 - Add user API
│
◉ main
```

### 5. Navigate the Stack

```bash
gt up       # Move to branch above
gt down     # Move to branch below
gt checkout # Interactive branch selector
gt top      # Go to top of stack
gt bottom   # Go to bottom of stack
```

### 6. Respond to Feedback

When reviewer requests changes on any PR in the stack:

```bash
# Checkout the branch that needs changes
gt checkout feat/add-api

# Make your changes
vim src/api.py

# Amend the branch and rebase upstack
gt modify -m "fix: address review feedback"
```

`gt modify` automatically rebases all branches above the current one.

### 7. Sync with Trunk

When `main` has new commits:

```bash
gt sync
```

This:
- Pulls latest trunk
- Rebases all stacks on trunk
- Prompts to delete merged/stale branches

### 8. Merge the Stack

After all PRs are approved:

```bash
# Merge from bottom of stack upward
gt merge
```

Or merge via GitHub's UI - Graphite auto-updates the stack.

---

## Advanced Commands

### Modify Stack Structure

```bash
# Combine current branch into parent
gt fold

# Split current branch into multiple
gt split

# Move branch to different parent
gt rebase --onto <target>

# Absorb uncommitted changes into appropriate commits
gt absorb
```

### Handle Conflicts

```bash
# If rebase has conflicts
# 1. Resolve conflicts in files
# 2. Stage resolved files
git add <resolved-files>
# 3. Continue
gt continue

# Or abort
gt abort
```

### Undo Operations

```bash
# Undo last Graphite operation
gt undo
```

### Track Existing Branches

```bash
# Add existing branch to Graphite tracking
gt track

# Or track with explicit parent
gt track --parent feat/add-api
```

---

## Common Workflows

### Quick Stack Creation

```bash
# From main, create a 3-PR stack
gt checkout main
echo "api code" > api.py && gt create -m "feat: add API"
echo "frontend" > app.js && gt create -m "feat: add frontend"
echo "tests" > test.py && gt create -m "test: add tests"

# Submit all at once
gt ss  # short for: gt submit --stack
```

### Handling Review Feedback Mid-Stack

```bash
# Reviewer comments on PR #2 of 4
gt checkout feat/add-frontend

# Make changes
vim app.js

# Amend and auto-rebase PRs 3 and 4
gt modify -m "fix: address frontend feedback"

# Re-push affected PRs
gt submit --stack
```

### Rebasing on Updated Main

```bash
# Main was updated by other PRs
gt sync

# If conflicts occur:
# 1. Resolve conflicts
# 2. gt continue
# 3. Repeat for each branch in stack

# Re-push updated stack
gt ss
```

---

## Troubleshooting

### "Branch not tracked by Graphite"

```bash
# Track the branch
gt track

# Or track with specific parent
gt track --parent main
```

### "Stack out of sync"

```bash
# Force restack all branches
gt restack

# If that fails, sync from trunk
gt sync --force
```

### "Merge conflicts during restack"

```bash
# Resolve conflicts manually
git add <resolved-files>
gt continue

# Or skip this branch (not recommended)
gt continue --skip

# Or abort entirely
gt abort
```

### "PR base branch is wrong"

```bash
# Graphite usually fixes this automatically
# If not, edit in GitHub UI or:
gt submit  # Re-submits with correct base
```

### "gt command not found"

```bash
# Check npm global bin is in PATH
npm bin -g
# Add to PATH in ~/.bashrc or ~/.zshrc
export PATH="$(npm bin -g):$PATH"
```

### "Not authenticated"

```bash
# Re-authenticate
gt auth --token <token>
# Get token from: https://app.graphite.com/settings/cli
```

---

## Configuration

```bash
# Open interactive config menu
gt config

# Common settings:
# - Default PR draft mode
# - Auto-submit behavior
# - Editor preferences
```

Config file: `~/.config/graphite/user_config`

---

## Integration with AgentReview

The Stacked PR Agent can use Graphite when available:

```python
# Agent detects Graphite CLI
if shutil.which("gt"):
    # Use gt create/submit for stack management
    await graphite_create_stack(plan)
else:
    # Fall back to manual git/gh commands
    await manual_create_stack(plan)
```

Benefits of Graphite integration:
- Automatic stack tracking
- Simplified rebasing
- AI-generated PR descriptions
- Better merge conflict handling

---

## Resources

- **Documentation**: https://graphite.dev/docs
- **Cheatsheet**: https://graphite.dev/docs/cheatsheet
- **Tutorial Videos**: https://youtube.com/@withgraphite
- **Community Slack**: https://community.graphite.dev
- **Troubleshooting**: https://graphite.dev/docs/troubleshooting
