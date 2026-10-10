#!/usr/bin/env bash
# RAPR AI on a Mac, natively: one command.
#
#   curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-mac.sh | bash
#
# Installs what's missing with Homebrew (Python 3.12, Node.js, git, ffmpeg),
# sets RAPR up in ~/.rapr-ai, and adds "RAPR AI" to your Applications folder.
# Open that app to start RAPR (it opens in your browser); quit it to stop RAPR.
# RAPR runs on your Mac itself, so it works with your project folders and the
# AI tools you already have (Claude Code, Codex, Gemini CLI, Ollama...).
# Run the command again to update. Your data stays in
# ~/Library/Application Support/RAPR AI.
#
# The "rapr" command: rapr start | stop | open | status | logs | update | uninstall
#
# Options (environment variables):
#   RAPR_REF=<branch or tag>   what to install (default: main)
#   RAPR_SOURCE_DIR=<folder>   use this checkout instead of downloading (tests)
#   RAPR_NO_OPEN=1             don't start RAPR at the end (tests)
#   RAPR_YES=1                 answer yes to questions (tests)

set -euo pipefail

REPO="https://github.com/rawalrahul/raprai.git"
REF="${RAPR_REF:-main}"
HOME_DIR="$HOME/.rapr-ai"
VENV="$HOME_DIR/venv"
BIN="$HOME_DIR/bin"
DATA_DIR="$HOME/Library/Application Support/RAPR AI"
LOG_DIR="$HOME/Library/Logs/RAPR AI"
APP="$HOME/Applications/RAPR AI.app"

say()  { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ✓\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m ✗ %s\033[0m\n' "$*" >&2; exit 1; }

ask_yes() {   # ask_yes "question" -> 0 for yes
  [ "${RAPR_YES:-}" = 1 ] && return 0
  local a
  read -r -p "    $1 [y/N] " a </dev/tty || return 1
  [[ "$a" =~ ^[Yy] ]]
}

main() {
  [ "$(uname -s)" = "Darwin" ] || fail "This installer is for macOS. On Linux, use scripts/install-server.sh."
  local major
  major=$(sw_vers -productVersion | cut -d. -f1)
  [ "$major" -ge 12 ] || fail "RAPR needs macOS 12 (Monterey) or newer; this Mac has $(sw_vers -productVersion)."
  ok "macOS $(sw_vers -productVersion) on $(uname -m)"

  find_brew
  if [ -z "${BREW:-}" ]; then
    say "RAPR uses Homebrew (brew.sh) to install Python and Node.js."
    ask_yes "Install Homebrew now? It asks for your Mac password." \
      || fail "Install Homebrew from https://brew.sh, then run this again."
    NONINTERACTIVE="${RAPR_YES:-}" /bin/bash -c \
      "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/tty
    find_brew
    [ -n "${BREW:-}" ] || fail "Homebrew didn't install. See https://brew.sh."
  fi
  eval "$("$BREW" shellenv)"
  ok "Homebrew ready"

  local pkg missing=()
  for pkg in python@3.12 node git ffmpeg; do
    "$BREW" list --versions "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    say "Installing ${missing[*]} with Homebrew (a few minutes)..."
    "$BREW" install --quiet "${missing[@]}"
  fi
  local py
  py="$("$BREW" --prefix python@3.12)/bin/python3.12"
  [ -x "$py" ] || fail "Python 3.12 isn't where Homebrew should have put it ($py)."
  ok "Python, Node.js, git and ffmpeg ready"

  mkdir -p "$HOME_DIR" "$BIN" "$DATA_DIR" "$LOG_DIR"
  local app_dir
  if [ -n "${RAPR_SOURCE_DIR:-}" ]; then
    app_dir="$(cd "$RAPR_SOURCE_DIR" && pwd)"
    ok "Using RAPR from $app_dir"
  else
    app_dir="$HOME_DIR/app"
    if [ -d "$app_dir/.git" ]; then
      say "Updating RAPR..."
      git -C "$app_dir" fetch --quiet --depth 1 origin "$REF"
      git -C "$app_dir" checkout --quiet -B "$REF" FETCH_HEAD
    else
      say "Downloading RAPR..."
      rm -rf "$app_dir"
      git clone --quiet --depth 1 --branch "$REF" "$REPO" "$app_dir"
    fi
    ok "RAPR $(app_version "$app_dir") downloaded"
  fi

  if [ ! -x "$VENV/bin/python" ]; then
    "$py" -m venv "$VENV"
  fi
  say "Installing RAPR's Python packages (a few minutes the first time)..."
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r "$app_dir/requirements.txt"
  ok "Packages installed"

  write_env "$app_dir"
  write_launchers
  make_app "$app_dir"
  ln -sf "$BIN/rapr" "$("$BREW" --prefix)/bin/rapr"
  ok "Added RAPR AI to $HOME/Applications and the 'rapr' command"

  echo
  if [ "${RAPR_NO_OPEN:-}" = 1 ]; then
    printf '\033[1;32mRAPR AI is installed.\033[0m Open "RAPR AI" from your Applications folder.\n'
  else
    "$BIN/rapr-stop" >/dev/null 2>&1 || true     # an update restarts a running RAPR
    open "$APP"
    printf '\033[1;32mRAPR AI is installed and starting.\033[0m It opens in your browser in a few seconds.\n'
    echo "Next time, open \"RAPR AI\" from your Applications folder (or Spotlight)."
  fi
  echo "Quit the RAPR AI app (Cmd+Q) to stop RAPR. Run this command again to update."
  echo "Commands: rapr status | rapr logs | rapr update | rapr uninstall"
}

find_brew() {
  BREW=""
  local b
  for b in "$(command -v brew 2>/dev/null || true)" /opt/homebrew/bin/brew /usr/local/bin/brew; do
    if [ -n "$b" ] && [ -x "$b" ]; then BREW="$b"; return; fi
  done
}

app_version() {
  grep -oE 'APP_VERSION = "[^"]+"' "$1/helm/version.py" 2>/dev/null | cut -d'"' -f2 || true
}

# Settings the launchers share. Apps opened from Finder get a bare PATH, so
# take the one from the user's login shell: that's where Claude Code, Codex,
# nvm's Node and Homebrew live.
write_env() {
  local app_dir="$1" shell_path
  shell_path=$("${SHELL:-/bin/zsh}" -ilc 'printf "__RAPR_PATH__%s\n" "$PATH"' 2>/dev/null \
    | sed -n 's/^.*__RAPR_PATH__//p' | tail -1 || true)
  cat >"$HOME_DIR/env.sh" <<EOF
# Written by install-mac.sh; read by the RAPR launchers.
export RAPR_APP_DIR=$(printf '%q' "$app_dir")
export RAPR_VENV=$(printf '%q' "$VENV")
export RAPR_DATA_DIR=$(printf '%q' "$DATA_DIR")
export RAPR_LOG=$(printf '%q' "$LOG_DIR/rapr.log")
export RAPR_PID=$(printf '%q' "$HOME_DIR/rapr.pid")
export RAPR_INSTALLER_DIR=$(printf '%q' "$HOME_DIR")
export PATH=$(printf '%q' "${shell_path:+$shell_path:}$("$BREW" --prefix)/bin:$HOME/.local/bin:$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
EOF
}

write_launchers() {
  cat >"$BIN/rapr-running" <<'EOF'
#!/bin/bash
# Exit 0 if RAPR is running.
. "$HOME/.rapr-ai/env.sh"
[ -f "$RAPR_PID" ] && kill -0 "$(cat "$RAPR_PID")" 2>/dev/null
EOF
  cat >"$BIN/rapr-open" <<'EOF'
#!/bin/bash
# Open RAPR's window in the browser.
. "$HOME/.rapr-ai/env.sh"
port=$(cat "$RAPR_DATA_DIR/web_port" 2>/dev/null || echo 8000)
open "http://localhost:$port"
EOF
  cat >"$BIN/rapr-start" <<'EOF'
#!/bin/bash
# Start RAPR in the background (it opens the browser itself); if it's already
# running, just open it.
. "$HOME/.rapr-ai/env.sh"
if "$HOME/.rapr-ai/bin/rapr-running"; then
  exec "$HOME/.rapr-ai/bin/rapr-open"
fi
mkdir -p "$(dirname "$RAPR_LOG")"
cd "$RAPR_APP_DIR" || exit 1
nohup "$RAPR_VENV/bin/python" web_app.py >>"$RAPR_LOG" 2>&1 </dev/null &
echo $! >"$RAPR_PID"
EOF
  cat >"$BIN/rapr-stop" <<'EOF'
#!/bin/bash
# Stop RAPR (gracefully, then for good after 15 seconds).
. "$HOME/.rapr-ai/env.sh"
"$HOME/.rapr-ai/bin/rapr-running" || { rm -f "$RAPR_PID"; exit 0; }
pid=$(cat "$RAPR_PID")
kill -INT "$pid" 2>/dev/null
for _ in $(seq 1 30); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
kill -9 "$pid" 2>/dev/null || true
rm -f "$RAPR_PID"
EOF
  cat >"$BIN/rapr" <<'EOF'
#!/bin/bash
# RAPR AI on this Mac (written by install-mac.sh).
. "$HOME/.rapr-ai/env.sh"
B="$HOME/.rapr-ai/bin"
case "${1:-}" in
  start)   "$B/rapr-start" ;;
  stop)    "$B/rapr-stop" && echo "RAPR stopped." ;;
  open)    "$B/rapr-open" ;;
  status)
    if "$B/rapr-running"; then
      echo "RAPR is running at http://localhost:$(cat "$RAPR_DATA_DIR/web_port" 2>/dev/null || echo 8000)"
    else
      echo "RAPR is not running. Start it with: rapr start (or open the RAPR AI app)"; exit 1
    fi ;;
  logs)    tail -n 120 "$RAPR_LOG" ;;
  update)  curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-mac.sh | bash ;;
  uninstall)
    read -r -p "Remove RAPR from this Mac? Your chats and settings stay unless you also type 'all': [yes/all/N] " a </dev/tty
    case "$a" in yes|all) ;; *) echo "Nothing removed."; exit 0 ;; esac
    "$B/rapr-stop"
    rm -rf "$HOME/Applications/RAPR AI.app"
    rm -f "$(command -v rapr)"
    [ "$a" = all ] && rm -rf "$RAPR_DATA_DIR" "$(dirname "$RAPR_LOG")"
    rm -rf "$RAPR_INSTALLER_DIR"
    if [ "$a" = all ]; then echo "RAPR and its data removed."; else echo "RAPR removed. Your data is still in $RAPR_DATA_DIR"; fi ;;
  *) echo "Usage: rapr start | stop | open | status | logs | update | uninstall" ;;
esac
EOF
  chmod 755 "$BIN"/rapr "$BIN"/rapr-*
}

# A small native app (AppleScript, built on this Mac, so no Gatekeeper
# warning): open it to start RAPR, click it in the Dock to bring RAPR's window
# back, quit it to stop RAPR. It quits by itself if RAPR stops.
make_app() {
  local app_dir="$1" tmp
  tmp=$(mktemp -d)
  cat >"$tmp/rapr.applescript" <<EOF
on run
  do shell script quoted form of "$BIN/rapr-start" & " >/dev/null 2>&1"
end run

on reopen
  do shell script quoted form of "$BIN/rapr-open" & " >/dev/null 2>&1"
end reopen

on idle
  try
    do shell script quoted form of "$BIN/rapr-running"
  on error
    quit
  end try
  return 10
end idle

on quit
  do shell script quoted form of "$BIN/rapr-stop" & " >/dev/null 2>&1"
  continue quit
end quit
EOF
  mkdir -p "$(dirname "$APP")"
  rm -rf "$APP"
  osacompile -s -o "$APP" "$tmp/rapr.applescript"
  if [ -f "$app_dir/rapr-logo.png" ]; then
    local set="$tmp/rapr.iconset" s
    mkdir -p "$set"
    for s in 16 32 128 256 512; do
      sips -z "$s" "$s" "$app_dir/rapr-logo.png" --out "$set/icon_${s}x${s}.png" >/dev/null
      sips -z $((s * 2)) $((s * 2)) "$app_dir/rapr-logo.png" --out "$set/icon_${s}x${s}@2x.png" >/dev/null
    done
    iconutil -c icns "$set" -o "$APP/Contents/Resources/applet.icns" 2>/dev/null || true
  fi
  /usr/libexec/PlistBuddy -c "Set :CFBundleName RAPR AI" "$APP/Contents/Info.plist" 2>/dev/null || true
  /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.raprai.launcher" "$APP/Contents/Info.plist" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.raprai.launcher" "$APP/Contents/Info.plist" 2>/dev/null || true
  touch "$APP"
  rm -rf "$tmp"
}

main "$@"
