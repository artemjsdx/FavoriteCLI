#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════
#  Termux Developer Environment Setup Script
#  Автоматическая настройка рабочего окружения
# ═══════════════════════════════════════════════════════════════════════════

set -e

# ─── Цвета ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ─── Переменные ───
REPORT_FILE="/tmp/setup_report.txt"
LOG_FILE="/tmp/setup.log"
INSTALL_LOG="/tmp/install_details.log"

# ─── Функции ───
log() {
    echo -e "$1"
    echo -e "$1" | sed 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE"
}

log_detail() {
    echo "$1" >> "$INSTALL_LOG"
}

success() {
    echo -e " ${GREEN}✓${NC} $1"
    echo "✓ $1" >> "$REPORT_FILE"
}

error() {
    echo -e " ${RED}✗${NC} $1"
    echo "✗ $1" >> "$REPORT_FILE"
}

info() {
    echo -e " ${CYAN}ℹ${NC} $1"
}

header() {
    echo ""
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}"
}

step() {
    echo -e "\n${YELLOW}▶ $1${NC}"
}

# ─── Инициализация логов ───
> "$REPORT_FILE"
> "$LOG_FILE"
> "$INSTALL_LOG"

# ─── Проверка запуска в Termux ───
header "Проверка окружения"

if [[ ! -f "/data/data/com.termux/files/usr/bin/pkg" ]]; then
    error "Скрипт предназначен для запуска в Termux!"
    info "Скачайте Termux: https://f-droid.org/packages/com.termux/"
    exit 1
fi

success "Обнаружен Termux"
info "Начинаем настройку окружения..."

# ─── Обновление пакетов ───
header "Обновление пакетной базы"

step "Обновление списка пакетов..."
if pkg update -y &>> "$INSTALL_LOG"; then
    success "Список пакетов обновлён"
else
    error "Не удалось обновить список пакетов"
fi

step "Обновление установленных пакетов..."
if pkg upgrade -y &>> "$INSTALL_LOG"; then
    success "Пакеты обновлены"
else
    error "Не удалось обновить пакеты"
fi

# ─── Установка базовых пакетов ───
header "Установка базовых пакетов"

BASIC_PACKAGES=(
    "git"
    "curl"
    "wget"
    "python"
    "nodejs"
    "nano"
    "termux-tools"
    "clang"
    "make"
    "openssh"
    "tree"
    "htop"
    "vim"
)

INSTALLED_PACKAGES=""
FAILED_PACKAGES=""

for pkg_name in "${BASIC_PACKAGES[@]}"; do
    step "Установка $pkg_name..."
    if pkg install -y "$pkg_name" &>> "$INSTALL_LOG"; then
        success "Установлен: $pkg_name"
        INSTALLED_PACKAGES="$INSTALLED_PACKAGES $pkg_name"
    else
        error "Не удалось установить: $pkg_name"
        FAILED_PACKAGES="$FAILED_PACKAGES $pkg_name"
    fi
done

# ─── Установка Python и pip ───
header "Настройка Python"

step "Проверка Python..."
if command -v python &>> "$INSTALL_LOG"; then
    PYTHON_VERSION=$(python --version 2>&1)
    success "Python: $PYTHON_VERSION"
    echo "Python: $PYTHON_VERSION" >> "$REPORT_FILE"
else
    error "Python не найден"
fi

step "Установка pip..."
if ! command -v pip &>> "$INSTALL_LOG"; then
    if pkg install -y python-pip &>> "$INSTALL_LOG"; then
        success "pip установлен"
    else
        error "Не удалось установить pip"
    fi
else
    success "pip уже установлен"
fi

# ─── Установка Python пакетов ───
header "Установка Python пакетов"

PYTHON_PACKAGES=(
    "requests"
    "flask"
    "aiogram"
    "httpx"
    "pillow"
    "python-dotenv"
    "aiohttp"
)

for pkg_name in "${PYTHON_PACKAGES[@]}"; do
    step "Установка $pkg_name..."
    if pip install "$pkg_name" --break-system-packages &>> "$INSTALL_LOG"; then
        success "Установлен: $pkg_name"
    else
        error "Не удалось установить: $pkg_name"
    fi
done

# ─── Настройка оболочки ───
header "Настройка оболочки"

SHELL_RC=""
CURRENT_SHELL=$(basename "$SHELL")

# Проверяем текущую оболочку
if [[ -n "$SHELL" ]]; then
    CURRENT_SHELL=$(basename "$SHELL")
else
    CURRENT_SHELL="bash"
fi

info "Текущая оболочка: $CURRENT_SHELL"

# Определяем какой RC файл использовать
if [[ "$CURRENT_SHELL" == "zsh" ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$CURRENT_SHELL" == "bash" ]] || [[ -f "$HOME/.bashrc" ]]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.bashrc"
fi

info "Используем файл: $SHELL_RC"

# ─── Проверка Oh My Zsh ───
header "Настройка Oh My Zsh"

if command -v zsh &>> "$INSTALL_LOG"; then
    step "Zsh доступен, проверка Oh My Zsh..."
    
    if [[ -d "$HOME/.oh-my-zsh" ]]; then
        success "Oh My Zsh уже установлен"
    else
        info "Установка Oh My Zsh..."
        
        # Установка Oh My Zsh
        if sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended &>> "$INSTALL_LOG"; then
            success "Oh My Zsh установлен"
            
            # Настройка плагинов
            step "Установка плагинов zsh..."
            
            # zsh-autosuggestions
            if [[ ! -d "$HOME/.oh-my-zsh/custom/plugins/zsh-autosuggestions" ]]; then
                git clone https://github.com/zsh-users/zsh-autosuggestions "$HOME/.oh-my-zsh/custom/plugins/zsh-autosuggestions" &>> "$INSTALL_LOG" || true
            fi
            
            # zsh-syntax-highlighting
            if [[ ! -d "$HOME/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting" ]]; then
                git clone https://github.com/zsh-users/zsh-syntax-highlighting "$HOME/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting" &>> "$INSTALL_LOG" || true
            fi
            
            # Обновляем SHELL_RC на .zshrc
            SHELL_RC="$HOME/.zshrc"
            success "Плагины установлены"
        else
            error "Не удалось установить Oh My Zsh"
        fi
    fi
else
    info "Zsh не установлен, используем улучшенный bash prompt"
    # Создаём красивый bash prompt
    step "Настройка красивого bash prompt..."
fi

# ─── Добавление алиасов ───
header "Настройка алиасов"

# Проверяем, не добавлены ли уже алиасы
if ! grep -q "# === Termux Setup Aliases ===" "$SHELL_RC" 2>/dev/null; then
    cat >> "$SHELL_RC" << 'EOF'

# === Termux Setup Aliases ===
# Основные алиасы
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'
alias py='python'
alias python='python3'

# Навигация
alias home='cd ~'
alias projects='cd ~/projects'

# Git короткие команды
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline -10'

# System
alias update='pkg update && pkg upgrade'
alias ports='netstat -tulanp'
alias meminfo='free -m -l'
alias dfh='df -h'

# Конфигурация
alias edit-bash='nano ~/.bashrc'
alias edit-zsh='nano ~/.zshrc'
alias reload='source ~/.bashrc'

# mkcd - создать папку и перейти в неё
mkcd() {
    mkdir -p "$1" && cd "$1"
}

# extract - распаковать архив
extract() {
    if [ -f "$1" ]; then
        case "$1" in
            *.tar.bz2) tar xjf "$1" ;;
            *.tar.gz) tar xzf "$1" ;;
            *.bz2) bunzip2 "$1" ;;
            *.rar) unrar x "$1" ;;
            *.gz) gunzip "$1" ;;
            *.tar) tar xf "$1" ;;
            *.tbz2) tar xjf "$1" ;;
            *.tgz) tar xzf "$1" ;;
            *.zip) unzip "$1" ;;
            *.Z) uncompress "$1" ;;
            *.7z) 7z x "$1" ;;
            *) echo "Не могу распаковать '$1'" ;;
        esac
    else
        echo "'$1' не является файлом"
    fi
}

# === Termux Setup Colors ===
export CLICOLOR=1
export LSCOLORS=ExFxBxDxCxegedabagacad

# === Termux Setup Path ===
export PATH="$HOME/bin:$PATH"

# === End Termux Setup ===
EOF
    success "Алиасы добавлены в $SHELL_RC"
else
    info "Алиасы уже существуют в $SHELL_RC"
fi

# ─── Создание директорий ───
header "Создание директорий"

step "Создание ~/projects..."
if mkdir -p "$HOME/projects"; then
    success "Директория ~/projects создана"
else
    error "Не удалось создать ~/projects"
fi

step "Создание ~/bin..."
if mkdir -p "$HOME/bin"; then
    success "Директория ~/bin создана"
else
    error "Не удалось создать ~/bin"
fi

step "Создание ~/downloads..."
if mkdir -p "$HOME/downloads"; then
    success "Директория ~/downloads создана"
else
    error "Не удалось создать ~/downloads"
fi

# ─── Настройка Git ───
header "Настройка Git"

step "Проверка git..."
if command -v git &>> "$INSTALL_LOG"; then
    GIT_VERSION=$(git --version)
    success "Git: $GIT_VERSION"
    
    # Базовая настройка git (если не настроено)
    if [[ ! -f "$HOME/.gitconfig" ]]; then
        info "Создание базовой конфигурации git..."
        git config --global init.defaultBranch main
        git config --global pull.rebase false
        git config --global user.name "Termux User"
        git config --global user.email "user@termux.local"
        success "Git настроен (можно изменить: git config --global user.name \"Ваше Имя\")"
    else
        info "Git уже настроен"
    fi
else
    error "Git не установлен"
fi

# ─── Настройка Node.js ───
header "Настройка Node.js"

if command -v node &>> "$INSTALL_LOG"; then
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    success "Node.js: $NODE_VERSION"
    success "npm: $NPM_VERSION"
    
    # Установка глобальных пакетов
    step "Установка глобальных npm пакетов..."
    for pkg in npm yarn serve; do
        if npm install -g "$pkg" &>> "$INSTALL_LOG"; then
            success "Установлен: $pkg"
        else
            error "Не удалось установить: $pkg"
        fi
    done
else
    error "Node.js не установлен"
fi

# ─── Termux API ───
header "Настройка Termux API"

step "Проверка Termux:API..."
if pkg show termux-api &>> "$INSTALL_LOG"; then
    if ! dpkg -l | grep -q "termux-api"; then
        if pkg install -y termux-api &>> "$INSTALL_LOG"; then
            success "Termux:API установлен"
            info "Доступны команды: termux-battery-status, termux-camera-photo, и др."
        else
            error "Не удалось установить Termux:API"
        fi
    else
        success "Termux:API уже установлен"
    fi
else
    info "Termux:API недоступен в данном репозитории"
fi

# ─── Итоговый отчёт ───
header "Установка завершена!"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e " ${GREEN}✓${NC} ${BOLD}Успешно установлено:${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Показываем установленные пакеты
cat "$REPORT_FILE"

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e " ${YELLOW}📋${NC} ${BOLD}Следующие шаги:${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  1. Перезагрузите оболочку:"
echo "     • Для bash: source ~/.bashrc"
echo "     • Для zsh:  source ~/.zshrc"
echo "     • Или просто закройте и откройте терминал"
echo ""
echo "  2. Настройте git (если нужно):"
echo "     git config --global user.name 'Ваше Имя'"
echo "     git config --global user.email 'your@email.com'"
echo ""
echo "  3. Проверьте установку:"
echo "     python --version"
echo "     node --version"
echo "     git --version"
echo "     ll"
echo ""
echo "  4. Создайте первый проект:"
echo "     cd ~/projects"
echo "     mkcd myproject"
echo ""

# ─── Статус завершения ───
if [[ -n "$FAILED_PACKAGES" ]]; then
    echo -e "${RED}⚠ Внимание: некоторые пакеты не удалось установить:${NC}"
    echo -e "${RED}$FAILED_PACKAGES${NC}"
    echo ""
    echo "Проверьте лог: $INSTALL_LOG"
fi

echo -e "${GREEN}Лог установки сохранён в: $LOG_FILE${NC}"
echo ""
echo -e "${CYAN}Спасибо за использование Termux Setup! 🚀${NC}"
