# Plan: Persistent Memory + Knowledge Discovery for Sundial

## Overview

Add persistent memory and knowledge discovery to make Claude a stateful assistant across conversations. Two options for the discovery layer — choose based on server constraints.

---

## Feature 1: Persistent Memory (both options use this)

Simple key-value memory store for preferences, decisions, and learned context. Claude extracts and stores these during conversations via MCP tools.

### Design Decisions
- **Dedicated `memories` table** — memories have different structure and access patterns than user notes
- **Categories** for organization: `preference`, `decision`, `pattern`, `project_context`, `person`
- **FTS5 index** on memories for keyword search
- **UNIQUE(category, key)** — Claude can upsert without creating duplicates

### Database Schema

```sql
CREATE TABLE memories (
    id VARCHAR PRIMARY KEY,              -- mem_abc123xyz
    category VARCHAR NOT NULL,           -- preference, decision, pattern, project_context, person
    key VARCHAR NOT NULL,                -- Short identifier (e.g., "preferred_language")
    content TEXT NOT NULL,               -- The memory content
    source_type VARCHAR,                 -- note, task, conversation
    source_id VARCHAR,                   -- Reference to source if applicable
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE(category, key)
);

CREATE INDEX idx_memories_category ON memories(category);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(id, key, content, category);
```

### MCP Tools (4 new)
| Tool | Description |
|------|-------------|
| `get_memories` | Retrieve memories, optionally filtered by category or search query |
| `add_memory` | Store a new memory with category, key, content |
| `update_memory` | Update existing memory content |
| `delete_memory` | Remove a memory |

### New Files
- `api/models/memory.py` — Memory model
- `api/services/memory_service.py` — CRUD + FTS search

---

## Feature 2: Knowledge Discovery

Two mutually exclusive options. Pick one.

---

### Option A: Knowledge Graph (recommended for small servers)

Claude reads notes and extracts entities + relationships, stores them as triples. The server is dumb storage — Claude does all the intelligence at call time. Zero compute on the server, just SQL queries.

#### Why this option
- **No model to run** — server just stores and queries triples
- **No dependencies** — pure SQLite
- **Explicit relationships** — "Sam works_on Sundial" is more useful than a similarity score
- **Builds on existing note_links** — the wiki-link system already tracks connections between notes/tasks/events; the knowledge graph adds typed, semantic relationships on top
- **Traversable** — "what do I know about X" becomes a graph walk, not a vector search

#### What you lose
- No fuzzy "find notes about burnout" — you need to know what you're looking for (FTS5 covers keyword search though)
- Graph quality depends on Claude remembering to extract entities during conversations

#### Database Schema

```sql
CREATE TABLE knowledge_graph (
    id VARCHAR PRIMARY KEY,
    subject VARCHAR NOT NULL,            -- entity name (normalized lowercase)
    predicate VARCHAR NOT NULL,          -- relationship type
    object VARCHAR NOT NULL,             -- entity name (normalized lowercase)
    source_note_id VARCHAR,              -- which note this was extracted from
    confidence FLOAT DEFAULT 1.0,        -- Claude's confidence in the triple
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE(subject, predicate, object)
);

CREATE INDEX idx_kg_subject ON knowledge_graph(subject);
CREATE INDEX idx_kg_object ON knowledge_graph(object);
CREATE INDEX idx_kg_predicate ON knowledge_graph(predicate);
CREATE INDEX idx_kg_source ON knowledge_graph(source_note_id);
```

#### MCP Tools (4 new)
| Tool | Description |
|------|-------------|
| `add_knowledge` | Store a (subject, predicate, object) triple, optionally linked to a source note |
| `query_knowledge` | Find triples by subject, predicate, and/or object. Supports partial queries (e.g., all triples where subject="sam") |
| `get_related` | Given an entity, return all directly connected entities (one hop). Useful for "what do I know about X?" |
| `delete_knowledge` | Remove a triple |

#### Example triples
```
(sam, prefers, python)
(sam, prefers, svelte)
(sundial, built_with, fastapi)
(sundial, built_with, sveltekit)
(meeting_2024_02_03, mentions, sarah)
(sarah, works_on, project_atlas)
(project_atlas, deadline, march_2024)
(sundial, design_decision, hybrid_storage)
(hybrid_storage, means, markdown_files_plus_sqlite)
```

#### New Files
- `api/models/knowledge.py` — KnowledgeGraph model
- `api/services/knowledge_service.py` — CRUD + graph queries

---

### Option B: Semantic Search via Embeddings (requires beefier server)

Generate vector embeddings for notes and search by meaning. Requires running a ~90MB+ model on the server or calling an external embedding API.

#### Why this option
- **Fuzzy search** — "that thing about feeling stuck" can find a note titled "career reflection"
- **No manual extraction** — every note is automatically searchable by meaning
- **Works without Claude** — search is independent of conversation context

#### What you lose
- **Server resources** — sentence-transformers needs ~500MB RAM for the model, or you pay per API call for external embeddings
- **No relationships** — you get "these notes are similar" but not "why" or "how they connect"
- **Dependency** — adds `sentence-transformers` (~90MB package) or external API dependency

#### Database Schema

```sql
CREATE TABLE embeddings (
    id VARCHAR PRIMARY KEY,
    entity_type VARCHAR NOT NULL,        -- 'note' or 'memory'
    entity_id VARCHAR NOT NULL,
    embedding TEXT NOT NULL,             -- JSON array of floats
    model VARCHAR NOT NULL,              -- e.g., 'all-MiniLM-L6-v2'
    created_at DATETIME NOT NULL,
    UNIQUE(entity_type, entity_id)
);

CREATE INDEX idx_embeddings_entity ON embeddings(entity_type, entity_id);
```

#### MCP Tool (1 new)
| Tool | Description |
|------|-------------|
| `semantic_search` | Search notes by meaning. Returns ranked results with similarity scores. |

#### Embedding Flow
1. Note created/updated → queue for embedding (in-process, after response)
2. Background task loads model → generates embedding → stores in DB
3. Semantic search → embed query → cosine similarity against stored embeddings
4. Model loaded lazily on first use (~500MB download on first run)

#### New Files
- `api/services/embedding_service.py` — Embedding generation + similarity search

---

## Comparison

| | Knowledge Graph (A) | Semantic Search (B) |
|---|---|---|
| Server requirements | Minimal (SQLite only) | ~500MB RAM for model |
| Dependencies | None | sentence-transformers or API |
| Search type | Exact entities + traversal | Fuzzy meaning-based |
| Data quality | High (explicit relationships) | Automatic (but opaque) |
| Maintenance | Claude must extract triples | Automatic on note save |
| Works offline | Yes | Yes (local model) or No (API) |
| Best for | "What do I know about X?" | "Find notes like Y" |

---

## Implementation Order

### Phase 1: Memory System (shared)
1. Create `api/models/memory.py`
2. Update `api/models/__init__.py`
3. Add migration in `api/init_db.py`
4. Create `api/services/memory_service.py`
5. Add 4 MCP tools to `api/mcp/server.py`

### Phase 2A: Knowledge Graph (if choosing Option A)
1. Create `api/models/knowledge.py`
2. Update `api/models/__init__.py`
3. Add migration in `api/init_db.py`
4. Create `api/services/knowledge_service.py`
5. Add 4 MCP tools to `api/mcp/server.py`
6. Optionally: backfill by having Claude read existing notes and extract triples

### Phase 2B: Semantic Search (if choosing Option B)
1. Add `sentence-transformers` to `pyproject.toml`
2. Add `embeddings_enabled` setting
3. Create `api/services/embedding_service.py`
4. Add embeddings table migration in `api/init_db.py`
5. Hook into `note_service.py` for background embedding
6. Add `semantic_search` MCP tool
7. Batch embed existing notes

---

## Files to Modify

### Shared (Phase 1)
| File | Changes |
|------|---------|
| `api/models/memory.py` | NEW — Memory model |
| `api/models/__init__.py` | Import Memory |
| `api/services/memory_service.py` | NEW — Memory CRUD + FTS |
| `api/mcp/server.py` | Add 4 memory tools |
| `api/init_db.py` | Add memories table + FTS |

### Option A additions
| File | Changes |
|------|---------|
| `api/models/knowledge.py` | NEW — KnowledgeGraph model |
| `api/models/__init__.py` | Import KnowledgeGraph |
| `api/services/knowledge_service.py` | NEW — CRUD + graph queries |
| `api/mcp/server.py` | Add 4 knowledge graph tools |
| `api/init_db.py` | Add knowledge_graph table |

### Option B additions
| File | Changes |
|------|---------|
| `api/services/embedding_service.py` | NEW — Embeddings + similarity |
| `api/services/note_service.py` | Hook embedding generation |
| `api/mcp/server.py` | Add semantic_search tool |
| `api/init_db.py` | Add embeddings table |
| `pyproject.toml` | Add sentence-transformers |

---

## Verification

1. **Memory system**: Add/get/search memories via MCP tools across separate conversations
2. **Knowledge graph (A)**: Extract triples from a note, query by entity, traverse relationships
3. **Semantic search (B)**: Create notes, verify embeddings generated, search by meaning and get relevant results
