# Agent Core Rules — Obsidian Memory Protocols

> **Mandatory Rule for All AI Coding Assistants**: Always sync with Obsidian Memory (`/home/ashutoshsahoo/Downloads/Claude memory/`) at the start and end of every task.

---

## 1. MANDATORY STARTUP STEP: Read Obsidian Vault Memory

Before performing ANY research, code search, plan creation, or editing, you MUST view the persistent memory artifacts in the Obsidian Vault:

1. **[Brock_Music_Bot_Architecture.md](file:///home/ashutoshsahoo/Downloads/Claude%20memory/Brock_Music_Bot_Architecture.md)**: Read for architectural guarantees, file layout, and component boundaries.
2. **[Brock_Music_Bot_Progress.md](file:///home/ashutoshsahoo/Downloads/Claude%20memory/Brock_Music_Bot_Progress.md)**: Read for feature status, completed milestones, and recent technical decisions.
3. **[SOUL_MEMORY.md](file:///home/ashutoshsahoo/Downloads/Claude%20memory/SOUL_MEMORY.md)**: Read for workspace identity and rules.

---

## 2. MANDATORY FINAL STEP: Update Obsidian Vault Memory

After completing any task, bug fix, refactoring, or feature addition (and verifying clean `cargo test`), you MUST update the Obsidian Vault memory files:

1. Update **[Brock_Music_Bot_Progress.md](file:///home/ashutoshsahoo/Downloads/Claude%20memory/Brock_Music_Bot_Progress.md)** with:
   - Feature/Milestone name
   - Target component
   - Completion status (`✅ Completed`)
   - Current date/timestamp
   - Concise technical details of changes made
2. Update **[Brock_Music_Bot_Architecture.md](file:///home/ashutoshsahoo/Downloads/Claude%20memory/Brock_Music_Bot_Architecture.md)** if core invariants or component structures changed.
