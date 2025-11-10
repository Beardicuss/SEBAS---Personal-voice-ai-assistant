# -*- coding: utf-8 -*-
"""
Quick test for integrations.storage_manager
"""

from integrations.storage_manager import StorageManager
import pprint

if __name__ == "__main__":
    print("=== StorageManager Test ===")
    sm = StorageManager()

    print("\n[1] Disk Partitions:")
    pprint.pprint(sm.list_disk_partitions())

    print("\n[2] Disk Info:")
    pprint.pprint(sm.get_disk_info())

    print("\n[3] Volume Info:")
    pprint.pprint(sm.get_volume_info())

    print("\n[4] Disk Usage (All):")
    pprint.pprint(sm.get_disk_usage())

    print("\n[5] BitLocker Status:")
    pprint.pprint(sm.get_bitlocker_status())

    print("\n[6] Storage Spaces:")
    pprint.pprint(sm.get_storage_spaces_status())

    print("\n=== Done ===")
