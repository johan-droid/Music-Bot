#!/usr/bin/env python3
"""
Obsidian Memory Sync Utility for Brock Music Bot.
Reads and updates persistent project memory in /home/ashutoshsahoo/Downloads/Claude memory/.
"""

import os
import sys

VAULT_DIR = "/home/ashutoshsahoo/Downloads/Claude memory"
ARCH_FILE = os.path.join(VAULT_DIR, "Brock_Music_Bot_Architecture.md")
PROGRESS_FILE = os.path.join(VAULT_DIR, "Brock_Music_Bot_Progress.md")
SOUL_FILE = os.path.join(VAULT_DIR, "SOUL_MEMORY.md")

def read_memory():
    print(f"=== Reading Obsidian Memory Vault from {VAULT_DIR} ===")
    for filepath in [ARCH_FILE, PROGRESS_FILE, SOUL_FILE]:
        if os.path.exists(filepath):
            print(f"\n--- {os.path.basename(filepath)} ---")
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                print("".join(lines[:20]))
                if len(lines) > 20:
                    print(f"... [{len(lines)-20} more lines]")
        else:
            print(f"Warning: {filepath} not found.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--read":
        read_memory()
    else:
        read_memory()

if __name__ == "__main__":
    main()
