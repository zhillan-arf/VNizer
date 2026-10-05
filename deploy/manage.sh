#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'EOF'
Usage: ./deploy/manage.sh COMMAND

  start     Build and start the web and worker services.
  stop      Stop all VNizer services. Keep application data.
  restart   Build and replace the web and worker containers.
  status    Show container status.
  logs      Show the last 200 log lines and wait for new lines.
  help      Show these instructions.
EOF
}

if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi
case "$1" in
    help|-h|--help) usage; exit 0 ;;
    start|stop|restart|status|logs) ;;
    *) usage >&2; exit 2 ;;
esac

cd -- "$DEPLOY_DIR"
command -v docker >/dev/null 2>&1 || { echo 'Install Docker and Docker Compose v2.' >&2; exit 1; }
DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
    command -v sudo >/dev/null 2>&1 || { echo 'Docker access failed. Check Docker and your permissions.' >&2; exit 1; }
    PRESERVE_ENV='COMPOSE_PROFILES,COMPOSE_PROJECT_NAME,VNIZER_BIND_ADDRESS,VNIZER_ENV_FILE'
    PRESERVE_ENV+=',VNIZER_LANGUAGE,VNIZER_MODEL_ROOT,VNIZER_PORT,VNIZER_SPEAKER'
    PRESERVE_ENV+=',VNIZER_TTS_API_KEY,VNIZER_TTS_PORT,VNIZER_TTS_TYPE,VNIZER_TTS_URL'
    DOCKER=(sudo "--preserve-env=$PRESERVE_ENV" docker)
fi
"${DOCKER[@]}" compose version >/dev/null

compose() {
    "${DOCKER[@]}" compose --project-directory "$DEPLOY_DIR" -f "$DEPLOY_DIR/compose.yaml" "$@"
}

case "$1" in
    start|restart)
        options=(up -d --build --wait --wait-timeout 120)
        if [[ "$1" == restart ]]; then options+=(--force-recreate); fi
        compose "${options[@]}" web worker
        compose ps
        ;;
    stop) compose down ;;
    status) compose ps ;;
    logs) compose logs --follow --tail 200 ;;
esac
