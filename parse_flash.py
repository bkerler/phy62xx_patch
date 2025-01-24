#!/usr/bin/env python3
import sys
from io import BytesIO


def crc16_modbus(data: bytes, startval: int = 0xFFFF):
    data = bytearray(data)
    poly = 0xA001
    crc = startval
    for b in data:
        crc ^= (0xFF & b)
        for _ in range(0, 8):
            crc = ((crc >> 1) & 0xFFFF) ^ poly if (crc & 0x0001) else ((crc >> 1) & 0xFFFF)
    return crc & 0xFFFF


class ByteReader:
    def __init__(self, data: bytearray, flash_mem_base: int = 0):
        self.data = BytesIO(data)
        self.flash_mem_base = 0x11000000

    def seek(self, offset):
        self.data.seek(offset - self.flash_mem_base)

    def pos(self):
        return self.data.tell()

    def dword(self, pos: int = None, signed: bool = False):
        if pos:
            self.data.seek(pos - self.flash_mem_base)
        val = int.from_bytes(self.data.read(4), 'little') & 0xFFFFFFFF
        if signed:
            val -= 1 << 32
        return val

    def bytes(self, length: int, pos: int = None):
        if pos:
            self.data.seek(pos - self.flash_mem_base)
        return self.data.read(length)

    def short(self, pos: int = None, signed: bool = False):
        if pos:
            self.data.seek(pos - self.flash_mem_base)
        val = int.from_bytes(self.data.read(2), 'little') & 0xFFFF
        if signed:
            val -= 1 << 16
        return val

    def bytes2short(self, value: int, pos: int = None, signed: bool = False):
        if pos:
            self.data.seek(pos - self.flash_mem_base)
        if signed:
            value += 1 << 16
        self.data.write(int.to_bytes(value & 0xFFFF, 2, 'little'))

    def bytes2dword(self, value: int, pos: int = None, signed: bool = False):
        if pos:
            self.data.seek(pos - self.flash_mem_base)
        if signed:
            value += 1 << 32
        self.data.write(int.to_bytes(value & 0xFFFFFFFF, 4, 'little'))


def main():
    print()
    print("PHY62xx/ST17H66 FW Patcher (c) B.Kerler 2025")
    if len(sys.argv) < 2:
        print("Usage: ./parse_flash.py <flash file>")
        sys.exit(1)
    with open(sys.argv[1], "rb") as rf:
        flash_mem_base = 0x11000000
        sram_mem_base = 0x1FFF0000
        br = ByteReader(bytearray(rf.read()), flash_mem_base=flash_mem_base)
        print()
        print(f"Map FLASH function is at 0x1000A3C0 in ROM.")
        print(f"Verfiy FLASH function is at 0x11009C2E in FLASH")
        print(f"{hex(0x11001000)} => ADC_Calibration_Value: {hex(br.dword(pos=0x11001000))}")

        unk = br.dword(pos=0x11001824)
        unk2 = br.dword()

        mac = br.bytes(length=6, pos=0x11004000)
        vmac = ":".join(["%02X" % x for x in mac])

        print(f"{hex(0x11004000)} => MAC Address: {vmac}")
        ble_ad_names_offsets = []
        br.seek(flash_mem_base)
        dt = br.bytes(0x30000)
        pos = dt.find(b"multiConfigLink_status")
        if pos != -1:
            pos = pos - 0x15 + flash_mem_base
            ble_ad_name = br.bytes(length=0x15, pos=pos).rstrip(b"\x00")
            print(f"{hex(pos)} => BLE AD Name: \"{ble_ad_name.decode('utf-8')}\"")
            ble_ad_names_offsets.append(pos)
            idx = dt.find(ble_ad_name)
            if idx != -1:
                print(f"{hex(idx + flash_mem_base)} => BLE AD Name: \"{ble_ad_name.decode('utf-8')}\"")
                ble_ad_names_offsets.append(idx)
        print()
        print("Parsing Memory Mapping")

        class memmap_tbl:
            def __init__(self, br: ByteReader):
                self.pos = br.pos()
                self.src = br.dword()
                self.length = br.dword()
                self.dst = br.dword()
                crc = br.dword(signed=True)
                self.crc = crc

            def __repr__(self):
                v = f"{hex(self.pos + 0x11000000)} => Src:{hex(self.src)}, Dst:{hex(self.dst)}, Length:{hex(self.length)}"
                if self.crc != -1:
                    v += f", CRC: {hex(self.crc)}"
                else:
                    v += f", CRC: None"
                return v

        memmap_count = br.dword(pos=0x11002000)
        br.seek(0x11002100)
        for pos in range(0x11002100, 0x11002100 + memmap_count * 0x10, 0x10):
            print(memmap_tbl(br))

        print()
        print("Parsing CRC Table")

        class crc_tbl:
            def __init__(self, br: ByteReader):
                self.pos = br.pos()
                self.offset = br.dword()
                self.moffset = br.dword()
                self.length = br.dword()
                self.crc = br.dword()

            def __repr__(self):
                return f"{hex(self.pos + 0x11000000)} => Offset: {hex(self.offset)}, Mapped Offset: {hex(self.moffset)}, Length: {hex(self.length)}, CRC: {hex(self.crc)}"

        crc_count = br.dword(pos=0x11003000)
        br.seek(0x11003010)
        offset_table = {}
        for pos in range(0x11003010, 0x11003010 + crc_count * 0x10, 0x10):
            br.seek(pos)
            ct = crc_tbl(br)
            if 0x11000000 <= ct.moffset < 0x11080000:
                br.seek(ct.moffset)
                section_data = br.bytes(ct.length)
                calced_crc = crc16_modbus(section_data, startval=0)
                stored_crc = ct.crc
                info = str(ct)
                if stored_crc != calced_crc:
                    info += f"; Flash CRC mismatch. Real CRC: {hex(calced_crc)}"
                    offset_table[pos + 4 + 4 + 4] = int.to_bytes(calced_crc, 2, 'little')
                else:
                    info += "; Flash CRC valid"
                print(info)
            else:
                print(ct)
        print()
        if len(offset_table) > 0:
            ret = input("Shall we fix the CRC table? [y/n]")
            if ret == "y":
                rf.seek(0)
                data = bytearray(rf.read())
                for offset in offset_table:
                    foffset = offset-0x11000000
                    patch = offset_table[offset]
                    data[foffset:foffset + len(patch)] = patch
                with open(sys.argv[1] + ".patched", "wb") as wf:
                    wf.write(data)
                    print("Fixed flash was written to", sys.argv[1] + ".patched")
        # We seek to the memory map table with crc16 checksums
        #crc_ccitt_16 = calculate_crc_ccitt_16(data, crc_ccitt_table)
        #print(hex(crc_ccitt_16))


if __name__ == "__main__":
    main()
