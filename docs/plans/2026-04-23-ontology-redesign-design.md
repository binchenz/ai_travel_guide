# Ontology Redesign — Design Document

**Status**: Approved (brainstorming complete)
**Date**: 2026-04-23
**Scope**: Refactor the Shanghai Museum guide's data model from an ad-hoc pseudo JSON-LD dictionary into a lightweight three-layer ontology with independent `Hall`, `Dynasty`, and `Person` entities, schema validation, and persona/narrative decoupling.

---

## 1. Decision Summary

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Target ambition | Educational / capstone-grade | YAGNI on CIDOC CRM, Wikidata, cross-institution interop |
| 2 | Extension depth | Full: independent Hall / Dynasty / Person nodes | Best story to tell during the thesis defense |
| 3 | Person granularity | Coarse (name + short bio + dynasty ref) | Avoid biography rabbit hole |
| 4 | Dataset volume | Expand from 5 to 15 artifacts | Makes entity reuse visible |
| 5 | API shape | New structure with reference IDs, drawer UI on frontend | Showcases graph interaction |
| 6 | storylines coupling | Half-decoupled: artifact keeps `narrativePoints`, persona gets `depthTemplates` | Clean three-tier separation |
| 7 | Fence refactor | Skip this round | Separate concern; keep focus |

---

## 2. Non-Goals

- No alignment with CIDOC CRM / Schema.org / Wikidata IRIs.
- No resolvable `@context`; the pseudo JSON-LD keywords (`@id`, `@type`, `@context`) are removed.
- No curator-facing entry tool, no CMS import.
- No transitive closure / SPARQL / graph database.
- No changes to `backend/fence.py`.
- No independent routes for entities on the frontend (a Drawer overlay is sufficient).

---

## 3. Three-Layer Architecture

```
┌─────────────────────────────────────────────────┐
│  FACTS  — data/ontology/                        │
│  ─────────────────────────────────────────────  │
│  artifacts.json     ─┐                          │
│  halls.json          │  cross-referenced by ID  │
│  dynasties.json      │  forming a lightweight   │
│  persons.json        │  knowledge graph         │
│  (+ schemas/*.json) ─┘                          │
├─────────────────────────────────────────────────┤
│  NARRATIVE  — data/persona/current.json         │
│  ─────────────────────────────────────────────  │
│  depthTemplates.entry / deeper / expert         │
│    opener / focus / sentenceStyle               │
│  principles / boundaries / tone  (unchanged)    │
├─────────────────────────────────────────────────┤
│  SYNTHESIS  — backend/ontology/ + persona.py    │
│  ─────────────────────────────────────────────  │
│  build_system_prompt(                           │
│    persona.depthTemplates[level] +              │
│    artifact.narrativePoints[level] +            │
│    resolved(hall, dynasty, persons)             │
│  ) → LLM                                        │
└─────────────────────────────────────────────────┘
```

**Invariants**

- Artifact files contain **no** narrative tokens (no `hook`, `opener`, `tone`).
- Persona files contain **no** factual data (no years, dimensions, names of historical people).
- Every cross-entity link is a string ID; expansion happens in the API layer.

---

## 4. Data Model

### 4.1 Directory layout

```
data/ontology/
  schemas/
    artifact.schema.json
    hall.schema.json
    dynasty.schema.json
    person.schema.json
  artifacts.json          ← replaces data/exhibits.json
  halls.json
  dynasties.json
  persons.json
```

### 4.2 Entity shapes

**Hall**
```json
{
  "id": "hall/bronze-gallery",
  "name": { "en": "Chinese Ancient Bronze Gallery", "zh": "中国古代青铜馆" },
  "floor": 1,
  "theme": { "en": "Ritual vessels and inscriptions",
             "zh": "礼器与铭文" }
}
```

**Dynasty**
```json
{
  "id": "dynasty/western-zhou",
  "name": { "en": "Western Zhou", "zh": "西周" },
  "period": { "start": -1046, "end": -771,
              "label": { "en": "1046-771 BCE", "zh": "公元前1046—前771年" } },
  "predecessor": "dynasty/shang",
  "successor": "dynasty/eastern-zhou",
  "shortDesc": { "en": "...", "zh": "..." }
}
```

**Person** (coarse-grained)
```json
{
  "id": "person/king-li-of-zhou",
  "name": { "en": "King Li of Zhou", "zh": "周厉王" },
  "role": { "en": "Ruler", "zh": "君主" },
  "dynastyId": "dynasty/western-zhou",
  "shortDesc": { "en": "...", "zh": "..." }
}
```

**Artifact** (facts layer, replaces the old `exhibits.json` entries)
```json
{
  "id": "artifact/da-ke-ding",
  "type": "BronzeWare",
  "name": { "en": "Da Ke Ding", "zh": "大克鼎" },
  "imageUrl": "...",

  "hallId":    "hall/bronze-gallery",
  "dynastyId": "dynasty/western-zhou",
  "personIds": ["person/king-li-of-zhou"],

  "period":     { "start": -1000, "end": -900,
                  "label": { "en": "10th century BCE",
                             "zh": "公元前10世纪" } },
  "dimensions": { "height": { "value": 93.1, "unit": "cm" },
                  "weight": { "value": 201.5, "unit": "kg" } },
  "material":   ["bronze", "tin", "lead"],
  "techniques": ["piece-mold casting"],
  "inscriptions": {
    "characterCount": 290,
    "significance": { "en": "...", "zh": "..." }
  },
  "culturalContext": {
    "ritualUse":       { "en": "...", "zh": "..." },
    "socialFunction":  { "en": "...", "zh": "..." },
    "relatedConcepts": ["ritual bronze system", "Zhou li"]
  },

  "narrativePoints": {
    "entry":  ["200kg+ weight", "Survived 3000 years", "Ritual use in ancestor worship"],
    "deeper": ["290-char inscription decoding", "Land grant system of Western Zhou", "Ke family lineage"],
    "expert": ["Piece-mold casting analysis", "Alloy composition details", "Stylistic comparisons"]
  },

  "relationships": {
    "sameDynasty":   ["artifact/mao-gong-ding"],
    "sameTechnique": ["artifact/si-yang-fang-zun"]
  },

  "quickQuestions": {
    "en": ["Tell me about the inscription", "How heavy is it?", "What was it used for?"],
    "zh": ["介绍一下铭文", "有多重？", "用来做什么？"]
  }
}
```

### 4.3 Old vs new field mapping

| Old field | New field | Change |
|-----------|-----------|--------|
| `@context` / `@id` / `@type` | `id` / `type` | Drop pseudo JSON-LD |
| `hall: "Bronze Gallery"` | `hallId: "hall/bronze-gallery"` | String → reference |
| `dynasty: "Western Zhou"` | `dynastyId: "dynasty/western-zhou"` | Same |
| `period: "10th century BCE"` | `period: { start, end, label }` | Structured |
| `dimensions.height: "93.1 cm"` | `height: { value, unit }` | Structured |
| `quickQuestions: ["..."]` | `quickQuestions: { en, zh }` | Bilingual |
| `storylines.entry.hook/theme/focus` | Moved to persona | Decoupled |
| `storylines.entry.keyPoints` | `narrativePoints.entry` | Renamed |

### 4.4 Bidirectional relationships

Authors write **only one direction** for relationships; the loader auto-fills the inverse at startup:

```python
# Authored:
artifact/da-ke-ding.relationships.sameDynasty = ["artifact/mao-gong-ding"]

# After loading, the loader also injects:
artifact/mao-gong-ding.relationships.sameDynasty = ["artifact/da-ke-ding"]
```

---

## 5. Schema Validation

### 5.1 Stack

- **JSON Schema (2020-12)** for tooling and VS Code live lint.
- **Pydantic v2** for runtime validation at load time and automatic OpenAPI docs.

### 5.2 Validation points

| When | Where | Action |
|------|-------|--------|
| Startup | `ontology/loader.py` | Pydantic + jsonschema; fail-fast on any violation |
| Editing | VS Code via `.vscode/settings.json` `json.schemas` mapping | Live red-squigglies on field errors |
| CI / pytest | `test_ontology_integrity.py` | Every JSON file passes `jsonschema validate` |
| Integrity | `test_ontology_integrity.py` | All `hallId` / `dynastyId` / `personId` references resolve |

### 5.3 Editor integration

```json
// .vscode/settings.json
{
  "json.schemas": [
    { "fileMatch": ["data/ontology/artifacts.json"],
      "url": "./data/ontology/schemas/artifact.schema.json" },
    { "fileMatch": ["data/ontology/halls.json"],
      "url": "./data/ontology/schemas/hall.schema.json" },
    { "fileMatch": ["data/ontology/dynasties.json"],
      "url": "./data/ontology/schemas/dynasty.schema.json" },
    { "fileMatch": ["data/ontology/persons.json"],
      "url": "./data/ontology/schemas/person.schema.json" }
  ]
}
```

### 5.4 Failure policy

On startup validation failure, print the exact file/path/field that fails and `sys.exit(1)`. Do not start the server with inconsistent data.

---

## 6. API Design

### 6.1 New entity endpoints

```
GET /ontology/halls                      → list of halls
GET /ontology/dynasties                  → list of dynasties
GET /ontology/persons                    → list of persons

GET /ontology/halls/{id}/artifacts       → artifacts in this hall
GET /ontology/dynasties/{id}/artifacts   → artifacts of this dynasty
GET /ontology/persons/{id}/artifacts     → artifacts related to this person
```

### 6.2 Changed artifact endpoints

`GET /exhibits` — same URL, new shape (list). Each item:

```json
{
  "id": "artifact/da-ke-ding",
  "name": { "en": "Da Ke Ding", "zh": "大克鼎" },
  "imageUrl": "...",
  "hallId": "hall/bronze-gallery",
  "dynastyId": "dynasty/western-zhou",
  "personIds": ["person/king-li-of-zhou"],
  "period": { "start": -1000, "end": -900, "label": {...} },
  "quickQuestions": { "en": [...], "zh": [...] }
}
```

`GET /exhibits/{id}` — detail endpoint **expands references one level** so the frontend avoids N extra requests:

```json
{
  "id": "artifact/da-ke-ding",
  "name": {...},
  "hall":    { "id": "hall/bronze-gallery", "name": {...}, "floor": 1 },
  "dynasty": { "id": "dynasty/western-zhou", "name": {...}, "period": {...} },
  "persons": [{ "id": "person/king-li-of-zhou", "name": {...}, "role": {...} }],
  ...all fact fields...,
  "narrativePoints": {...}
}
```

Only one level of expansion — no `Person → Dynasty → Artifact` recursion.

### 6.3 Chat endpoints

`POST /chat` and `/chat/stream` keep their request shape (exhibitId / depthLevel / language). What changes is the server-side prompt construction; see §7.

### 6.4 Deprecation window

For **one release cycle**, `GET /exhibits` also returns the old flattened fields (`dynasty` string, `hall` string, `originalId`) alongside the new ones. The frontend migrates, then the old fields are removed.

---

## 7. Prompt Construction

### 7.1 Before

```
persona.build_system_prompt(lang, artifact_raw)
  └─ identity + principles + boundaries + tone
     + json.dumps(artifact_raw)  ← contains storylines.hook/theme/focus
```

Narrative templates and facts are entangled in the same blob.

### 7.2 After

```
persona.build_system_prompt(lang, depth_level, artifact_expanded)
  │
  ├─ Narrative (from persona.depthTemplates[depth_level])
  │     opener_instruction           "Start with a vivid analogy..."
  │     focus                        "emotion over precision"
  │     sentence_style               "conversational"
  │     cultural_translator          (existing, reused)
  │
  ├─ Facts (from expanded artifact)
  │     basic_facts      { name, dynasty.name, hall.name, period.label }
  │     detail_facts     { dimensions, material, techniques, inscriptions }
  │     related_entities { persons, sameDynasty, sameTechnique }
  │     narrative_points[depth_level]   (3–5 bullet points)
  │
  └─ Composition rules
        "Use ONLY the facts above."
        "Pick 1–3 narrative_points as the backbone."
        "Apply the opener_instruction and tone."
```

### 7.3 Example prompt (entry level, Da Ke Ding)

```
You are a knowledgeable, warm museum storyteller...

### Principles
- ...

### How to respond at this depth level (entry)
- Start with a vivid analogy or startling comparison
- Focus on emotion and imagination over precision
- Keep sentences conversational

### Current artifact (facts only — do not invent beyond this)
- Name: Da Ke Ding (大克鼎)
- Dynasty: Western Zhou (1046-771 BCE)
- Hall: Chinese Ancient Bronze Gallery, floor 1
- Height: 93.1 cm, Weight: 201.5 kg
- Inscription: 290 characters; records land grants under King Li

### Narrative points you may draw from
- 200kg+ weight
- Survived 3000 years
- Ritual use in ancestor worship

### Related entities the visitor can ask about next
- Persons: King Li of Zhou
- Same dynasty: Mao Gong Ding, San Shi Pan
```

### 7.4 Code responsibility split

| Module | New responsibility |
|--------|--------------------|
| `persona.py` | `get_depth_template(level)` returns the depth template dict |
| `ontology/resolver.py` (new) | `expand_artifact(id)` resolves one level of references |
| `persona.py:build_system_prompt` | Accepts `depth_level`; composes the new sections |
| `main.py` `/chat` endpoint | Passes `depth_level` into `build_system_prompt` (request shape unchanged) |

---

## 8. Frontend Interaction

### 8.1 Principles

No new routes, no layout surgery. Add three clickable chips in the artifact detail and one slide-in Drawer.

### 8.2 Detail view layout (after)

```
┌─ Da Ke Ding ──────────────────────────────┐
│ [image]                                   │
│                                           │
│  [chip: Bronze Gallery]  [chip: W. Zhou]  │
│  [chip: King Li of Zhou]                  │
│                                           │
│  Height 93.1 cm, Weight 201.5 kg          │
│  Material: bronze, tin, lead              │
│  ...                                      │
│                                           │
│  [Chat window unchanged]                  │
└───────────────────────────────────────────┘
```

### 8.3 Drawer contents (Dynasty example)

```
┌─ Drawer: Western Zhou ────────────────────┐
│  1046–771 BCE                             │
│  Follows: Shang    →   Precedes: E. Zhou  │
│                                           │
│  Other artifacts from this dynasty (3):   │
│  ┌──────┐  ┌──────┐  ┌──────┐             │
│  │ Mao  │  │ San  │  │ Da   │             │
│  │ Gong │  │ Shi  │  │ Yu   │             │
│  │ Ding │  │ Pan  │  │ Ding │             │
│  └──────┘  └──────┘  └──────┘             │
└───────────────────────────────────────────┘
```

Hall and Person Drawers use the same layout with different field blocks.

### 8.4 New components (all inline in `App.tsx`)

| Component | Purpose |
|-----------|---------|
| `EntityChip` | Pill; props `{entityType, id, label}`; click triggers `openDrawer(type, id)` |
| `EntityDrawer` | Controlled drawer driven by `useState<{type, id} \| null>` |
| `RelatedArtifacts` | Reusable grid within the drawer |

### 8.5 TypeScript type additions

```typescript
interface Artifact {
  id: string
  name: { en: string; zh: string }
  hallId: string
  dynastyId: string
  personIds: string[]
  period: { start: number; end: number; label: { en: string; zh: string } }
  // ...
}

interface Hall    { id: string; name: {en, zh}; floor: number; theme: {en, zh} }
interface Dynasty { id: string; name: {en, zh}; period: {...}; predecessor?: string; successor?: string }
interface Person  { id: string; name: {en, zh}; role: {en, zh}; dynastyId: string }
```

### 8.6 Out of scope

- Independent `/dynasty/:id` / `/hall/:id` routes
- Dynasty timeline visualization
- Person relationship graph

---

## 9. Data Expansion Plan (5 → 15)

### 9.1 Coverage targets

- **Dynasties balanced**: Shang, Western Zhou, Warring States, Han, Tang, Song, Yuan, Ming, Qing — 1–2 artifacts each.
- **Categories diverse**: Bronze / Ceramic / Jade / Calligraphy-Painting / Lacquer / Coin — 2–3 each.
- **Halls** ≥ 3.
- **Persons** 5–8 (Shang Yang, Qin Shi Huang, Han Wudi, Tang Taizong, Song Huizong, Kangxi, etc.).

### 9.2 Authoring order

Writing order is chosen so that reference IDs always exist when a downstream file references them:

1. `halls.json` (2–3 items)
2. `dynasties.json` (~10 items)
3. `persons.json` (5–8 items)
4. `artifacts.json` (15 items)

### 9.3 Sources

No external scraping. Image URLs continue using the existing `trae-api-cn.mchost.guru` text-to-image endpoint (no new CDN dependency).

---

## 10. Testing Strategy

Three layers, each runnable in under 15 seconds.

### 10.1 Integrity tests — `test_ontology_integrity.py`

- Every JSON file passes its JSON Schema.
- All `hallId` / `dynastyId` / `personId` / `relationships.*` references resolve.
- Each `narrativePoints` depth has at least 2 items.
- Every bilingual field has both `en` and `zh` keys non-empty.

### 10.2 Resolver tests — `test_ontology_resolver.py`

- `expand_artifact(id)` returns the expected nested shape.
- Bidirectional relationship filling is idempotent and complete.
- `get_depth_template(level)` returns the correct template per level.

### 10.3 API contract tests — `test_api_ontology.py`

- `GET /ontology/halls` / `/dynasties` / `/persons` return the expected fields.
- `GET /exhibits/{id}` expansion includes `hall` / `dynasty` / `persons` objects.
- `GET /ontology/dynasties/{id}/artifacts` filters correctly.

### 10.4 Optional: prompt snapshot — `test_prompt_snapshot.py`

Given one artifact and three depth levels, render the prompt and diff against `tests/__snapshots__/`. Intentional prompt changes require approving the new snapshot. Useful narrative material for the defense ("we put prompt engineering under change control").

### 10.5 Out of scope

- End-to-end LLM output quality (already covered by `evaluation_suite.py`).
- Frontend UI tests (no Playwright for a capstone-scale project).

---

## 11. File Change List

| File | Action | Rough size |
|------|--------|-----------|
| `data/exhibits.json` | **Delete** (replaced by `ontology/artifacts.json`) | — |
| `data/ontology/schemas/*.schema.json` | Add (4 files) | ~200 lines |
| `data/ontology/halls.json` | Add | 3 items |
| `data/ontology/dynasties.json` | Add | ~10 items |
| `data/ontology/persons.json` | Add | ~7 items |
| `data/ontology/artifacts.json` | Add (migrate 5 + write 10 new) | 15 items |
| `data/persona/current.json` | Modify (add `depthTemplates.*`) | +30 lines |
| `backend/ontology/__init__.py` | Add | empty |
| `backend/ontology/models.py` | Add (Pydantic models) | ~150 lines |
| `backend/ontology/loader.py` | Add (load + validate + backfill) | ~120 lines |
| `backend/ontology/resolver.py` | Add (`expand_artifact`) | ~60 lines |
| `backend/persona.py` | Modify `build_system_prompt` | -40 / +60 lines |
| `backend/main.py` | Modify `/exhibits`; add `/ontology/*` | +80 lines |
| `frontend/src/App.tsx` | Add `EntityChip` / `EntityDrawer` / types | +150 lines |
| `.vscode/settings.json` | Add schema associations | 10 lines |
| `backend/test_ontology_integrity.py` | Add | ~80 lines |
| `backend/test_ontology_resolver.py` | Add | ~80 lines |
| `backend/test_api_ontology.py` | Add | ~90 lines |

---

## 12. Phased Rollout

Each phase ends in a clean state with green tests, suitable for a git commit.

### Phase 1 — Foundation (schemas, loader, models, migrate 5 artifacts)
- Server still boots; `/exhibits` still returns the same list (now produced by the new loader).
- `test_ontology_integrity.py` is green.

### Phase 2 — Resolver + new endpoints
- `/ontology/halls|dynasties|persons` added.
- Frontend untouched.
- `test_ontology_resolver.py` and `test_api_ontology.py` green.

### Phase 3 — Persona refactor
- `depthTemplates` added; `build_system_prompt` rewritten.
- `/chat` still works (manual smoke check + prompt snapshot tests).

### Phase 4 — Frontend integration
- `EntityChip` and `EntityDrawer` added to artifact detail.
- Click-through works; chat UI unaffected.

### Phase 5 — Data expansion
- Halls 3 → dynasties 10 → persons 7 → artifacts 15, in small commits, each one passes integrity tests.

Estimated total effort: 6–8 hours, spread across 2–3 work sessions.

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM output quality regresses after prompt refactor | Phase 3 snapshot tests + manual spot check of 3 artifacts × 3 depth levels |
| Chip UI disrupts existing chat flow | Drawer is an overlay; chat state remains isolated from drawer state |
| Data expansion overruns schedule | 15 items is a hard ceiling; if capacity is limited, stop at 10 |
| Schema too strict, blocks authoring | Only `id` / `name` / `hallId` / `dynastyId` are required; everything else optional |
