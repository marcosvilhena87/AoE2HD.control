"""API experimental somente leitura para AoK HD.exe 5.8.INT (x86).

Nenhum offset fica duplicado no codigo: todos sao carregados do AoE2HD.mapping.
Campos com evidencia `hipotese` ou `ancora_experimental` exigem opt-in explicito.
"""
from __future__ import annotations

import ctypes
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .catalog import load_catalog, mapping_dir

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class ObjectAPIError(RuntimeError):
    """Falha controlada sem tentativa de escrita na memoria."""


class MemoryReader(Protocol):
    module_base: int
    def read(self, address: int, size: int) -> bytes: ...


@dataclass(frozen=True)
class HDObject:
    object_id: int
    address: int
    class_id: int | None
    genie_type_id: int | None
    owner_address: int | None
    position: tuple[float, float] | None
    candidate_fields: tuple[str, ...]


@dataclass(frozen=True)
class HDPlayer:
    slot: int
    address: int


class MappingOffsets:
    """Consulta exclusivamente dados/enderecos espelhados em catalogo canonico."""
    def __init__(self, root: Path, *, allow_candidates: bool = False):
        self.allow_candidates = allow_candidates
        self.entries: dict[tuple[str, str], dict[str, str]] = {}
        for row in load_catalog("memory", root):
            key = (row["raiz"], row["offset_ou_endereco"].lower())
            if key in self.entries:
                raise ObjectAPIError(f"Offset duplicado: {key}")
            self.entries[key] = row

    def get(self, root: str, hex_offset: str, *, candidate: bool = False) -> int:
        key = (root, hex_offset.lower())
        row = self.entries.get(key)
        if row is None:
            raise ObjectAPIError(f"Falta mapeamento: {root}+{hex_offset}")
        status = row["status"]
        trusted = status in {"validado", "historico_validado"}
        if not trusted and not (self.allow_candidates and candidate):
            raise ObjectAPIError(f"Campo nao validado: {root}+{hex_offset} ({status}); habilite allow_candidates conscientemente")
        return int(row["offset_ou_endereco"], 0)


class WindowsProcessReader:
    """Leitura Win32 sem PROCESS_VM_WRITE, sem injeção e sem abrir processo por PID implicitamente."""
    def __init__(self, pid: int, *, expected_name: str = "AoK HD.exe"):
        if os.name != "nt":
            raise ObjectAPIError("Leitura de processo real disponivel somente no Windows")
        if pid <= 0:
            raise ValueError("PID invalido")
        from ctypes import wintypes
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self._kernel.OpenProcess.restype = wintypes.HANDLE
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.CloseHandle.restype = wintypes.BOOL
        self._kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        self._kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self._kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self._kernel.ReadProcessMemory.restype = wintypes.BOOL
        self._handle = self._kernel.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not self._handle:
            raise ObjectAPIError(f"OpenProcess falhou: {ctypes.get_last_error()}")
        self.module_base = 0
        try:
            # A versao do executavel deve ser confirmada externamente; o nome sozinho nao basta.
            class MODULEENTRY32W(ctypes.Structure):
                _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
                            ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
                            ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
                            ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
                            ("szModule", wintypes.WCHAR * 256), ("szExePath", wintypes.WCHAR * 260)]
            self._kernel.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
            self._kernel.Module32FirstW.restype = wintypes.BOOL
            self._kernel.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
            self._kernel.Module32NextW.restype = wintypes.BOOL
            snap = self._kernel.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
            if snap == INVALID_HANDLE_VALUE:
                raise ObjectAPIError("Nao foi possivel inspecionar os modulos do processo")
            try:
                entry = MODULEENTRY32W()
                entry.dwSize = ctypes.sizeof(entry)
                ok = self._kernel.Module32FirstW(snap, ctypes.byref(entry))
                while ok:
                    if entry.szModule.lower() == expected_name.lower():
                        self.module_base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value or 0
                        break
                    ok = self._kernel.Module32NextW(snap, ctypes.byref(entry))
            finally:
                self._kernel.CloseHandle(snap)
            if not self.module_base:
                raise ObjectAPIError(f"Modulo {expected_name} nao encontrado no PID {pid}")
        except Exception:
            self.close()
            raise

    def read(self, address: int, size: int) -> bytes:
        if not 0x10000 <= address <= 0xFFFFFFFF or size <= 0 or size > 4096 or address + size > 0x100000000:
            raise ObjectAPIError("Endereco ou tamanho fora do intervalo x86 permitido")
        buffer = ctypes.create_string_buffer(size)
        count = ctypes.c_size_t()
        success = self._kernel.ReadProcessMemory(self._handle, ctypes.c_void_p(address),
                                                  buffer, size, ctypes.byref(count))
        if not success or count.value != size:
            raise ObjectAPIError(f"Falha leitura em 0x{address:08X} ({size} bytes)")
        return buffer.raw

    def close(self) -> None:
        handle = getattr(self, "_handle", None)
        if handle:
            self._kernel.CloseHandle(handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class HDObjectAPI:
    """Consultas pontuais, sem promessa de enumeracao global completa."""
    def __init__(self, reader: MemoryReader, root: Path | None = None, *,
                 allow_candidates: bool = False):
        self.reader = reader
        self.offsets = MappingOffsets(root or mapping_dir(), allow_candidates=allow_candidates)
        self.allow_candidates = allow_candidates

    def _read(self, addr: int, fmt: str):
        size = struct.calcsize(fmt)
        if addr < 0x10000 or addr + size > 0x100000000:
            raise ObjectAPIError("Ponteiro nulo/invalido")
        try:
            return struct.unpack("<" + fmt, self.reader.read(addr, size))[0]
        except (struct.error, OSError, KeyError) as exc:
            raise ObjectAPIError(f"Falha leitura em 0x{addr:08X}") from exc

    def _ptr(self, addr: int) -> int:
        return self._read(addr, "I")

    def _offset(self, root: str, name: str, *, candidate: bool = False) -> int:
        return self.offsets.get(root, name, candidate=candidate)

    def world(self) -> int:
        owner = self._ptr(self.reader.module_base + self._offset("RVA", "0x006F2C58"))
        return self._ptr(owner + self._offset("Owner", "0xC8"))

    def get_assigned_player(self) -> HDPlayer:
        world = self.world()
        slot = self._read(world + self._offset("World", "0x174"), "I")
        start = self._ptr(world + self._offset("World", "0x184"))
        end = self._ptr(world + self._offset("World", "0x188"))
        stride = 8
        if slot > 8 or not start or end < start or end - start > 9 * stride:
            raise ObjectAPIError("Tabela de jogadores inconsistente")
        addr = start + slot * stride
        if addr >= end:
            raise ObjectAPIError("Jogador local fora da tabela")
        player = self._ptr(addr + self._offset("PlayerEntry", "0x00"))
        if not player:
            raise ObjectAPIError("Ponteiro jogador local nulo")
        return HDPlayer(slot=slot, address=player)

    def get_object_by_id(self, object_id: int, *, include_candidate_position: bool = False) -> HDObject | None:
        if not 0 <= object_id <= 1000000:
            raise ValueError("Object ID fora de limite defensivo")
        table = self._ptr(self.world() + self._offset("World", "0x0E8"))
        addr = self._ptr(table + object_id * 4)
        if not addr:
            return None
        stored_id = self._read(addr + self._offset("Object", "0x08", candidate=True), "I")
        if stored_id != object_id:
            raise ObjectAPIError(f"ID inconsistente: solicitado={object_id}, encontrado={stored_id}")
        class_ptr = self._ptr(addr + self._offset("Object", "0x078"))
        class_id = (self._read(class_ptr + self._offset("Object78Target", "0x00C"), "I")
                    if class_ptr else None)
        type_ptr = self._ptr(addr + self._offset("Object", "0x0C", candidate=True))
        type_id = (self._read(type_ptr + self._offset("ObjectTypeTarget", "0x10"), "H")
                   if type_ptr else None)
        owner = self._ptr(addr + self._offset("Object", "0x10", candidate=True))
        position = None
        if include_candidate_position:
            if not self.allow_candidates:
                raise ObjectAPIError("Posicao candidata exige allow_candidates")
            # v9.13 nao promoveu estes campos ao catalogo: nao supor disponibilidade.
            position = None
        return HDObject(object_id, addr, class_id, type_id, owner or None, position,
                        ("Object+0x08", "Object+0x0C", "Object+0x10"))

    def get_objects_by_ids(self, ids: list[int], *, class_id: int | None = None,
                           genie_type_id: int | None = None) -> tuple[HDObject, ...]:
        if len(ids) > 10000:
            raise ValueError("Muitos IDs solicitados")
        result = []
        for object_id in dict.fromkeys(ids):
            obj = self.get_object_by_id(object_id)
            if obj is None:
                continue
            if class_id is not None and obj.class_id != class_id:
                continue
            if genie_type_id is not None and obj.genie_type_id != genie_type_id:
                continue
            result.append(obj)
        return tuple(result)

    def get_objects_by_class(self, class_id: int, ids: list[int]) -> tuple[HDObject, ...]:
        """Recebe IDs explicitos; enumeracao global nao esta comprovada."""
        return self.get_objects_by_ids(ids, class_id=class_id)
