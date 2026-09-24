#!/usr/bin/env bash
# Build, push and roll out Hockey Decoded to ECS. See Deploy.md for the long version.
#
#   ./deploy.sh          deploy the committed state of main
#   ./deploy.sh logs     tail the live CloudWatch logs
#
# Set FORCE=1 to deploy from another branch or with uncommitted changes.
set -euo pipefail

REGION="us-east-1"
REGISTRY="113087453968.dkr.ecr.us-east-1.amazonaws.com"
REPO="$REGISTRY/hockey-decoded"
CLUSTER="hockey-decoded-cluster"
SERVICE="hockey-decoded-service-alb"
LOG_GROUP="/ecs/hockey-decoded"
HEALTH_URL="https://www.hockeydecoded.com/health"

export AWS_PAGER=""           # stops the AWS CLI opening output in `less` (the "press q" step)
cd "$(dirname "$0")"

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die()  { printf '\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

if [[ "${1:-}" == "logs" ]]; then
  exec aws logs tail "$LOG_GROUP" --follow --region "$REGION"
fi

step "Pre-flight checks"
docker info >/dev/null 2>&1 || die "Docker isn't running. Start Docker Desktop and try again."
aws sts get-caller-identity >/dev/null 2>&1 || die "AWS credentials aren't working (aws sts get-caller-identity failed)."

BRANCH=$(git rev-parse --abbrev-ref HEAD)
SHA=$(git rev-parse --short HEAD)
if [[ "${FORCE:-0}" != "1" ]]; then
  [[ "$BRANCH" == "main" ]] || die "You're on '$BRANCH', not main. Merge first, or run FORCE=1 ./deploy.sh"
  [[ -z "$(git status --porcelain --untracked-files=no)" ]] || die "Uncommitted changes (git status). Commit them first, or run FORCE=1 ./deploy.sh"
fi
git fetch -q origin main 2>/dev/null || true
if [[ -n "$(git log origin/main..HEAD --oneline 2>/dev/null)" ]]; then
  echo "Note: main has commits that aren't on GitHub yet. Run 'git push origin main' when you get a chance."
fi
echo "Deploying $BRANCH @ $SHA"

step "Logging in to ECR"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null

step "Building for linux/amd64 and pushing (tags: latest, $SHA)"
docker buildx build --platform linux/amd64 -t "$REPO:latest" -t "$REPO:$SHA" --push .

step "Rolling out on ECS"
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" \
  --force-new-deployment --region "$REGION" >/dev/null
echo "Waiting for the new task to go healthy (usually 2-5 minutes)..."
if ! aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION"; then
  die "Rollout didn't settle. Check the logs with: ./deploy.sh logs"
fi

STATE=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --region "$REGION" \
  --query 'services[0].deployments[0].rolloutState' --output text)
[[ "$STATE" == "COMPLETED" ]] || die "Rollout state is $STATE. Check the logs with: ./deploy.sh logs"

step "Checking the live site"
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$HEALTH_URL" || true)
[[ "$CODE" == "200" ]] || die "$HEALTH_URL returned $CODE. Check the logs with: ./deploy.sh logs"

printf '\n\033[32mDeployed %s to https://www.hockeydecoded.com\033[0m\n' "$SHA"
