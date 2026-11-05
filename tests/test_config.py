"""Проверка разбора INI и диагностики каждого обязательного поля."""

import tempfile
import unittest
from pathlib import Path

from src.config import config_text, load_config

EXAMPLE = Path("examples/configuration.ini")


class ConfigTests(unittest.TestCase):
    """Сценарии работы с пользовательским конфигом."""

    def setUp(self):
        """Создать отдельный каталог для пользовательского файла."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "test.ini"
        self.example = EXAMPLE.read_text(encoding="utf-8")

    def test_valid_ini(self):
        """Прочитать настройки и вывести нормализованную версию."""
        config = load_config(EXAMPLE)
        self.assertEqual(config.package, "microsoft.extensions.configuration")
        self.assertEqual(str(config.version), "8.0.0")
        self.assertIn("ascii_tree=true", config_text(config))
        self.assertTrue(config.output.is_absolute())

    def test_invalid_parameter_values(self):
        """В каждом случае сообщить, какое поле не прошло проверку."""
        bad_values = {
            "package": ("Microsoft.Extensions.Configuration", "bad name"),
            "repository": ("https://api.nuget.org/v3/index.json", "file:///a"),
            "test_mode": ("false", "maybe"),
            "version": ("8.0.0", "latest"),
            "output": ("../out/configuration.svg", "graph.png"),
            "ascii_tree": ("true", "maybe"),
            "max_depth": ("5", "-1"),
            "target_framework": ("net8.0", "not a TFM"),
        }
        for key, (old, new) in bad_values.items():
            with self.subTest(key=key):
                content = self.example.replace(
                    f"{key} = {old}", f"{key} = {new}"
                )
                self.path.write_text(content, encoding="utf-8")
                message = "версия" if key == "version" else key
                with self.assertRaisesRegex(ValueError, message):
                    load_config(self.path)

    def test_test_mode_requires_local_file(self):
        """В режиме теста отклонить несуществующий файл графа."""
        content = self.example.replace(
            "package = Microsoft.Extensions.Configuration", "package = A"
        ).replace("test_mode = false", "test_mode = true")
        self.path.write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "repository: файл не найден"):
            load_config(self.path)
