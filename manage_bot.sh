#!/bin/bash

# Скрипт для управления Meow Bot
# Использование: ./manage_bot.sh [start|stop|restart|status|logs|install]

BOT_NAME="meow-bot"
SERVICE_FILE="meow-bot.service"
BOT_DIR="$(pwd)"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав суперпользователя
check_sudo() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Этот скрипт должен быть запущен с правами суперпользователя (sudo)"
        exit 1
    fi
}

# Установка сервиса
install_service() {
    check_sudo
    print_status "Установка systemd сервиса..."
    
    # Получаем текущего пользователя
    CURRENT_USER=$(who am i | awk '{print $1}')
    if [[ -z "$CURRENT_USER" ]]; then
        CURRENT_USER=$SUDO_USER
    fi
    
    # Обновляем пути в файле сервиса
    sed -i "s|YOUR_USERNAME|$CURRENT_USER|g" $SERVICE_FILE
    sed -i "s|/path/to/your/my-meow-bot|$BOT_DIR|g" $SERVICE_FILE
    
    # Копируем файл сервиса
    cp $SERVICE_FILE /etc/systemd/system/
    
    # Перезагружаем systemd
    systemctl daemon-reload
    
    # Включаем автозапуск
    systemctl enable $BOT_NAME
    
    print_status "Сервис установлен и включен для автозапуска"
    print_status "Используйте: sudo systemctl start $BOT_NAME"
}

# Запуск бота
start_bot() {
    check_sudo
    print_status "Запуск бота..."
    systemctl start $BOT_NAME
    
    if systemctl is-active --quiet $BOT_NAME; then
        print_status "Бот успешно запущен!"
    else
        print_error "Ошибка при запуске бота"
        systemctl status $BOT_NAME
        exit 1
    fi
}

# Остановка бота
stop_bot() {
    check_sudo
    print_status "Остановка бота..."
    systemctl stop $BOT_NAME
    print_status "Бот остановлен"
}

# Перезапуск бота
restart_bot() {
    check_sudo
    print_status "Перезапуск бота..."
    systemctl restart $BOT_NAME
    
    if systemctl is-active --quiet $BOT_NAME; then
        print_status "Бот успешно перезапущен!"
    else
        print_error "Ошибка при перезапуске бота"
        systemctl status $BOT_NAME
        exit 1
    fi
}

# Статус бота
status_bot() {
    print_status "Статус бота:"
    systemctl status $BOT_NAME --no-pager -l
}

# Просмотр логов
show_logs() {
    print_status "Последние логи бота:"
    journalctl -u $BOT_NAME -f --no-pager
}

# Просмотр логов файла
show_file_logs() {
    if [[ -d "logs" ]]; then
        print_status "Логи из файлов:"
        ls -la logs/
        echo ""
        if [[ -f "logs/bot_$(date +%Y%m%d).log" ]]; then
            tail -f logs/bot_$(date +%Y%m%d).log
        else
            print_warning "Лог файл за сегодня не найден"
        fi
    else
        print_warning "Папка logs не найдена"
    fi
}

# Основная логика
case "$1" in
    install)
        install_service
        ;;
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    logs)
        show_logs
        ;;
    file-logs)
        show_file_logs
        ;;
    *)
        echo "Использование: $0 {install|start|stop|restart|status|logs|file-logs}"
        echo ""
        echo "Команды:"
        echo "  install    - Установить systemd сервис"
        echo "  start      - Запустить бота"
        echo "  stop       - Остановить бота"
        echo "  restart    - Перезапустить бота"
        echo "  status     - Показать статус бота"
        echo "  logs       - Показать логи systemd"
        echo "  file-logs  - Показать логи из файлов"
        exit 1
        ;;
esac

exit 0 