#!/usr/bin/env bash
# RAPR AI: set it up on this server, no laptop needed.
#
#   curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-server.sh | bash
#
# Installs Docker if it's missing, asks for a PIN, starts RAPR and a free
# Cloudflare quick tunnel, and prints the address to open from any browser.
# Run it again to update RAPR (your PIN and settings are kept).
# Afterwards, the "rapr" command shows the address, logs, and updates or removes it.
#
# Works on Ubuntu, Debian and similar Linux servers (Oracle's free server too).
# Same setup as the app's Settings -> Cloud server; the files come from the
# RAPR image itself (helm/cloud/server_files.py).

set -euo pipefail

IMAGE="ghcr.io/rawalrahul/raprai:latest"
NAME="${RAPR_NAME:-rapr}"
DIR="/opt/rapr/$NAME"

say()  { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ✓\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m ✗ %s\033[0m\n' "$*" >&2; exit 1; }

main() {
  [ "$(uname -s)" = "Linux" ] || fail "This server isn't Linux. RAPR's server setup supports Ubuntu, Debian and similar."
  [[ "$NAME" =~ ^[a-z0-9-]{1,30}$ ]] || fail "RAPR_NAME: use lowercase letters, digits and dashes."

  if [ "$(id -u)" = 0 ]; then SUDO=""; else
    command -v sudo >/dev/null || fail "Run this as root, or install sudo."
    SUDO="sudo"
    say "Some steps need administrator rights; sudo may ask for your password."
    $SUDO true || fail "sudo didn't work for this user."
  fi

  local mem_mb free_gb
  mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
  if [ "${mem_mb:-0}" -lt 900 ]; then
    fail "The server has ${mem_mb} MB of memory. RAPR needs about 1 GB (Oracle's free server: pick the bigger Ampere shape, or add swap)."
  fi
  free_gb=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
  if [ "${free_gb:-0}" -lt 4 ]; then
    fail "Only ${free_gb} GB free. RAPR and its AI tools need about 4 GB."
  fi
  ok "System: Linux, ${mem_mb} MB memory, ${free_gb} GB free"

  if ! command -v docker >/dev/null; then
    say "Installing Docker (a few minutes)..."
    curl -fsSL https://get.docker.com | $SUDO sh >/dev/null
  fi
  $SUDO docker compose version >/dev/null 2>&1 || fail "Docker Compose is missing. Install the docker-compose-plugin package and run this again."
  ok "Docker is ready"

  local compose="$SUDO docker compose --project-directory $DIR -f $DIR/docker-compose.yml"

  if $SUDO test -f "$DIR/rapr.env"; then
    say "RAPR is already set up here. Updating it (your PIN and settings are kept)..."
    $compose pull -q
  else
    local pin pin2
    say "Choose a PIN. You'll type it to open RAPR (at least 4 characters)."
    while true; do
      read -r -s -p "    PIN: " pin </dev/tty; echo
      read -r -s -p "    PIN again: " pin2 </dev/tty; echo
      if [ "$pin" != "$pin2" ]; then echo "    The PINs don't match, try again."
      elif [ "${#pin}" -lt 4 ]; then echo "    Use at least 4 characters."
      else break; fi
    done
    say "Downloading RAPR (the first time takes a few minutes)..."
    $SUDO docker pull -q "$IMAGE" >/dev/null
    $SUDO mkdir -p "$DIR"
    $SUDO chmod 700 "$DIR"
    # The PIN goes in on stdin, never on a command line; only its hash is saved.
    printf '%s\n' "$pin" | $SUDO docker run --rm -i --user 0 -v "$DIR:/out" "$IMAGE" \
      python -m helm.cloud.server_files "$NAME" || fail "Couldn't write RAPR's settings."
    unset pin pin2
    ok "Settings written (your PIN is stored as a hash only)"
  fi

  $compose up -d --pull missing >/dev/null 2>&1 || { $compose up -d; fail "RAPR didn't start (see above)."; }
  say "Waiting for RAPR to start..."
  local i healthy=""
  for i in $(seq 1 30); do
    if $compose exec -T rapr python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" >/dev/null 2>&1; then
      healthy=1; break
    fi
    sleep 5
  done
  [ -n "$healthy" ] || fail "RAPR didn't answer its health check. See why with: rapr logs"
  ok "RAPR is running"

  install_helper
  say "Getting your address..."
  local url=""
  for i in $(seq 1 12); do
    url=$(rapr url 2>/dev/null || true)
    [ -n "$url" ] && break
    sleep 5
  done

  echo
  if [ -n "$url" ]; then
    printf '\033[1;32mRAPR AI is ready:\033[0m %s\n' "$url"
    echo "Open it on any phone or computer and enter your PIN."
  else
    echo "RAPR is running, but its address isn't ready yet. Run 'rapr url' in a minute."
  fi
  echo "The address changes when the server restarts; 'rapr url' always shows the current one."
  echo "Other commands: rapr status | rapr logs | rapr update | rapr restart | rapr remove"
}

install_helper() {
  $SUDO tee /usr/local/bin/rapr >/dev/null <<EOF
#!/usr/bin/env bash
# RAPR AI server helper (written by install-server.sh).
set -e
DIR="$DIR"
S=""; [ "\$(id -u)" = 0 ] || S="sudo"
C="\$S docker compose --project-directory \$DIR -f \$DIR/docker-compose.yml"
case "\${1:-}" in
  url)     \$C logs tunnel --no-color 2>&1 | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | grep -v '^https://api\.' | tail -1 ;;
  status)  \$C ps ;;
  logs)    \$C logs rapr --tail 120 --no-color ;;
  update)  \$C pull && \$C up -d && echo "Updated. New address (if it changed): run 'rapr url' in a minute." ;;
  restart) \$C restart && echo "Restarted. Run 'rapr url' in a minute for the address." ;;
  remove)
    read -r -p "Remove RAPR and all its data from this server? Type yes: " a </dev/tty
    [ "\$a" = yes ] || { echo "Nothing removed."; exit 0; }
    \$C down -v && \$S rm -rf "\$DIR" && \$S rm -f /usr/local/bin/rapr && echo "RAPR removed." ;;
  *) echo "Usage: rapr url | status | logs | update | restart | remove" ;;
esac
EOF
  $SUDO chmod 755 /usr/local/bin/rapr
}

main "$@"
