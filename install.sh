#!/usr/bin/env bash
#
# ROBIXA BOT Installer v2.1.512
# One-liner: bash <(curl -fsSL https://raw.githubusercontent.com/mrmarzx/ROBIXA-BOT/main/install.sh)
#
set -euo pipefail

REPO_URL="https://github.com/mrmarzx/ROBIXA-BOT.git"
REPO_NAME="ROBIXA-BOT"

_SELF="${BASH_SOURCE[0]:-}"
if [[ -n "$_SELF" && -f "$_SELF" ]]; then
  _DIR="$(cd "$(dirname "$_SELF")" && pwd)"
else
  _DIR=""
fi

if [[ -z "$_DIR" || ! -f "${_DIR}/main.py" ]]; then
  if ! command -v git &>/dev/null; then
    echo "git is required. Install: sudo apt install git"
    exit 1
  fi
  echo "Cloning ROBIXA BOT..."
  TARGET="${HOME}/${REPO_NAME}"
  if [[ -d "$TARGET/.git" ]]; then
    git -C "$TARGET" pull --ff-only || true
  else
    rm -rf "$TARGET"
    git clone --depth 1 "$REPO_URL" "$TARGET"
  fi
  cd "$TARGET"
  exec bash "./install.sh" "$@"
fi

INSTALL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$INSTALL_ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'
BOLD='\033[1m'; NC='\033[0m'
SPINNER=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')

VENV_DIR="${INSTALL_ROOT}/venv"
DATA_DIR="${INSTALL_ROOT}/data"
ENV_FILE="${INSTALL_ROOT}/.env"
SERVICE_NAME="robixa-bot"
BIN_LINK="/usr/local/bin/robixa"
LOG_FILE="${INSTALL_ROOT}/data/robixa.log"

print_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    cat << 'EOF'
  ____   ___  ____ _____  __  __    _    
 |  _ \ / _ \| __ )_ _\ \/ /   / \   
 | |_) | | | |  _ \| | \  /   / _ \  
 |  _ <| |_| | |_) | | /  \  / ___ \ 
 |_| \_\\___/|____/___/_/\_\/_/   \_\
EOF
    echo -e "${NC}"
    echo -e "${BOLD}          ROBIXA BOT  •  v2.1.512${NC}"
    echo -e "${BLUE}     Multi-Panel Telegram Shop  •  Phase 1-2-3${NC}"
    echo ""
}

progress_bar() {
    local current=$1 total=$2 width=42
    local percent=$(( current * 100 / total ))
    local filled=$(( current * width / total ))
    local empty=$(( width - filled ))
    printf "\r  ${CYAN}["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] ${BOLD}%3d%%${NC}  " "$percent"
}

spin_and_run() {
    local msg="$1"; shift
    local cmd=("$@")
    local pid i=0
    echo -ne "  ${YELLOW}${SPINNER[0]}${NC} ${msg}..."
    "${cmd[@]}" > /tmp/robixa_install.log 2>&1 &
    pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        i=$(( (i + 1) % ${#SPINNER[@]} ))
        echo -ne "\r  ${YELLOW}${SPINNER[$i]}${NC} ${msg}..."
        sleep 0.08
    done
    if wait "$pid"; then
        echo -e "\r  ${GREEN}✔${NC} ${msg}                         "
        return 0
    else
        echo -e "\r  ${RED}✖${NC} ${msg}                         "
        echo -e "${RED}Error details:${NC}"
        cat /tmp/robixa_install.log
        return 1
    fi
}

detect_previous() {
    local found=0
    if [[ -d "$VENV_DIR" ]] || [[ -f "$ENV_FILE" ]] || [[ -d "$DATA_DIR" && -n "$(ls -A "$DATA_DIR" 2>/dev/null || true)" ]]; then
        found=1
    fi
    if [[ -L "$BIN_LINK" ]] || [[ -f "$BIN_LINK" ]]; then found=1; fi
    if systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE_NAME}.service"; then found=1; fi
    echo $found
}

wipe_previous() {
    echo -e "\n  ${YELLOW}Removing previous ROBIXA installation...${NC}"
    if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        sudo systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    fi
    if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        sudo systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
    fi
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service" 2>/dev/null || true
    sudo systemctl daemon-reload 2>/dev/null || true
    sudo rm -f "$BIN_LINK" 2>/dev/null || true
    rm -rf "$VENV_DIR" 2>/dev/null || true
    rm -rf "$DATA_DIR" 2>/dev/null || true
    rm -f "$ENV_FILE" 2>/dev/null || true
    echo -e "  ${GREEN}✔${NC} Previous installation wiped"
}

ask_yes_no() {
    local prompt="$1" answer
    while true; do
        echo -ne "  ${YELLOW}${prompt} [Y/N]: ${NC}"
        read -r answer
        case "${answer,,}" in
            y|yes) return 0 ;;
            n|no)  return 1 ;;
            *) echo -e "  ${RED}Please type Y or N${NC}" ;;
        esac
    done
}

ask_admin_id() {
    local id
    while true; do
        echo -ne "  ${CYAN}Enter main Admin numeric Telegram ID: ${NC}"
        read -r id
        if [[ "$id" =~ ^[0-9]+$ ]] && [[ ${#id} -ge 5 ]]; then
            ADMIN_ID="$id"; return 0
        fi
        echo -e "  ${RED}Invalid ID. Numbers only (e.g. 123456789)${NC}"
    done
}

ask_bot_token() {
    local token
    while true; do
        echo -ne "  ${CYAN}Enter BotFather Token: ${NC}"
        read -r token
        if [[ "$token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
            BOT_TOKEN="$token"; return 0
        fi
        echo -e "  ${RED}Invalid token format. Example: 123456:ABC-DEF...${NC}"
    done
}

check_python() {
    if ! command -v python3 &>/dev/null; then
        echo -e "${RED}Python 3 not found. Install Python 3.10+${NC}"; exit 1
    fi
    local ver
    ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
        echo -e "${RED}Python 3.10+ required. Found ${ver}${NC}"; exit 1
    fi
    echo -e "  ${GREEN}✔${NC} Python ${ver}"
}

install_cli() {
    local cli_src="${INSTALL_ROOT}/scripts/robixa"
    if [[ ! -f "$cli_src" ]]; then
        echo -e "  ${RED}CLI script missing${NC}"; return 1
    fi
    chmod +x "$cli_src" || true
    if command -v sudo &>/dev/null; then
        sudo tee "$BIN_LINK" > /dev/null << EOF
#!/usr/bin/env bash
cd "${INSTALL_ROOT}"
exec bash "${INSTALL_ROOT}/scripts/robixa" "\$@"
EOF
        sudo chmod +x "$BIN_LINK" || true
    else
        mkdir -p "$HOME/bin"
        cat > "$HOME/bin/robixa" << EOF
#!/usr/bin/env bash
cd "${INSTALL_ROOT}"
exec bash "${INSTALL_ROOT}/scripts/robixa" "\$@"
EOF
        chmod +x "$HOME/bin/robixa"
        echo -e "  ${YELLOW}Installed to ~/bin/robixa (add ~/bin to PATH if needed)${NC}"
    fi
    echo -e "  ${GREEN}✔${NC} CLI → ${BOLD}robixa${NC}"
}

write_env() {
    cat > "$ENV_FILE" << EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_IDS=${ADMIN_ID}
DATABASE_URL=sqlite+aiosqlite:///./data/robixa.db
BOT_VERSION=2.1.512
BOT_NAME=ROBIXA BOT
SUPPORT_USERNAME=@Support
BACKUP_INTERVAL_HOURS=24
BACKUP_CHAT_ID=
EOF
    chmod 600 "$ENV_FILE" || true
}


install_systemd_service() {
    local service_file="/etc/systemd/system/${SERVICE_NAME}.service"
    local py="${VENV_DIR}/bin/python"
    local main="${INSTALL_ROOT}/main.py"
    if [[ ! -x "$py" ]]; then
        echo -e "  ${YELLOW}⚠${NC} venv python not found – skip systemd"
        return 0
    fi
    sudo tee "$service_file" > /dev/null << UNIT
[Unit]
Description=ROBIXA BOT Telegram Reseller Shop
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_ROOT}
Environment=PYTHONUNBUFFERED=1
ExecStart=${py} ${main}
Restart=always
RestartSec=5
StandardOutput=append:${INSTALL_ROOT}/data/robixa.log
StandardError=append:${INSTALL_ROOT}/data/robixa.log

[Install]
WantedBy=multi-user.target
UNIT
    sudo systemctl daemon-reload
    sudo systemctl enable "${SERVICE_NAME}.service" >/dev/null 2>&1 || true
    sudo systemctl restart "${SERVICE_NAME}.service" || sudo systemctl start "${SERVICE_NAME}.service" || true
    sleep 1
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo -e "  ${GREEN}✔${NC} systemd service active (${SERVICE_NAME}) – bot stays running"
    else
        echo -e "  ${YELLOW}⚠${NC} service installed but not active – run: sudo systemctl start ${SERVICE_NAME}"
        echo -e "      logs: journalctl -u ${SERVICE_NAME} -n 50 --no-pager"
    fi
}


main() {
    print_banner
    TOTAL=10; STEP=0

    if [[ "$(detect_previous)" == "1" ]]; then
        echo -e "${YELLOW}${BOLD}⚠  Previous ROBIXA installation detected.${NC}"
        if ask_yes_no "Completely REMOVE previous installation?"; then
            wipe_previous
        else
            echo -e "  ${BLUE}Keeping existing data.${NC}"
        fi
        echo ""
    fi

    echo -e "${BOLD}Configuration:${NC}\n"
    ask_admin_id
    ask_bot_token
    echo ""

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} System check"
    check_python; sleep 0.15

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} Virtual environment"
    if [[ ! -d "$VENV_DIR" ]]; then
        spin_and_run "Creating venv" python3 -m venv "$VENV_DIR"
    else
        echo -e "  ${GREEN}✔${NC} venv exists"
    fi
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} Upgrading pip"
    spin_and_run "Upgrading pip" pip install --upgrade pip setuptools wheel

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} Installing packages"
    spin_and_run "Installing dependencies" pip install -r "${INSTALL_ROOT}/requirements.txt"

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} Data directory"
    mkdir -p "$DATA_DIR"
    echo -e "  ${GREEN}✔${NC} data/ ready"

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} Configuration"
    write_env
    echo -e "  ${GREEN}✔${NC} .env written"

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} Generators"
    python3 -c "from utils.generators import generate_username, generate_password; assert generate_username().startswith('HHabVI')"
    echo -e "  ${GREEN}✔${NC} OK"

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} CLI"
    install_cli

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} Import check"
    python3 -c "import aiogram, httpx, aiosqlite, sqlalchemy, pydantic"
    echo -e "  ${GREEN}✔${NC} Packages OK"

    STEP=$((STEP+1)); progress_bar $STEP $TOTAL; echo -e "\n  ${BLUE}→${NC} systemd service"
    install_systemd_service

    progress_bar $TOTAL $TOTAL
    echo ""
    echo ""
    echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}   ROBIXA BOT installed successfully!${NC}"
    echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Bot runs as systemd service: ${BOLD}${SERVICE_NAME}${NC}"
    echo -e "  Status:  ${BOLD}sudo systemctl status ${SERVICE_NAME}${NC}"
    echo -e "  Restart: ${BOLD}sudo systemctl restart ${SERVICE_NAME}${NC}"
    echo -e "  Stop:    ${BOLD}sudo systemctl stop ${SERVICE_NAME}${NC}"
    echo -e "  Logs:    ${BOLD}journalctl -u ${SERVICE_NAME} -f${NC}"
    echo -e "  Or:      ${BOLD}robixa${NC}  (menu)"
    echo -e "  Admin ID: ${BOLD}${ADMIN_ID}${NC}"
    echo ""
}

main "$@"
