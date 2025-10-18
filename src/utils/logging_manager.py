"""Менеджер логирования с автоматической ротацией и очисткой"""

import os
import logging
import logging.handlers
from datetime import datetime, timedelta
import glob
from pathlib import Path


class DailyRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Кастомный обработчик с автоматическим удалением старых логов"""
    
    def __init__(self, filename, when='midnight', interval=1, backupCount=7, encoding=None, delay=False, utc=False, atTime=None):
        """
        Инициализация обработчика
        
        Args:
            filename: Путь к файлу лога
            when: Когда ротировать ('midnight' для ежедневной ротации)
            interval: Интервал ротации
            backupCount: Количество файлов для хранения (0 = удалять каждый день)
            encoding: Кодировка файла
            delay: Отложенное создание файла
            utc: Использовать UTC время
            atTime: Время ротации
        """
        # Устанавливаем backupCount=0 для ежедневного удаления
        super().__init__(filename, when, interval, 0, encoding, delay, utc, atTime)
        self.max_days = backupCount if backupCount > 0 else 1
        
    def doRollover(self):
        """Выполнить ротацию и очистку старых файлов"""
        super().doRollover()
        self.cleanup_old_logs()
    
    def cleanup_old_logs(self):
        """Удалить логи старше указанного количества дней"""
        try:
            log_dir = os.path.dirname(self.baseFilename)
            log_name = os.path.basename(self.baseFilename)
            
            # Получаем все файлы логов
            pattern = os.path.join(log_dir, f"{log_name}.*")
            log_files = glob.glob(pattern)
            
            # Текущая дата
            now = datetime.now()
            cutoff_date = now - timedelta(days=self.max_days)
            
            for log_file in log_files:
                try:
                    # Получаем время создания файла
                    file_time = datetime.fromtimestamp(os.path.getctime(log_file))
                    
                    # Удаляем файл если он старше cutoff_date
                    if file_time < cutoff_date:
                        os.remove(log_file)
                        print(f"Удален старый лог файл: {log_file}")
                        
                except (OSError, ValueError) as e:
                    print(f"Ошибка при удалении лог файла {log_file}: {e}")
                    
        except Exception as e:
            print(f"Ошибка при очистке старых логов: {e}")


def setup_logging(log_level=logging.INFO, log_to_file=True, log_to_console=True, 
                 log_dir="logs", max_days=1):
    """
    Настройка системы логирования с ротацией
    
    Args:
        log_level: Уровень логирования
        log_to_file: Логировать в файл
        log_to_console: Логировать в консоль
        log_dir: Директория для логов
        max_days: Количество дней хранения логов (1 = удалять каждый день)
    """
    # Создаем директорию для логов если её нет
    if log_to_file:
        Path(log_dir).mkdir(exist_ok=True)
    
    # Формат логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Создаем форматтер
    formatter = logging.Formatter(log_format, date_format)
    
    # Получаем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Очищаем существующие обработчики
    root_logger.handlers.clear()
    
    handlers = []
    
    # Добавляем файловый обработчик с ротацией
    if log_to_file:
        log_filename = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d')}.log")
        
        file_handler = DailyRotatingFileHandler(
            filename=log_filename,
            when='midnight',
            interval=1,
            backupCount=max_days,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Добавляем консольный обработчик
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # Добавляем все обработчики
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Настраиваем логирование для httpx (слишком много INFO сообщений)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # Логируем успешную инициализацию
    logger = logging.getLogger(__name__)
    logger.info(f"Система логирования инициализирована. Уровень: {logging.getLevelName(log_level)}")
    if log_to_file:
        logger.info(f"Логи сохраняются в: {log_dir}/")
        logger.info(f"Автоматическое удаление логов через: {max_days} дн.")


def cleanup_old_logs_manual(log_dir="logs", max_days=1):
    """
    Ручная очистка старых логов
    
    Args:
        log_dir: Директория с логами
        max_days: Количество дней для хранения
    """
    try:
        if not os.path.exists(log_dir):
            return
        
        now = datetime.now()
        cutoff_date = now - timedelta(days=max_days)
        
        # Получаем все .log файлы
        log_files = glob.glob(os.path.join(log_dir, "*.log"))
        
        removed_count = 0
        for log_file in log_files:
            try:
                # Получаем время создания файла
                file_time = datetime.fromtimestamp(os.path.getctime(log_file))
                
                # Удаляем файл если он старше cutoff_date
                if file_time < cutoff_date:
                    os.remove(log_file)
                    removed_count += 1
                    print(f"Удален старый лог файл: {log_file}")
                    
            except (OSError, ValueError) as e:
                print(f"Ошибка при удалении лог файла {log_file}: {e}")
        
        if removed_count > 0:
            logger = logging.getLogger(__name__)
            logger.info(f"Удалено {removed_count} старых лог файлов")
        
    except Exception as e:
        print(f"Ошибка при ручной очистке логов: {e}")


def get_log_stats(log_dir="logs"):
    """
    Получить статистику по логам
    
    Args:
        log_dir: Директория с логами
        
    Returns:
        dict: Статистика по логам
    """
    try:
        if not os.path.exists(log_dir):
            return {"error": "Директория логов не существует"}
        
        log_files = glob.glob(os.path.join(log_dir, "*.log"))
        
        if not log_files:
            return {"files_count": 0, "total_size": 0}
        
        total_size = 0
        files_info = []
        
        for log_file in log_files:
            try:
                stat = os.stat(log_file)
                size = stat.st_size
                created = datetime.fromtimestamp(stat.st_ctime)
                modified = datetime.fromtimestamp(stat.st_mtime)
                
                total_size += size
                files_info.append({
                    "name": os.path.basename(log_file),
                    "size": size,
                    "size_mb": round(size / 1024 / 1024, 2),
                    "created": created.strftime('%Y-%m-%d %H:%M:%S'),
                    "modified": modified.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            except OSError:
                continue
        
        return {
            "files_count": len(files_info),
            "total_size": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "files": sorted(files_info, key=lambda x: x['created'], reverse=True)
        }
        
    except Exception as e:
        return {"error": str(e)}
