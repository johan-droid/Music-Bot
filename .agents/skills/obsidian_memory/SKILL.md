---
name: obsidian_memory
description: Sync, read, and write persistent project state and architectural memory in Obsidian Vault (/home/ashutoshsahoo/Downloads/Claude memory/). Triggered automatically on task start and task completion.
---

# Obsidian Memory Skill

This skill governs reading and persisting codebase memory to the user's Obsidian Vault directory at `/home/ashutoshsahoo/Downloads/Claude memory/`.

## When to Trigger
- **At Start of Job**: Read all Obsidian memory documents to recall architectural guarantees, file maps, and progress history.
- **At End of Job**: Append/update progress entries and architectural notes in the vault.

## Vault Files Structure
- `/home/ashutoshsahoo/Downloads/Claude memory/Brock_Music_Bot_Architecture.md`: Core system architecture diagram, invariants, and file mapping.
- `/home/ashutoshsahoo/Downloads/Claude memory/Brock_Music_Bot_Progress.md`: Feature milestone progress table.
- `/home/ashutoshsahoo/Downloads/Claude memory/SOUL_MEMORY.md`: Identity and persistent harddrive directives.

## Automated Sync Script
Execute the helper script to verify vault integrity or append entries:
```bash
python3 .agents/skills/obsidian_memory/scripts/sync_memory.py
```
