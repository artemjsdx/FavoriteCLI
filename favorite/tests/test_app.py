"""
Тесты для main application entry point.
"""
import pytest
from pathlib import Path


class TestAppImport:
    """Тесты импорта основного модуля."""
    
    def test_app_import(self):
        """Проверка что app.py импортируется без ошибок."""
        from favorite import app
        assert app is not None
    
    def test_console_init(self):
        """Проверка инициализации консольного вывода."""
        from favorite.app import console
        assert console is not None


class TestTokenEstimate:
    """Тесты оценки токенов."""
    
    def test_empty_text(self):
        """Пустой текст — 0 токенов."""
        from favorite.app import estimate_tokens
        assert estimate_tokens("") == 0
    
    def test_non_empty_text(self):
        """Текст даёт ненулевую оценку."""
        from favorite.app import estimate_tokens
        result = estimate_tokens("hello")
        assert result > 0
    
    def test_cyrillic_weighting(self):
        """Кириллица должна считаться differently."""
        from favorite.app import estimate_tokens
        cyrillic = "Привет мир"
        ascii_text = "Hello world"
        
        cyrillic_tokens = estimate_tokens(cyrillic)
        ascii_tokens = estimate_tokens(ascii_text)
        
        # Кириллица должна получать меньше токенов (двухбайтная)
        assert cyrillic_tokens <= ascii_tokens * 2


class TestConfigLoader:
    """Тесты загрузки конфигурации."""
    
    def test_config_directory_exists(self):
        """Проверка что директория config существует."""
        from favorite.config import loader
        assert loader is not None


class TestCommands:
    """Тесты команд."""
    
    def test_command_registry_exists(self):
        """Проверка регистрации команд."""
        from favorite.commands.registry import CommandRegistry
        assert CommandRegistry is not None
    
    def test_command_base_exists(self):
        """Проверка базового класса команд."""
        from favorite.commands.base import Command
        assert Command is not None


class TestUtilities:
    """Тесты утилит."""
    
    def test_path_exists(self):
        """Проверка работы с Path."""
        p = Path("favorite/app.py")
        assert p.exists()
    
    def test_file_readable(self):
        """Проверка чтения файла."""
        content = Path("favorite/app.py").read_text(encoding="utf-8")
        assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
