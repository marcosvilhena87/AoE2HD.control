"""Testes sem conexão ao jogo e sem depender do catálogo remoto."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from aoe2hdcontrol.catalog import CATALOGS, load_catalog, mapping_dir
from aoe2hdcontrol.__main__ import main


class CatalogTests(unittest.TestCase):
    def test_read_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / CATALOGS["genie"]
            path.parent.mkdir(parents=True)
            path.write_text("id,nome\\n83,aldeao\\n", encoding="utf-8")
            self.assertEqual(load_catalog("genie", root), [{"id": "83", "nome": "aldeao"}])

    def test_unknown_catalog(self):
        with self.assertRaises(ValueError):
            load_catalog("invalido", Path("."))

    def test_missing_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                load_catalog("memory", Path(temp))

    def test_override_path(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(mapping_dir(temp), Path(temp).resolve())

    def test_environment_path(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"AOE2HD_MAPPING_DIR": temp}):
                self.assertEqual(mapping_dir(), Path(temp).resolve())

    def test_doctor_fails_without_mapping(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(main(["--mapping-dir", temp, "doctor"]), 1)


if __name__ == "__main__":
    unittest.main()
