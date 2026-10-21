"""Testes offline: leitor simulado, sem acesso ao jogo nem escrita."""
import tempfile
import unittest
from pathlib import Path
from aoe2hdcontrol.object_api import HDObjectAPI, ObjectAPIError, MappingOffsets

ROWS = [
("RVA","0x006F2C58","historico_validado"),("Owner","0xC8","historico_validado"),
("World","0x174","historico_validado"),("World","0x184","historico_validado"),
("World","0x188","historico_validado"),("World","0x0E8","validado"),
("PlayerEntry","0x00","historico_validado"),("Object","0x08","hipotese"),
("Object","0x078","validado"),("Object78Target","0x00C","validado"),
("Object","0x0C","hipotese"),("ObjectTypeTarget","0x10","validado"),
("Object","0x10","hipotese"),
]

class FakeReader:
    module_base = 0x400000
    def __init__(self):
        self.memory = {}
    def put(self, address, fmt, value):
        import struct
        for i, byte in enumerate(struct.pack("<" + fmt, value)):
            self.memory[address+i] = byte
    def read(self, address, size):
        return bytes(self.memory[address+i] for i in range(size))

class ObjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        file = root / "dados/catalogos/estruturas_memoria.csv"
        file.parent.mkdir(parents=True)
        import csv
        with file.open("w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp)
            w.writerow(["raiz","offset_ou_endereco","descricao","tipo","status","origem"])
            for base,off,status in ROWS:
                w.writerow([base,off,"teste","ptr32",status,"test"])
        self.root = root
        self.mem = FakeReader()
        self.mem.put(0x400000+0x006F2C58,"I",0x100000)
        self.mem.put(0x100000+0xC8,"I",0x110000)
        self.mem.put(0x110000+0x174,"I",1)
        self.mem.put(0x110000+0x184,"I",0x120000)
        self.mem.put(0x110000+0x188,"I",0x120018)
        self.mem.put(0x120008,"I",0x130000)
        self.mem.put(0x110000+0x0E8,"I",0x140000)
        self.mem.put(0x140000+2188*4,"I",0x150000)
        self.mem.put(0x150000+0x08,"I",2188)
        self.mem.put(0x150000+0x078,"I",0x160000)
        self.mem.put(0x160000+0x0C,"I",4)
        self.mem.put(0x150000+0x0C,"I",0x170000)
        self.mem.put(0x170000+0x10,"H",83)
        self.mem.put(0x150000+0x10,"I",0x130000)

    def test_candidate_gating(self):
        api=HDObjectAPI(self.mem,self.root)
        self.assertEqual(api.get_assigned_player().slot,1)
        with self.assertRaises(ObjectAPIError):
            api.get_object_by_id(2188)

    def test_object_class_type_owner_and_filter(self):
        api=HDObjectAPI(self.mem,self.root,allow_candidates=True)
        obj=api.get_object_by_id(2188)
        self.assertEqual((obj.object_id,obj.class_id,obj.genie_type_id,obj.owner_address),
                         (2188,4,83,0x130000))
        self.assertIsNone(obj.position)
        self.assertEqual(len(api.get_objects_by_class(4,[2188])),1)
        self.assertEqual(api.get_objects_by_class(6,[2188]),())
        self.assertEqual(api.get_objects_by_ids([2188,2188]),(obj,))

    def test_missing_object(self):
        self.mem.put(0x140000+2189*4,"I",0)
        api=HDObjectAPI(self.mem,self.root,allow_candidates=True)
        self.assertIsNone(api.get_object_by_id(2189))

    def test_mismatched_id_rejected(self):
        self.mem.put(0x150000+0x08,"I",42)
        with self.assertRaises(ObjectAPIError):
            HDObjectAPI(self.mem,self.root,allow_candidates=True).get_object_by_id(2188)

    def test_missing_mapping_or_invalid_id(self):
        api=HDObjectAPI(self.mem,self.root,allow_candidates=True)
        with self.assertRaises(ValueError):
            api.get_object_by_id(-1)
        with self.assertRaises(ObjectAPIError):
            api.get_objects_by_ids([2188,2189],class_id=4)

if __name__ == "__main__":
    unittest.main()
