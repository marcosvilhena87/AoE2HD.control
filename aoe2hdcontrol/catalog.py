"""Acesso somente leitura aos arquivos oficiais de AoE2HD.mapping."""
from __future__ import annotations
import csv
import os
from pathlib import Path

CATALOGS = {
    "genie": "dados/catalogos/tipos_genie.csv",
    "classes": "dados/catalogos/classes_objetos.csv",
    "identities": "dados/catalogos/identidades_individuais.csv",
    "memory": "dados/catalogos/estruturas_memoria.csv",
}


def mapping_dir(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("AOE2HD_MAPPING_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parents[2] / "AoE2HD.mapping").resolve()


def load_catalog(kind: str, root: Path) -> list[dict[str, str]]:
    if kind not in CATALOGS:
        raise ValueError(f"Catálogo desconhecido: {kind}")
    path = root / CATALOGS[kind]
    if not path.is_file():
        raise FileNotFoundError(f"Catálogo canônico não localizado: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"Catálogo sem cabeçalho: {path}")
        return list(reader)
