#!/bin/bash
# scripts/worktree-create.sh
# Ensembleの並列開発用worktreeを作成する

set -euo pipefail

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ログ関数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 使用方法
usage() {
    echo "Usage: $0 <branch-name> [base-branch]"
    echo ""
    echo "Arguments:"
    echo "  branch-name    作成するブランチ名（ensemble/接頭辞が自動付与）"
    echo "  base-branch    ベースとなるブランチ（デフォルト: main）"
    echo ""
    echo "Example:"
    echo "  $0 feature-auth main"
    echo "  → ../ensemble-feature-auth にworktreeが作成される"
    echo "  → ブランチ名: ensemble/feature-auth"
    exit 1
}

# 引数チェック
if [ $# -lt 1 ]; then
    usage
fi

BRANCH_NAME="$1"
BASE_BRANCH="${2:-main}"

# ensemble/ プレフィックスを付与（まだない場合）
if [[ ! "$BRANCH_NAME" =~ ^ensemble/ ]]; then
    FULL_BRANCH_NAME="ensemble/${BRANCH_NAME}"
else
    FULL_BRANCH_NAME="$BRANCH_NAME"
    BRANCH_NAME="${BRANCH_NAME#ensemble/}"
fi

# worktreeディレクトリ名
PROJECT_ROOT=$(git rev-parse --show-toplevel)
PARENT_DIR=$(dirname "$PROJECT_ROOT")
WORKTREE_DIR="${PARENT_DIR}/ensemble-${BRANCH_NAME}"

log_info "Creating worktree for: ${FULL_BRANCH_NAME}"
log_info "Base branch: ${BASE_BRANCH}"
log_info "Worktree directory: ${WORKTREE_DIR}"

# 既存チェック
if [ -d "$WORKTREE_DIR" ]; then
    log_error "Worktree directory already exists: ${WORKTREE_DIR}"
    exit 1
fi

# ベースブランチが存在するか確認
if ! git rev-parse --verify "$BASE_BRANCH" >/dev/null 2>&1; then
    log_error "Base branch does not exist: ${BASE_BRANCH}"
    exit 1
fi

# ブランチが既に存在するか確認
if git rev-parse --verify "$FULL_BRANCH_NAME" >/dev/null 2>&1; then
    log_warn "Branch already exists: ${FULL_BRANCH_NAME}"
    log_info "Creating worktree with existing branch..."
    git worktree add "$WORKTREE_DIR" "$FULL_BRANCH_NAME"
else
    log_info "Creating new branch and worktree..."
    git worktree add -b "$FULL_BRANCH_NAME" "$WORKTREE_DIR" "$BASE_BRANCH"
fi

# 成功メッセージ
log_info "Worktree created successfully!"
echo ""
echo "Next steps:"
echo "  1. cd ${WORKTREE_DIR}"
echo "  2. Start Claude Code in this directory"
echo ""
echo "To remove this worktree later:"
echo "  git worktree remove ${WORKTREE_DIR}"
echo "  git branch -d ${FULL_BRANCH_NAME}"
