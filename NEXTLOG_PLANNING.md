# NextLog - Planning Document

> Last Updated: 2026-04-07

## System Overview

NextLog is an agentic vault system that processes raw information from various sources (X bookmarks, YouTube links, Obsidian web clips) and synthesizes them into structured, interconnected notes.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Inbox (Raw)                             │
│  - X Bookmarks                                                  │
│  - YouTube Links                                                │
│  - Obsidian Web Clips                                          │
│  - Other sources                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Processing Layer                             │
│  - URL detection & routing                                     │
│  - Content extraction (X API, YouTube transcript, etc.)        │
│  - Metadata + status tracking                                   │
│  - Markdown generation                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Synthesis Layer                              │
│  - Topic identification                                         │
│  - Note generation                                              │
│  - Backlink management                                          │
│  - Update on new information                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Output Vault                                 │
│  - inbox/           (processed raw content)                     │
│  - synthesis/       (topic-organized notes)                     │
│  - ref/             (ultra-refined, future)                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decisions (Finalized)

### Inbox
- [x] **Q1**: Folder-based inbox (raw dump/queue)
- [x] **Q1b**: Also supports API pulls (X bookmarks via existing processor.js)

### Processing Layer
- [x] **Q2**: Reuse existing `processor.js` for X bookmarks
- [x] **Q3**: Use `yt-dlp` CLI for YouTube transcripts
- [x] **Q4**: Obsidian Web Clips - just index, don't re-process
- [x] **Q5**: Frontmatter in each MD file with status (pending, processed, failed)

---

## Synthesis Layer Questions

### Topic Identification
- [ ] **Q6**: How to identify topics?
  - Manual tags from user?
  - LLM-based extraction from content?
  - Hybrid (LLM suggests, user confirms)?
  LLM should ideally be able to do it themselves. 

### Note Structure
- [ ] **Q7**: How to organize synthesized notes?
  - One note per topic? (e.g., `synthesis/ai-alignment.md`)
  - Folder per topic with multiple notes?
  - Dataview-style queries?
  Folder per meta topic with notes per topic inside them internally. 

### Update Strategy
- [ ] **Q8**: When new info arrives for existing topic:
  - Append to existing note?
  - Create new note with timestamp?
  - Rewrite entirely with context?
  - Create a "living document" that auto-merges?
  rewrite entirely if needed BUT keep a log in each note on what decision/reference logs were made and reference should also be ensured to be retained. 

### Backlinks
- [ ] **Q9**: How to maintain backlinks?
  - Obsidian's native backlinks?
  - Explicit `[[wikilinks]]` in notes?
  - Separate backlink index?
  wikilinks are good option with an option for the user to only use it in obsidian native links.

---

## Decisions (Finalized)

### Synthesis Layer
- [x] **Q6**: Topic Identification - LLM-based (autonomous)
- [x] **Q7**: Note Structure - Folder per meta topic, notes inside
- [x] **Q8**: Update Strategy - Rewrite entirely if needed, with decision logs + references retained
- [x] **Q9**: Backlinks - Wikilinks with option for Obsidian native links

---

## Next Round: Tech Stack & CLI Design

### Tech Stack
- [ ] **Q10**: What language?
  - JavaScript/TypeScript (extend existing smaug)?
  - Python (for ML/LLM integration)?
  - Go (single binary, fast)?
  I am ok with go or python as it is easy to integrate LLMs. 

### CLI Commands
- [ ] **Q11**: What should CLI commands look like?
  - `nextlog process` - process inbox
  - `nextlog synthesize` - create structured notes
  - `nextlog sync` - run both?
  - Other commands?
  we need a command which can be added to a cron job to fetch bookmarks from x/twitter also. 

### Cron/Scheduling
- [ ] **Q12**: How to trigger processing?
  - Manual CLI only?
  - Cron job?
  - File watcher (inotify/fsevents)?
  - All of the above? 
  CLI / CRON only. 

---

## Decisions (Finalized)

### Tech Stack
- [x] **Q10**: Python (chosen - same repo, reusing processor.js)
- [x] **Q11**: CLI with cron-friendly fetch command for X bookmarks
- [x] **Q12**: CLI / Cron only (no file watcher)

---

## Next Round: LLM Integration & Folder Structure

### LLM Integration
- [ ] **Q13**: Which LLM provider?
  - OpenAI (GPT-4)?
  - Anthropic (Claude)?
  - OpenRouter (many models)?
  - Ollama (local)?
  Openrouter to start. 

### Config File
- [ ] **Q14**: How to configure?
  - YAML file?
  - JSON file?
  - TOML?
  - Environment variables?
  JSON/YAML whatever is easy to maintain for a CLI based tool. 

### Folder Structure
- [ ] **Q15**: What should the output structure look like?
```
nextlog/
  inbox/
    raw/           # pending items
    processed/    # extracted content
  synthesis/
    meta-topic-1/
      note-1.md
      note-2.md
    meta-topic-2/
  config.yaml
```
Yeah this looks fine to start. 

### Error Handling
- [ ] **Q16**: How to handle failures?
  - Retry queue?
  - Dead letter folder?
  - Log only? 
  Retry queue, along with CLI showcasing what is the possible resolution. 

---

## New: Knowledge Graph & Search (QMD Integration)

Based on your reference to [qmd](https://github.com/tobi/qmd):

### QMD Integration
- [ ] **Q17**: Should NextLog integrate QMD for search?
  - Local hybrid search (BM25 + vector + LLM rerank)
  - All local, no cloud dependencies
  - MCP server for AI agent integration
  Local QMD search should be there with option for LLM rerank which user can enable. 

### Knowledge Graph
- [ ] **Q18**: How to build the knowledge graph?
  - Auto-generate from wikilinks in synthesis notes?
  - LLM extracts entities + relationships?
  - Both?
  Both. 

### Search UI
- [ ] **Q19**: How should users search?
  - CLI only (`nextlog search "query"`)?
  - QMD CLI directly?
  - Obsidian native search (already built-in)?
  - All of the above?
  USer should be able to refer using a skill by invoking it into his LLM for now. Query is also necessary for synthesis purposes to be able to generate deeper linking between notes between cross topics also. 

---

## Decisions (Finalized)

### LLM & Config
- [x] **Q13**: LLM Provider - OpenRouter (to start)
- [x] **Q14**: Config File - JSON/YAML (whatever is easy)
- [x] **Q15**: Folder Structure - as proposed
- [x] **Q16**: Error Handling - Retry queue + CLI resolution hints

### Search & Graph
- [x] **Q17**: QMD Integration - Yes, with optional LLM rerank
- [x] **Q18**: Knowledge Graph - Both (wikilinks + LLM extraction)
- [x] **Q19**: Search UI - Skill-based for LLM + CLI for synthesis queries

---

## Next Round: Synthesis Prompts & Data Flow

### Synthesis Prompt Design
- [ ] **Q20**: What should the synthesis prompt look like?
  - Give raw content + existing notes → LLM decides structure
  - Pre-defined templates per topic type?
  - User can customize prompts?
  Give raw content + existing notes → LLM creates structure but frontmatter should be specific to a template. 

### Cross-Topic Linking
- [ ] **Q21**: How to link related topics?
  - LLM detects cross-topic relevance during synthesis?
  - Separate cross-reference generation pass?
  - Both?
  LLM detects cross-topic relevance during synthesis because we will have qmd searching also avaialble. 

### Source Attribution
- [ ] **Q22**: How to attribute sources in synthesized notes?
  - Inline links to source MD files?
  - Footnotes/endnotes?
  - Backlinks section at bottom? 
  Inline links to source MD files but only if the links are continously maintained. 

---

## Decisions (Finalized)

### Synthesis Details
- [x] **Q20**: Prompts - Raw content + existing notes → LLM decides, but frontmatter follows template
- [x] **Q21**: Cross-topic linking - LLM detects during synthesis (with QMD search available)
- [x] **Q22**: Source attribution - Inline links (maintained continuously)

---

## Next Round: Implementation Details

### Metadata Templates
- [ ] **Q23**: What frontmatter fields should every note have?
  - `created:`, `updated:`, `topics:`, `sources:`, `status:`?
  - Any others?
For processed we should have status if synthesized or not. For synthesized we dont need a status per se. 

### State Tracking
- [ ] **Q24**: How to track overall system state?
  - JSON state file?
  - SQLite?
  - YAML?
  What is the meaning of this? States can be maintained in same qmd can we not? 

### Incremental vs Full Sync
- [ ] **Q25**: Synthesis mode?
  - Always process only new items (incremental)?
  - Option to do full rebuild?
  - Both?
  Both. 

---

## Decisions (Finalized)

### Implementation
- [x] **Q23**: Frontmatter - processed notes have status (synthesized or not), synthesized notes don't need status
- [x] **Q24**: State Tracking - Use QMD's built-in collections/context (no separate state file needed)
- [x] **Q25**: Sync Mode - Both incremental and full rebuild options

---

## Next Round: CLI Commands & Naming

### CLI Command Naming
- [ ] **Q26**: What exact commands?
  - `nextlog fetch` - fetch from X
  - `nextlog process` - extract content
  - `nextlog synthesize` - create notes
  - `nextlog search` - search via QMD
  - `nextlog run` - run all
  - Any additions?

  For now it is fine. 

### CLI Flags
- [ ] **Q27**: Common flags needed?
  - `--config` - config file path
  - `--verbose` - debug output
  - `--dry-run` - don't write files
  - Others? 

  for now it is ok. We will add as we proceed. 

---

## Decisions (Finalized)

### CLI
- [x] **Q26**: Commands - fetch, process, synthesize, search, run (as proposed)
- [x] **Q27**: Flags - basic set, add more as needed

---

## Final Architecture (Complete)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NextLog                                        │
│                    Agentic Vault System                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐     ┌─────────────────────────┐
│        INBOX            │     │        SOURCES           │
│   (raw data dump)      │     │  - X/Twitter Bookmarks   │
│                         │     │  - YouTube Links        │
│  - inbox/raw/           │     │  - Obsidian Web Clips    │
│    (pending items)      │     │  - Manual additions     │
│                         │     │  - API pulls            │
│  - inbox/processed/     │     │                         │
│    (extracted content) │     │                         │
└───────────┬─────────────┘     └─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROCESSING LAYER                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  URL Detection & Routing                                             │  │
│  │   - X articles → bird CLI → extract content                         │  │
│  │   - YouTube → yt-dlp → get transcript                               │  │
│  │   - Obsidian clips → index only (no reprocessing)                  │  │
│  │   - Other URLs → fetch & extract                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Metadata + Status Tracking (frontmatter)                          │  │
│  │   - status: pending | processed | failed                           │  │
│  │   - source: x-bookmark | youtube | obsidian-clip | manual          │  │
│  │   - processedAt: timestamp                                          │  │
│  │   - synthesized: true | false                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYNTHESIS LAYER                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Topic Identification (LLM-based)                                    │  │
│  │   - LLM analyzes content, auto-assigns topics                       │  │
│  │   - Creates folder structure: synthesis/<meta-topic>/              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Note Generation                                                     │  │
│  │   - Frontmatter template: created, updated, topics, sources        │  │
│  │   - Decision log maintained in each note                           │  │
│  │   - Rewrite entirely if needed, retain references                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Cross-Topic Linking                                                │  │
│  │   - LLM detects relevance during synthesis                        │  │
│  │   - Uses QMD search for context                                     │  │
│  │   - Wikilinks [[note-name]] for connections                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Source Attribution                                                 │  │
│  │   - Inline links to source MD files                                 │  │
│  │   - Continuously maintained                                         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OUTPUT VAULT                                          │
│                                                                           │
│  inbox/                                                                   │
│    raw/           - pending items                                         │
│    processed/    - extracted content with frontmatter                    │
│                                                                           │
│  synthesis/                                                              │
│    <meta-topic-1>/                                                       │
│      note-1.md     (frontmatter: created, updated, topics, sources)      │
│      note-2.md                                                          │
│    <meta-topic-2>/                                                       │
│                                                                           │
│  ref/            - ultra-refined notes (future, user manually maintains)  │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SEARCH & GRAPH                                        │
│                                                                           │
│  QMD Integration                                                         │
│  - Local hybrid search (BM25 + vector + LLM rerank, optional)            │
│  - Collections for inbox/, synthesis/                                    │
│  - Context for better search relevance                                   │
│                                                                           │
│  Knowledge Graph                                                         │
│  - Auto-generated from wikilinks                                         │
│  - LLM extracts entities + relationships                                │
│  - Both methods combined                                                 │
│                                                                           │
│  Search UI                                                               │
│  - CLI: nextlog search "query"                                           │
│  - QMD CLI directly                                                      │
│  - Obsidian native search                                                │
│  - LLM skill integration (invoke QMD in AI agent)                        │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLI COMMANDS                                         │
│                                                                           │
│  nextlog fetch        - Fetch X bookmarks (cron-friendly)                │
│  nextlog process     - Extract content from inbox/raw                    │
│  nextlog synthesize  - Create structured notes from processed            │
│  nextlog search      - Search via QMD                                     │
│  nextlog run         - Run fetch + process + synthesize                  │
│  nextlog status      - Show pending/processing status                    │
│                                                                           │
│  Flags (basic): --config, --verbose, --dry-run                          │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        TECH STACK                                           │
│                                                                           │
│  Language:     Python (replaces existing JS, reuses processor.js logic)   │
│  LLM:          OpenRouter (to start)                                      │
│  Config:       JSON/YAML                                                  │
│  Search:       QMD (local hybrid search)                                  │
│  Scheduling:   CLI / Cron only                                            │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary of All Decisions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Inbox location | Folder-based inbox (raw dump/queue) + API pulls |
| Q2 | X bookmarks | Reuse existing processor.js logic |
| Q3 | YouTube | yt-dlp CLI for transcripts |
| Q4 | Obsidian clips | Just index, don't re-process |
| Q5 | Storage | Frontmatter with status (pending/processed/failed) |
| Q6 | Topic ID | LLM-based (autonomous) |
| Q7 | Note structure | Folder per meta topic, notes inside |
| Q8 | Update strategy | Rewrite entirely if needed + decision logs + references |
| Q9 | Backlinks | Wikilinks with option for Obsidian native |
| Q10 | Language | Python |
| Q11 | CLI commands | fetch, process, synthesize, search, run |
| Q12 | Scheduling | CLI / Cron only |
| Q13 | LLM provider | OpenRouter |
| Q14 | Config format | JSON/YAML |
| Q15 | Folder structure | As proposed in architecture |
| Q16 | Error handling | Retry queue + CLI resolution hints |
| Q17 | QMD integration | Yes, with optional LLM rerank |
| Q18 | Knowledge graph | Both (wikilinks + LLM extraction) |
| Q19 | Search UI | Skill-based for LLM + CLI |
| Q20 | Synthesis prompt | Raw content + existing → LLM decides, frontmatter template |
| Q21 | Cross-topic linking | LLM detects during synthesis |
| Q22 | Source attribution | Inline links (continuously maintained) |
| Q23 | Frontmatter | Processed: status (synthesized/not), Synthesized: no status needed |
| Q24 | State tracking | Use QMD collections/context |
| Q25 | Sync mode | Both incremental and full rebuild |
| Q26 | CLI commands | As proposed |
| Q27 | CLI flags | Basic set, add as needed |

---

## Next Steps

Ready to start implementation? Key priorities:
1. Set up Python project structure
2. Port processor.js logic to Python (or wrap it)
3. Implement inbox folder structure
4. Add QMD integration
5. Build synthesis layer 