Sync Claude Code (and Codex CLI) session transcripts into the llmwiki, then ingest the new ones into `wiki/`.

Usage: /wiki-sync [project-substring]

Steps (run in this order, report progress to the user):

1. **Convert new sessions to markdown** by running:
   ```bash
   python3 -m llmwiki sync $ARGUMENTS
   ```
   Capture the summary line (`N converted, M unchanged, K live, J filtered, X errors`).

2. **If `N == 0`**: report "wiki is already up to date" and stop. Don't run ingest.

3. **If `N > 0`**: for each newly written markdown file under `raw/sessions/`, follow the **Ingest Workflow** from `CLAUDE.md`. Process one project at a time. If there are more than 20 new files total, ask the user whether to process them all or a subset first.

4. **Append to `wiki/log.md`**:
   ```
   ## [YYYY-MM-DD] sync | <N> sessions across <M> projects
   ```

5. **Report** to the user:
   - How many sessions were converted
   - Which projects got updated
   - Which wiki pages were created or updated
   - Any contradictions flagged under `## Contradictions` on wiki pages
