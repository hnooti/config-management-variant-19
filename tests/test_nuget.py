"""Проверка форматов NuGet и обращения к точной версии пакета."""

import json
import unittest
from unittest.mock import patch

from src.model import Package
from src.nuget import NuGetRepository
from src.nuspec import parse_nuspec
from src.version import parse_range, parse_version

INDEX = "https://example.test/v3/index.json"
BASE = "https://example.test/packages"
MANIFEST = b"""<package xmlns="http://schemas.microsoft.com/packaging/2013">
<metadata><dependencies>
  <group targetFramework="net8.0">
    <dependency id="Child" version="[1.2,2.0)" />
  </group>
  <group targetFramework="net7.0" />
  <group targetFramework=".NETStandard2.0">
    <dependency id="Other" version="4.0" />
  </group>
</dependencies></metadata></package>"""


class NuGetTests(unittest.TestCase):
    """Независимые от сети сценарии чтения пакета."""

    def test_versions_and_ranges(self):
        """Учитывать порядок prerelease и открытые границы."""
        self.assertEqual(str(parse_version("01.02+build")), "1.2.0")
        self.assertLess(parse_version("1.0-rc.2"), parse_version("1.0-rc.10"))
        self.assertLess(parse_version("1.0-rc.10"), parse_version("1.0"))
        self.assertTrue(parse_range("[1.2,2)").contains(parse_version("1.2.1")))
        self.assertFalse(parse_range("[1.2,2)").contains(parse_version("2")))
        self.assertTrue(parse_range("(,2]").contains(parse_version("2.0")))
        self.assertTrue(parse_range("[2.0]").contains(parse_version("2")))
        self.assertFalse(parse_range("1.2").contains(parse_version("2-beta")))
        self.assertTrue(parse_range("1-beta").contains(parse_version("1-rc")))
        with self.assertRaisesRegex(ValueError, "пустой диапазон"):
            parse_range("[1.2,1.2)")

    def test_groups(self):
        """Различить пустую точную группу и отсутствующую группу."""
        self.assertEqual(parse_nuspec(MANIFEST, "NET7.0"), ())
        self.assertEqual(len(parse_nuspec(MANIFEST, "")), 2)
        with self.assertRaisesRegex(ValueError, "нет группы"):
            parse_nuspec(MANIFEST, "net9.0")

    @patch("src.nuget._fetch")
    def test_api_reads_manifest_and_selects_lowest_version(self, fetch):
        """Пройти от индекса сервиса до точной версии и индекса потомка."""
        responses = {
            INDEX: json.dumps({"resources": [
                {"@id": BASE + "/", "@type": "PackageBaseAddress/3.0.0"}
            ]}).encode(),
            BASE + "/root/2.5.0/root.nuspec": MANIFEST,
            BASE + "/child/index.json": b'{"versions":["2.0", "1.5", "1.2"]}',
        }
        fetch.side_effect = responses.__getitem__
        repository = NuGetRepository(INDEX, "net8.0")
        root = Package("root", parse_version("2.5"))
        expected = (Package("child", parse_version("1.2")),)
        self.assertEqual(repository.children(root), expected)
        self.assertEqual(repository.children(root), expected)
        self.assertEqual(fetch.call_count, len(responses))
