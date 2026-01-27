# Scribe Skill — Example User Flows

This document captures example user flows to exercise all corners of the scribe skill.

---

## Initialization Flows

### 1. First use in empty directory
> User enters an empty directory, says "hey scribe, I'm starting an analysis to figure out why Q4 forecasts are off by 15%"
> 
> Claude creates `.scribe/`, proposes first entry capturing the goal, user confirms, entry is written.

### 2. First use in existing project (johnny-come-lately)
> User enters a project with existing code but no `.scribe/`, says "scribe, log this"
> 
> Claude notices no scribe history, asks "What's this project about and where do things stand?", creates initial entry capturing current state.

### 3. First use with deep dive request
> User says "scribe, look around and get oriented before we start logging"
> 
> Claude explores README, git log, file structure, then proposes an initial entry summarizing what it found.

---

## Logging Flows

### 4. Basic logging after work
> User has been debugging nulls for 30 minutes, says "scribe, log this"
> 
> Claude proposes entry with title, narrative, files touched, status. User says "looks good", entry is written.

### 5. Logging with user correction
> User says "scribe, log this"
> 
> Claude proposes entry mentioning null handling. User says "no, the issue was timezone handling not nulls". Claude revises and re-proposes.

### 6. Logging with user annotation
> User says "scribe — this was a dead end, log it"
> 
> Claude incorporates the "dead end" judgment into the narrative and status.

### 7. Logging a concern/question to explore
> User says "/scribe I'm worried that duplicates are tricking me in this dataset"
> 
> Claude proposes entry capturing the concern, then proceeds to help investigate.

### 8. Explicit entry request with slash command
> User says "/scribe make an entry"
> 
> Claude assesses the conversation since the last entry, proposes a draft covering what was worked on, files touched, and current status. User confirms or edits.

### 9. Quick log bypass
> User says "scribe, quick log: fixed the off-by-one error in pagination"
> 
> Claude writes the entry directly without proposing, then shows brief confirmation.

---

## Archiving Flows

### 10. Snapshot before risky change
> User says "scribe, snapshot the ETL script before I refactor"
> 
> Claude proposes entry, offers `etl.py` as archive option (checked), user confirms, file is archived and linked in entry.

### 11. Snapshot of working version
> User says "scribe, save clustering.ipynb — this is the first version that actually works"
> 
> Claude proposes entry celebrating the milestone, archives the file with description "First working version".

### 12. Snapshot files from another skill directory
> User says "scribe, save the viz plot we just made"
> 
> Claude archives `.viz/plots/revenue_forecast.png` to `.scribe/assets/`, entry references it.

### 13. Multiple files in one snapshot
> User says "scribe, snapshot the notebook and the config"
> 
> Claude archives both `clustering.ipynb` and `config.yaml` with the same entry ID.

---

## Restoring Flows

### 14. Restore for comparison
> User says "scribe, restore the notebook from before the refactor so I can compare"
> 
> Claude searches logs, finds asset and original path `src/analysis/clustering.ipynb`, runs `assets.py get ... --dest src/analysis/`, file appears as `src/analysis/_2026-01-23-14-35-clustering.ipynb` — next to current version.

### 15. Restore and run
> User says "scribe, run the ETL script we saved last Tuesday"
> 
> Claude finds the asset, restores it, then executes it.

### 16. List assets with filter
> User says "scribe, what snapshots do we have of the notebook?"
> 
> Claude runs `assets.py list clustering`, shows matching assets.

### 17. Restore fails — destination exists
> User says "scribe, restore the notebook from yesterday"
> 
> Script fails with "already exists". Claude tells user and offers to delete the existing file or suggests they rename/remove it first.

---

## Querying Flows

### 18. Time-based query — today
> User says "scribe, what did we do today?"
> 
> Claude reads today's log file, summarizes the entries.

### 19. Time-based query — last week
> User says "scribe, summarize last week"
> 
> Claude reads the last 7 day files, synthesizes a summary.

### 20. Topic-based query
> User says "scribe, what did we try for the null problem?"
> 
> Claude greps for "null" across logs, reads matching files, answers.

### 21. Pick up where we left off
> User starts new session, says "scribe, where did we leave off?"
> 
> Claude reads most recent entry, sees Status line, tells user "Last session you fixed null handling and kicked off validation. Ready to check results?"

### 22. What's still unresolved?
> User says "scribe, what's still unresolved?"
> 
> Claude searches logs for open threads, Status lines with questions, summarizes outstanding items.

### 23. Query finds nothing
> User says "scribe, what did we try for the kafka issue?"
> 
> Claude greps logs, finds no matches. Responds "I don't see any entries about kafka in the logs."

### 24. Ask about specific archived file context
> User says "scribe, what's the context for the 2026-01-20-09-15-pipeline.py snapshot?"
> 
> Claude extracts entry ID, searches logs, finds and explains why it was archived.

---

## Related / Follow-up Entry Flows

### 25. Simple addendum to previous entry
> User says "scribe, add to the last entry — I forgot to mention we also updated the tests"
> 
> Claude creates a follow-up entry with **Related** linking to the previous entry, narrative mentions the tests.

### 26. Closing a thread — dead end
> User says "scribe, the timezone hypothesis was a red herring. Log that and link back to those entries."
> 
> Claude creates entry explaining timezones were a dead end, **Related** lists the 3 timezone investigation entries with their titles.

### 27. Closing a thread — success
> User says "scribe, we finally figured out the revenue discrepancy. It connects back to the null handling and the migration issues."
> 
> Claude creates entry with the resolution, **Related** links both the null handling and migration investigation entries.

### 28. Synthesis entry connecting multiple threads
> User says "scribe, I realized the timezone issue, the null issue, and the negative values are all symptoms of the same migration bug"
> 
> Claude creates entry explaining the connection, **Related** lists all three threads.

### 29. Returning to old work
> User says "scribe, we're picking up the clustering work from two weeks ago"
> 
> Claude creates entry noting the return to clustering, **Related** links to the last clustering entry from two weeks ago with its title.

### 30. Building on specific previous approach
> User says "scribe, we're trying the SMOTE approach again but with different parameters — related to when we tried it before"
> 
> Claude creates entry about the new SMOTE attempt, **Related** links to the original SMOTE entry, narrative explains what's different this time.

### 31. Marking multiple entries as superseded
> User says "scribe, the new ETL pipeline replaces everything we did in the old approach. Link back to all those entries."
> 
> Claude creates entry about the new pipeline, **Related** lists all the old approach entries, narrative explains they're superseded.

### 32. Following up on an open question
> User says "scribe, remember when we noted we should check if the issue affects historical data? We checked — it doesn't."
> 
> Claude finds the entry with the open question, creates follow-up entry with the answer, **Related** links back.

### 33. Correcting a previous conclusion
> User says "scribe, I was wrong in yesterday's entry about the root cause. Log the correction."
> 
> Claude creates entry with the corrected understanding, **Related** links to yesterday's entry, narrative explains what was wrong and what's actually true.

---

## Edge Cases

### 34. Multiple entries in same minute (collision handling)
> User logs two entries at 14:35
> 
> First entry gets ID `2026-01-23-14-35`, second gets `2026-01-23-14-35-02`.

### 35. Validation catches missing asset
> Claude writes entry referencing archived file but `assets.py save` fails
> 
> Validation runs, reports "references X but file not found", Claude fixes before continuing.

### 36. New session with no context, user just says "log this"
> User starts fresh session, says "scribe, log this" with no prior conversation
> 
> Claude checks recent logs and file mod-times, asks "I see these files changed since the last entry — what should I capture?"

### 37. Validation finds orphaned asset
> User manually deletes an entry from the log but leaves the asset file
> 
> Validation reports "Orphaned asset: 2026-01-23-14-35-old.py — no entry references it".

### 38. User references scribe naturally mid-conversation
> User says "okay that worked — scribe, we should remember this approach"
> 
> Claude recognizes this as a logging request, proposes entry capturing the successful approach.

### 39. Minimal entry — just a note
> User says "scribe, just note that the client approved the approach"
> 
> Claude proposes a short entry with no Files touched section, just the note and status.

### 40. User declines snapshot suggestion
> Claude proposes entry and suggests snapshotting `model.py`. User says "no snapshot, just log it"
> 
> Claude writes entry without archiving any files.

### 41. Related entry where original is hard to find
> User says "scribe, this connects to something we did a while back about caching — can you find it?"
> 
> Claude greps for "caching", finds the entry, confirms with user, then creates new entry with **Related** linking to it.

### 42. Long gap between sessions with related work
> User returns after a month, says "scribe, I'm revisiting the clustering analysis from last month"
> 
> Claude finds the old clustering entries, creates new entry marking the return, **Related** links to the most relevant previous entry with its title.

### 43. Chain of related entries
> User has been iterating on an approach across 4 entries, says "scribe, log this next attempt"
> 
> Claude creates entry with **Related** pointing to the immediately previous entry in the chain. The chain is traceable by following Related links backward.

### 44. Querying entries related to a specific entry
> User says "scribe, show me everything related to the entry about feature engineering"
> 
> Claude finds the feature engineering entry, then searches for any entries with that ID in their **Related** section, presents the thread.

### 45. Branching — trying parallel approaches
> User says "scribe, we're going to try two different approaches from here — one using random forest, one using gradient boosting"
> 
> Claude creates two entries, both with **Related** pointing to the current state entry (the fork point). Each branch continues independently, traceable back to where they diverged.

### 46. Merging — parallel branches converge
> User says "scribe, both the random forest and gradient boosting approaches led us to the same conclusion — the feature set is the problem"
> 
> Claude creates a synthesis entry explaining the convergence, **Related** lists both branch entries, narrative explains that independent approaches confirmed the same finding.

---

## Error Recovery Flows (edit-latest)

### 47. Validation fails — user aborts entry
> Claude writes entry with **Archived** section, but `assets.py save` fails (file not found)
> 
> Validation reports broken reference. User says "forget it, delete the entry."
> 
> Claude runs `entry.py edit-latest delete`, which removes the entry and any partial assets. Validation passes.

### 48. Validation fails — user fixes by rearchiving
> Claude writes entry referencing `analysis.py`, but archived wrong file by mistake
> 
> Validation reports missing asset. User says "oops, archive the right file."
> 
> Claude runs `entry.py edit-latest rearchive analysis.py`. Validation passes.

### 49. User wants to correct the last entry's content
> User says "wait, I said null handling but I meant timezone handling"
> 
> Claude runs `entry.py edit-latest show` to see current entry, then `entry.py edit-latest replace` with corrected content. Entry ID stays the same, assets stay linked.

### 50. User wants to remove archives but keep the entry
> User says "actually don't archive those files, but keep the log entry"
> 
> Claude runs `entry.py edit-latest unarchive` to delete the assets, then edits the entry to remove the **Archived** section using `edit-latest replace`.

### 51. Check what the latest entry looks like
> User says "scribe, show me what you just logged"
> 
> Claude runs `entry.py edit-latest show` and displays the entry content.

### 52. Validation fails with orphaned asset — cleanup
> Claude archived a file but then the entry write failed
> 
> Validation reports orphaned asset. Claude runs `entry.py edit-latest unarchive` (if entry exists) or manually deletes the orphan from `.scribe/assets/`.

### 53. Quick log was too sparse — user wants to expand it
> User said "quick log: fixed bug" but now wants more detail
> 
> Claude runs `entry.py edit-latest replace` with a fuller entry. The entry ID is preserved.

### 54. User changes mind immediately after logging
> User confirms entry, Claude writes it, then user says "actually no, delete that"
> 
> Claude runs `entry.py edit-latest delete`. Entry and any assets are removed.

---

## Coverage Check: Related Mechanism

The **Related** mechanism is exercised in the following ways:

| Use Case | Related Usage |
|----------|---------------|
| 25 | Simple addendum — single backward link |
| 26 | Closing dead end — multiple backward links |
| 27 | Closing success — multiple backward links |
| 28 | Synthesis — connecting multiple threads |
| 29 | Returning to old work — single backward link across time gap |
| 30 | Building on previous approach — single backward link with context |
| 31 | Superseding old work — multiple backward links |
| 32 | Following up on open question — single backward link |
| 33 | Correcting previous conclusion — single backward link |
| 41 | Finding and linking to vaguely remembered entry |
| 42 | Long time gap — rediscovering old work |
| 43 | Chain of iterations — following links backward |
| 44 | Forward query — finding entries that reference a given entry |
| 45 | Branching — multiple entries link back to same fork point |
| 46 | Merging — synthesis entry links to multiple parallel branches |

**Covered scenarios:**
- Single related entry
- Multiple related entries
- Addendum / amendment
- Closing threads (dead end)
- Closing threads (success)
- Synthesis / connection discovery
- Returning to old work
- Iterating on an approach
- Correcting mistakes
- Superseding old work
- Finding related entries by searching **Related** sections
- Branching into parallel approaches
- Merging parallel branches back together

---

## Coverage Check: edit-latest Mechanism

The **edit-latest** commands are exercised in the following ways:

| Use Case | edit-latest Usage |
|----------|-------------------|
| 47 | `delete` — abort entry after validation failure |
| 48 | `rearchive` — fix wrong file archived |
| 49 | `replace` — correct entry content |
| 50 | `unarchive` + `replace` — remove archives, keep entry |
| 51 | `show` — display latest entry |
| 52 | `unarchive` — cleanup orphaned assets |
| 53 | `replace` — expand a sparse quick log |
| 54 | `delete` — immediate undo after logging |

**Covered scenarios:**
- Aborting a broken entry
- Fixing archive mistakes
- Correcting entry content
- Removing archives while keeping entry
- Viewing latest entry
- Cleaning up orphans
- Expanding sparse entries
- Immediate undo

---

## Deep Directory Archive/Restore Flows

### 55. Archive file from deep directory
> User says "scribe, snapshot the transform script before I refactor"
> 
> File is at `src/pipelines/etl/transform.py`. Claude writes entry with:
> ```
> **Archived:**
> - `src/pipelines/etl/transform.py` → [`2026-01-24-14-35-transform.py`](assets/2026-01-24-14-35-transform.py) — Before refactor
> ```
> The original path is preserved in the entry.

### 56. Restore file to original directory
> User says "scribe, restore the transform script from before the refactor"
> 
> Claude reads entry, finds original path `src/pipelines/etl/transform.py`, runs:
> ```bash
> python assets.py get 2026-01-24-14-35-transform.py --dest src/pipelines/etl/
> ```
> File restored to `src/pipelines/etl/_2026-01-24-14-35-transform.py` — next to current version for comparison.

### 57. Restore when two files had same name in different directories
> User archived both `src/etl/utils.py` and `tests/etl/utils.py` in different entries.
> User says "scribe, restore the utils.py from the ETL source"
> 
> Claude searches entries, finds the one with original path `src/etl/utils.py`, restores to that directory. The other `utils.py` (from tests/) is untouched.

### 58. Compare restored file with current version
> User says "scribe, restore yesterday's config and show me the diff"
> 
> Claude reads entry, finds original path `config/settings.yaml`, restores to `config/_2026-01-23-14-35-settings.yaml`, then runs:
> ```bash
> diff config/settings.yaml config/_2026-01-23-14-35-settings.yaml
> ```
> Files are side-by-side in same directory, easy to compare.

---

## Coverage Check: Deep Directory Handling

| Use Case | Coverage |
|----------|----------|
| 55 | Archive preserves original path in entry |
| 56 | Restore uses original directory via --dest |
| 57 | Same filename in different directories distinguished by entry path |
| 58 | Restored file next to current for easy comparison |

**Covered scenarios:**
- Deep directory paths preserved
- Restore to original location
- Disambiguation by path
- Side-by-side comparison
