# encoding: utf-8
import os
import pywintypes
from drive import get_fat32_partition, get_ntfs_partition
from drive.boot_sector.ebr import get_ext_partition_entries
from drive.fs.fat32.structs import FAT32BootSector
from drive.fs.ntfs.structs import NTFSBootSector
from drive.types import registry
from .keys import k_PartitionEntries, k_partition_type, k_ExtendedPartition, \
    k_first_byte_address
from .boot_sector import ClassicalMBR
from stream import WindowsPhysicalDriveStream


def discover_physical_drives(rng=range(16)):
    available_drives = []
    for i in rng:
        try:
            _ = WindowsPhysicalDriveStream(i)
            available_drives.append(i)
        except pywintypes.error:
            continue

    return available_drives


def get_partition_table(stream):
    type_ = stream.read(0xa)[3:]
    stream.seek(0, os.SEEK_SET)
    if b'NTFS' in type_:
        yield NTFSBootSector.parse_stream(stream)
    elif b'MSDOS' in type_:
        yield FAT32BootSector.parse_stream(stream)
    else:
        mbr = ClassicalMBR.parse_stream(stream)
        for entry in mbr[k_PartitionEntries]:
            if entry[k_partition_type] == k_ExtendedPartition:
                for sub_entry in get_ext_partition_entries(entry, stream):
                    yield sub_entry
            else:
                yield entry

    stream.seek(0, os.SEEK_SET)

def get_partition_obj(entry, stream, ui_handler=None):
    return registry[entry[k_partition_type]](entry, stream,
                                             ui_handler=ui_handler)
