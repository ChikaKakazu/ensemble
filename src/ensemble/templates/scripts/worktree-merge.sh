#!/bin/bash
# scripts/worktree-merge.sh
# Ensembleのworktreeをメインブランチにマージする

set -euo pipefail

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

# 使用方法
usage() {
    echo "Usage: $0 <worktree-path> [main-branch]"
    echo ""
    echo "Arguments:"
    echo "  worktree-path    マージするworktreeのパス"
    echo "  main-branch      マージ先ブランチ（デフォルト: main）"
    echo ""
    echo "Options:"
    echo "  --dry-run        実際にはマージせず、コンフリクトのみチェック"
    echo "  --auto-resolve   自動解決可能なコンフリクトを解決"
    echo ""
    echo "Example:"
    echo "  $0 ../ensemble-feature-auth"
    echo "  $0 ../ensemble-feature-auth main --dry-run"
    exit 1
}

# 引数チェック
if [ $# -lt 1 ]; then
    usage
fi

WORKTREE_PATH="$1"
MAIN_BRANCH="${2:-main}"
DRY_RUN=false
AUTO_RESOLVE=false

# オプション解析
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --auto-resolve)
            AUTO_RESOLVE=true
            shift
            ;;
    esac
done

# worktreeの存在確認
if [ ! -d "$WORKTREE_PATH" ]; then
    log_error "Worktree not found: ${WORKTREE_PATH}"
    exit 1
fi

# worktreeのブランチ名を取得
WORKTREE_PATH_ABS=$(cd "$WORKTREE_PATH" && pwd)
BRANCH_NAME=$(cd "$WORKTREE_PATH" && git rev-parse --abbrev-ref HEAD)

log_info "Merging worktree: ${WORKTREE_PATH_ABS}"
log_info "Branch: ${BRANCH_NAME}"
log_info "Target: ${MAIN_BRANCH}"

# メインリポジトリに移動
PROJECT_ROOT=$(git rev-parse --show-toplevel)
cd "$PROJECT_ROOT"

# メインブランチに切り替え
log_info "Switching to ${MAIN_BRANCH}..."
git checkout "$MAIN_BRANCH"

# 最新の変更をpull
log_info "Pulling latest changes..."
git pull --ff-only 2>/dev/null || log_warn "Could not fast-forward pull"

# dry-runモード
if [ "$DRY_RUN" = true ]; then
    log_info "Dry-run mode: checking for conflicts..."

    # マージを試行（コミットなし）
    if git merge --no-commit --no-ff "$BRANCH_NAME" 2>/dev/null; then
        log_info "No conflicts detected. Merge would succeed."
        git merge --abort 2>/dev/null || true
        exit 0
    else
        log_warn "Conflicts detected!"

        # コンフリクトファイル一覧
        echo ""
        echo "Conflicting files:"
        git diff --name-only --diff-filter=U
        echo ""

        git merge --abort 2>/dev/null || true
        exit 1
    fi
fi

# 実際のマージ
log_info "Merging ${BRANCH_NAME} into ${MAIN_BRANCH}..."

if git merge --no-ff "$BRANCH_NAME" -m "Merge ${BRANCH_NAME} into ${MAIN_BRANCH}"; then
    log_info "Merge successful!"

    # 統計情報
    echo ""
    echo "Merge statistics:"
    git diff --stat HEAD~1

    exit 0
else
    log_warn "Merge conflict detected!"

    # コンフリクトファイル一覧
    CONFLICT_FILES=$(git diff --name-only --diff-filter=U)
    echo ""
    echo "Conflicting files:"
    echo "$CONFLICT_FILES"
    echo ""

    if [ "$AUTO_RESOLVE" = true ]; then
        log_info "Attempting auto-resolve..."

        RESOLVED=0
        UNRESOLVED=0

        for file in $CONFLICT_FILES; do
            # 自動解決を試みる（両方の変更を保持）
            if git checkout --ours "$file" && git add "$file"; then
                log_info "Auto-resolved (ours): $file"
                ((RESOLVED++))
            else
                log_warn "Could not auto-resolve: $file"
                ((UNRESOLVED++))
            fi
        done

        if [ $UNRESOLVED -eq 0 ]; then
            git commit -m "Merge ${BRANCH_NAME} into ${MAIN_BRANCH} (auto-resolved)"
            log_info "All conflicts resolved!"
            exit 0
        else
            log_error "Some conflicts could not be resolved automatically."
            log_error "Please resolve manually and run: git commit"
            exit 1
        fi
    else
        # コンフリクト報告を生成
        REPORT_DIR="${PROJECT_ROOT}/queue/reports"
        mkdir -p "$REPORT_DIR"
        TIMESTAMP=$(date +%Y%m%d-%H%M%S)
        REPORT_FILE="${REPORT_DIR}/conflict-${TIMESTAMP}.yaml"

        cat > "$REPORT_FILE" << EOF
type: conflict
timestamp: $(date -Iseconds)
worktree: ${WORKTREE_PATH_ABS}
branch: ${BRANCH_NAME}
main_branch: ${MAIN_BRANCH}
conflict_files:
EOF

        for file in $CONFLICT_FILES; do
            cat >> "$REPORT_FILE" << EOF
  - file: ${file}
    status: unmerged
EOF
        done

        cat >> "$REPORT_FILE" << EOF

action_required: |
  Manual conflict resolution needed.
  Run: git status
  Resolve conflicts, then: git add . && git commit
EOF

        log_info "Conflict report saved to: ${REPORT_FILE}"
        log_error "Please resolve conflicts manually."
        exit 1
    fi
fi
