#!/usr/bin/env bash

# commit-to-git
# -------------
# This script commits the current project to Git and pushes to GitHub,
# with optional cloud deploy. Self-contained; no external skeleton needed.
#
# It is intended to be run from the project root. Cursor should invoke it
# via the corresponding command definition in `cursor/commands/commit-to-git.json`.
#
# NOTE: This is a starting point / scaffold. You will likely want to:
# - Make it executable: chmod +x cursor/scripts/commit-to-git.sh
# - Adapt detection of cloud targets to your environment

set -euo pipefail

main() {
  echo "[commit-to-git] Starting..."

  phase_repo_setup
  local branch
  branch="$(phase_branch_and_commit)"
  phase_summary "$branch"
  phase_post_action_cloud "$branch"

  echo "[commit-to-git] Done."
}

phase_repo_setup() {
  echo "[phase 1] Repository setup"

  # Detect git repository
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "  - Detected existing git repository."
  else
    echo "  - No git repository detected. Initializing..."
    git init
  fi

  # Ensure GitHub CLI is available
  if ! command -v gh >/dev/null 2>&1; then
    echo "  - GitHub CLI ('gh') is not installed."
    if command -v brew >/dev/null 2>&1; then
      if [ -t 0 ]; then
      read -r -p "  > Install GitHub CLI using 'brew install gh'? [Y/n]: " install_gh
      install_gh="${install_gh:-Y}"
      if [[ "$install_gh" =~ ^[Yy]$ ]]; then
        echo "  - Installing GitHub CLI via Homebrew..."
        if ! brew install gh; then
          echo "  - Failed to install GitHub CLI via Homebrew. Please install it manually and rerun."
          exit 1
        fi
      else
        echo "  - GitHub CLI is required but will not be installed. Aborting."
          exit 1
        fi
      else
        echo "  - GitHub CLI is required but cannot be installed automatically in non-interactive mode."
        echo "  - Please install it manually (e.g., 'brew install gh' or from https://cli.github.com/) and rerun."
        exit 1
      fi
    else
      echo "  - Homebrew not found. Please install GitHub CLI manually (e.g., from https://cli.github.com/) and rerun."
      exit 1
    fi
  fi

  # Ensure GitHub auth
  if ! gh auth status >/dev/null 2>&1; then
    echo "  - You are not logged in to GitHub CLI."
    if [ -t 0 ]; then
    read -r -p "  > Run 'gh auth login' now? [Y/n]: " gh_login
    gh_login="${gh_login:-Y}"
    if [[ "$gh_login" =~ ^[Yy]$ ]]; then
      gh auth login || {
        echo "  - 'gh auth login' failed. Please fix authentication and rerun."
        exit 1
      }
      if ! gh auth status >/dev/null 2>&1; then
        echo "  - GitHub authentication still not configured correctly. Aborting."
        exit 1
      fi
    else
      echo "  - GitHub CLI is not authenticated. Aborting."
        exit 1
      fi
    else
      echo "  - GitHub CLI is not authenticated and this script is running non-interactively."
      echo "  - Please run 'gh auth login' manually and rerun this command."
      exit 1
    fi
  fi

  # Ensure GitHub remote exists, auto-create private repo if needed
  if git remote get-url origin >/dev/null 2>&1; then
    echo "  - Found existing 'origin' remote."
  else
    echo "  - No 'origin' remote found. Creating private GitHub repository via 'gh repo create'..."
    local repo_name
    repo_name="$(basename "$(pwd)")"
    if [ -t 0 ]; then
    read -r -p "  > GitHub repo name [${repo_name}]: " input_name
    repo_name="${input_name:-$repo_name}"
    else
      echo "  > GitHub repo name [${repo_name}]: (non-interactive, using default)"
    fi

    # Create the repo as private from current directory and set origin.
    # If there are existing commits, also push the current state.
    if git rev-parse HEAD >/dev/null 2>&1; then
    if gh repo create "$repo_name" --private --source . --remote origin --push; then
        echo "  - Created GitHub repo '$repo_name', set 'origin', and pushed initial commit(s)."
      else
        echo "  - Failed to create GitHub repo via 'gh repo create'. Please check the error above."
        exit 1
      fi
    else
      if gh repo create "$repo_name" --private --source . --remote origin; then
        echo "  - Created GitHub repo '$repo_name' and set 'origin' (no commits to push yet)."
    else
      echo "  - Failed to create GitHub repo via 'gh repo create'. Please check the error above."
      exit 1
      fi
    fi
  fi
}

phase_branch_and_commit() {
  echo "[phase 2] Branch selection & commit"

  # List branches and detect current
  echo "  - Local branches:"
  git branch || echo "    (no branches yet)"

  # Ensure at least one branch exists
  if ! git rev-parse --abbrev-ref HEAD >/dev/null 2>&1; then
    echo "  - No current branch. Creating 'main'..."
    git checkout -b main
  fi

  local current_branch
  current_branch="$(git rev-parse --abbrev-ref HEAD)"
  echo "  - Current branch: ${current_branch}"

  # Simple prompt for branch (default = current)
  local target_branch
  if [ -t 0 ]; then
    read -r -p "  > Branch to commit to [${current_branch}]: " target_branch_input
    target_branch="${target_branch_input:-$current_branch}"
  else
    echo "  > Branch to commit to [${current_branch}]: (non-interactive, using default)"
    target_branch="$current_branch"
  fi

  if ! git show-ref --verify --quiet "refs/heads/${target_branch}"; then
    echo "  - Branch '${target_branch}' does not exist. Creating..."
    git checkout -b "$target_branch"
  else
    git checkout "$target_branch"
  fi

  echo "  - Staging changes..."
  git status --short
  if [ -t 0 ]; then
  read -r -p "  > Proceed with 'git add .' and commit all shown changes? [y/N]: " confirm
  if [[ "${confirm:-N}" != [yY] ]]; then
    echo "  - Aborted by user."
    exit 1
    fi
  else
    echo "  > Proceed with 'git add .' and commit all shown changes? [y/N]: y (non-interactive default)"
  fi

  git add .

  local commit_msg
  if [ -t 0 ]; then
    read -r -p "  > Commit message: " commit_msg_input
    commit_msg="${commit_msg_input:-update}"
  else
    echo "  > Commit message: update (non-interactive default)"
    commit_msg="update"
  fi

  if git diff --cached --quiet; then
    echo "  - No staged changes to commit."
  else
    git commit -m "$commit_msg"
  fi

  echo "  - Pushing to origin/${target_branch}..."
  git push -u origin "$target_branch"

  echo "$target_branch"
}

phase_summary() {
  local branch="$1"
  echo "[phase 3] Summary"

  local repo_url=""
  if git remote get-url origin >/dev/null 2>&1; then
    repo_url="$(git remote get-url origin)"
  fi

  local commit_hash commit_msg
  commit_hash="$(git rev-parse HEAD 2>/dev/null || echo "N/A")"
  commit_msg="$(git log -1 --pretty=%B 2>/dev/null || echo "N/A")"

  echo "  - Repository:"
  echo "      origin: ${repo_url:-<none>}"
  echo "  - Branch & commit:"
  echo "      branch: ${branch}"
  echo "      commit: ${commit_hash}"
  echo "      message: ${commit_msg}"

  echo "  - Next actions (suggested):"
  echo "      - Open the GitHub repo (if configured) and review the commit."
}

phase_post_action_cloud() {
  local branch="$1"
  echo "[phase 4] Post action – optional cloud deployment"

  # Placeholder detection for cloud target.
  # You can customize this to read from a config file or environment.
  local cloud_host="${CLOUD_DEPLOY_HOST:-}"
  local cloud_user="${CLOUD_DEPLOY_USER:-ubuntu}"
  local cloud_path="${CLOUD_DEPLOY_PATH:-/var/www/app}"

  if [[ -z "$cloud_host" ]]; then
    echo "  - No cloud deployment target configured (CLOUD_DEPLOY_HOST unset). Skipping."
    return 0
  fi

  echo "  - Detected deployment target: ${cloud_user}@${cloud_host}:${cloud_path}"
  read -r -p "  > Deploy latest '${branch}' to this cloud instance? [y/N]: " deploy
  if [ -t 0 ]; then
  if [[ "${deploy:-N}" != [yY] ]]; then
    echo "  - Skipping cloud deployment."
      return 0
    fi
  else
    echo "  > Deploy latest '${branch}' to this cloud instance? [y/N]: n (non-interactive default)"
    echo "  - Skipping cloud deployment (non-interactive mode)."
    return 0
  fi

  echo "  - Connecting via SSH and updating remote code..."
  ssh "${cloud_user}@${cloud_host}" bash -s <<EOF
set -euo pipefail
cd "${cloud_path}"
if command -v git >/dev/null 2>&1 && [ -d .git ]; then
  echo "[remote] Using git pull..."
  git pull origin "${branch}"
else
  echo "[remote] No git repo detected at ${cloud_path}."
  echo "[remote] TODO: add rsync/scp-based deployment here."
fi

if [ -f Dockerfile ] || [ -f docker-compose.yml ]; then
  echo "[remote] Docker configuration detected."
  # TODO: customize Docker rebuild/restart commands as needed.
  echo "[remote] (placeholder) Rebuild and restart Docker containers..."
fi
EOF

  echo "  - Cloud deployment step completed (see remote logs for details)."
}

main "$@"

