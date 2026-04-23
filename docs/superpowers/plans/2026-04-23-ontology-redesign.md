# Ontology Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the museum guide's data model into a three-layer ontology with independent `Hall` / `Dynasty` / `Person` entities, JSON Schema + Pydantic validation, and persona/narrative decoupling. Expand from 5 to 15 artifacts.

**Architecture:** New `data/ontology/` layout with four entity files + schemas. Backend gains an `ontology/` package (loader + models + resolver). Prompt construction splits facts (artifact) from narrative templates (persona). Frontend adds inline `EntityChip` + `EntityDrawer` components in `App.tsx`; no new routes.

**Tech Stack:** Python 3, FastAPI, Pydantic v2, jsonschema, React 18 / TypeScript / Vite. Design: `docs/plans/2026-04-23-ontology-redesign-design.md`.

---

## File Structure

| File | Role |
|------|------|
| `data/ontology/schemas/hall.schema.json` | New — JSON Schema for Hall |
| `data/ontology/schemas/dynasty.schema.json` | New — JSON Schema for Dynasty |
| `data/ontology/schemas/person.schema.json` | New — JSON Schema for Person |
| `data/ontology/schemas/artifact.schema.json` | New — JSON Schema for Artifact |
| `data/ontology/halls.json` | New — Hall entities |
| `data/ontology/dynasties.json` | New — Dynasty entities |
| `data/ontology/persons.json` | New — Person entities |
| `data/ontology/artifacts.json` | New — Artifact entities (migrated + new) |
| `data/exhibits.json` | Delete — superseded |
| `data/persona/current.json` | Modify — add `depthTemplates.entry/deeper/expert` |
| `backend/ontology/__init__.py` | New — package marker |
| `backend/ontology/models.py` | New — Pydantic v2 models |
| `backend/ontology/loader.py` | New — loads & validates JSON, backfills bidirectional rels |
| `backend/ontology/resolver.py` | New — `expand_artifact()` one-level reference expansion |
| `backend/persona.py` | Modify — `build_system_prompt(depth_level, artifact_expanded)` |
| `backend/main.py` | Modify — new `/ontology/*` endpoints; update `/exhibits`; update `/chat` |
| `backend/requirements.txt` | Modify — add `jsonschema>=4.21.0` |
| `backend/test_ontology_integrity.py` | New — JSON Schema + cross-reference validation |
| `backend/test_ontology_resolver.py` | New — Resolver behavior |
| `backend/test_api_ontology.py` | New — API contract |
| `backend/test_prompt_snapshot.py` | New — Prompt change-control snapshot tests |
| `backend/tests/__snapshots__/` | New — Snapshot files directory |
| `frontend/src/App.tsx` | Modify — add types, EntityChip, EntityDrawer, chip rendering |
| `.vscode/settings.json` | New — JSON schema associations for authoring |

---

## Phase 1 — Foundation

### Task 1: Add jsonschema dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Append dependency**

Add to `backend/requirements.txt`:

```
jsonschema>=4.21.0
```

- [ ] **Step 2: Install**

Run: `cd backend && source venv/bin/activate && pip install -r requirements.txt`
Expected: `Successfully installed jsonschema-...`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add jsonschema for ontology validation"
```

---

### Task 2: Write JSON Schema for Hall

**Files:**
- Create: `data/ontology/schemas/hall.schema.json`

- [ ] **Step 1: Create schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "hall.schema.json",
  "title": "Hall",
  "type": "object",
  "required": ["id", "name", "floor"],
  "additionalProperties": false,
  "properties": {
    "id": { "type": "string", "pattern": "^hall/[a-z0-9-]+$" },
    "name": { "$ref": "#/$defs/bilingualString" },
    "floor": { "type": "integer", "minimum": 0 },
    "theme": { "$ref": "#/$defs/bilingualString" }
  },
  "$defs": {
    "bilingualString": {
      "type": "object",
      "required": ["en", "zh"],
      "additionalProperties": false,
      "properties": {
        "en": { "type": "string", "minLength": 1 },
        "zh": { "type": "string", "minLength": 1 }
      }
    }
  }
}
```

- [ ] **Step 2: Validate the schema itself**

Run: `python -c "import json,jsonschema; s=json.load(open('data/ontology/schemas/hall.schema.json')); jsonschema.Draft202012Validator.check_schema(s); print('OK')"`
Expected: `OK`

---

### Task 3: Write JSON Schema for Dynasty

**Files:**
- Create: `data/ontology/schemas/dynasty.schema.json`

- [ ] **Step 1: Create schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "dynasty.schema.json",
  "title": "Dynasty",
  "type": "object",
  "required": ["id", "name", "period"],
  "additionalProperties": false,
  "properties": {
    "id": { "type": "string", "pattern": "^dynasty/[a-z0-9-]+$" },
    "name": { "$ref": "#/$defs/bilingualString" },
    "period": {
      "type": "object",
      "required": ["start", "end", "label"],
      "additionalProperties": false,
      "properties": {
        "start": { "type": "integer" },
        "end":   { "type": "integer" },
        "label": { "$ref": "#/$defs/bilingualString" }
      }
    },
    "predecessor": { "type": "string", "pattern": "^dynasty/[a-z0-9-]+$" },
    "successor":   { "type": "string", "pattern": "^dynasty/[a-z0-9-]+$" },
    "shortDesc":   { "$ref": "#/$defs/bilingualString" }
  },
  "$defs": {
    "bilingualString": {
      "type": "object",
      "required": ["en", "zh"],
      "additionalProperties": false,
      "properties": {
        "en": { "type": "string", "minLength": 1 },
        "zh": { "type": "string", "minLength": 1 }
      }
    }
  }
}
```

- [ ] **Step 2: Validate**

Run: `python -c "import json,jsonschema; s=json.load(open('data/ontology/schemas/dynasty.schema.json')); jsonschema.Draft202012Validator.check_schema(s); print('OK')"`
Expected: `OK`

---

### Task 4: Write JSON Schema for Person

**Files:**
- Create: `data/ontology/schemas/person.schema.json`

- [ ] **Step 1: Create schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "person.schema.json",
  "title": "Person",
  "type": "object",
  "required": ["id", "name", "role", "dynastyId"],
  "additionalProperties": false,
  "properties": {
    "id":        { "type": "string", "pattern": "^person/[a-z0-9-]+$" },
    "name":      { "$ref": "#/$defs/bilingualString" },
    "role":      { "$ref": "#/$defs/bilingualString" },
    "dynastyId": { "type": "string", "pattern": "^dynasty/[a-z0-9-]+$" },
    "shortDesc": { "$ref": "#/$defs/bilingualString" }
  },
  "$defs": {
    "bilingualString": {
      "type": "object",
      "required": ["en", "zh"],
      "additionalProperties": false,
      "properties": {
        "en": { "type": "string", "minLength": 1 },
        "zh": { "type": "string", "minLength": 1 }
      }
    }
  }
}
```

- [ ] **Step 2: Validate**

Run: `python -c "import json,jsonschema; s=json.load(open('data/ontology/schemas/person.schema.json')); jsonschema.Draft202012Validator.check_schema(s); print('OK')"`
Expected: `OK`

---

### Task 5: Write JSON Schema for Artifact

**Files:**
- Create: `data/ontology/schemas/artifact.schema.json`

- [ ] **Step 1: Create schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "artifact.schema.json",
  "title": "Artifact",
  "type": "object",
  "required": ["id", "type", "name", "hallId", "dynastyId"],
  "additionalProperties": false,
  "properties": {
    "id":        { "type": "string", "pattern": "^artifact/[a-z0-9-]+$" },
    "type":      { "type": "string" },
    "name":      { "$ref": "#/$defs/bilingualString" },
    "imageUrl":  { "type": "string", "format": "uri" },
    "hallId":    { "type": "string", "pattern": "^hall/[a-z0-9-]+$" },
    "dynastyId": { "type": "string", "pattern": "^dynasty/[a-z0-9-]+$" },
    "personIds": {
      "type": "array",
      "items": { "type": "string", "pattern": "^person/[a-z0-9-]+$" }
    },
    "period": {
      "type": "object",
      "required": ["start", "end", "label"],
      "additionalProperties": false,
      "properties": {
        "start": { "type": "integer" },
        "end":   { "type": "integer" },
        "label": { "$ref": "#/$defs/bilingualString" }
      }
    },
    "dimensions": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["value", "unit"],
        "additionalProperties": false,
        "properties": {
          "value": { "type": "number" },
          "unit":  { "type": "string" }
        }
      }
    },
    "material":   { "type": "array", "items": { "type": "string" } },
    "techniques": { "type": "array", "items": { "type": "string" } },
    "inscriptions": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "characterCount": { "type": "integer", "minimum": 0 },
        "significance":   { "$ref": "#/$defs/bilingualString" }
      }
    },
    "culturalContext": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "ritualUse":        { "$ref": "#/$defs/bilingualString" },
        "socialFunction":   { "$ref": "#/$defs/bilingualString" },
        "relatedConcepts":  { "type": "array", "items": { "type": "string" } }
      }
    },
    "narrativePoints": {
      "type": "object",
      "required": ["entry", "deeper", "expert"],
      "additionalProperties": false,
      "properties": {
        "entry":  { "type": "array", "minItems": 2, "items": { "type": "string" } },
        "deeper": { "type": "array", "minItems": 2, "items": { "type": "string" } },
        "expert": { "type": "array", "minItems": 2, "items": { "type": "string" } }
      }
    },
    "relationships": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": { "type": "string", "pattern": "^artifact/[a-z0-9-]+$" }
      }
    },
    "quickQuestions": {
      "type": "object",
      "required": ["en", "zh"],
      "additionalProperties": false,
      "properties": {
        "en": { "type": "array", "items": { "type": "string" } },
        "zh": { "type": "array", "items": { "type": "string" } }
      }
    }
  },
  "$defs": {
    "bilingualString": {
      "type": "object",
      "required": ["en", "zh"],
      "additionalProperties": false,
      "properties": {
        "en": { "type": "string", "minLength": 1 },
        "zh": { "type": "string", "minLength": 1 }
      }
    }
  }
}
```

- [ ] **Step 2: Validate**

Run: `python -c "import json,jsonschema; s=json.load(open('data/ontology/schemas/artifact.schema.json')); jsonschema.Draft202012Validator.check_schema(s); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit schemas**

```bash
git add data/ontology/schemas/
git commit -m "feat(ontology): add JSON Schemas for Hall/Dynasty/Person/Artifact"
```

---

### Task 6: Author initial halls.json

**Files:**
- Create: `data/ontology/halls.json`

The existing 5 artifacts reference two halls. Write both.

- [ ] **Step 1: Create file**

```json
[
  {
    "id": "hall/bronze-gallery",
    "name": { "en": "Chinese Ancient Bronze Gallery", "zh": "中国古代青铜馆" },
    "floor": 1,
    "theme": { "en": "Ritual vessels and inscriptions from the Shang through Han dynasties",
               "zh": "从商代到汉代的礼器与铭文" }
  },
  {
    "id": "hall/ceramics-gallery",
    "name": { "en": "Chinese Ceramics Gallery", "zh": "中国陶瓷馆" },
    "floor": 2,
    "theme": { "en": "Two thousand years of Chinese pottery and porcelain",
               "zh": "两千年的中国陶瓷艺术" }
  }
]
```

- [ ] **Step 2: Validate against schema**

Run:
```bash
python -c "
import json, jsonschema
schema = json.load(open('data/ontology/schemas/hall.schema.json'))
data = json.load(open('data/ontology/halls.json'))
for item in data:
    jsonschema.validate(item, schema)
print(f'{len(data)} halls validated')
"
```
Expected: `2 halls validated`

---

### Task 7: Author initial dynasties.json

**Files:**
- Create: `data/ontology/dynasties.json`

The existing 5 artifacts span 4 dynasties: Shang, Western Zhou, Warring States, Ming. We also include adjacent dynasties so `predecessor`/`successor` can link (Eastern Zhou, Qin, Han).

- [ ] **Step 1: Create file**

```json
[
  {
    "id": "dynasty/shang",
    "name": { "en": "Shang Dynasty", "zh": "商朝" },
    "period": { "start": -1600, "end": -1046,
                "label": { "en": "1600-1046 BCE", "zh": "公元前1600—前1046年" } },
    "successor": "dynasty/western-zhou",
    "shortDesc": { "en": "Bronze age dynasty famous for oracle bone script and ritual vessels.",
                   "zh": "青铜时代王朝，以甲骨文和礼器闻名。" }
  },
  {
    "id": "dynasty/western-zhou",
    "name": { "en": "Western Zhou", "zh": "西周" },
    "period": { "start": -1046, "end": -771,
                "label": { "en": "1046-771 BCE", "zh": "公元前1046—前771年" } },
    "predecessor": "dynasty/shang",
    "successor": "dynasty/eastern-zhou",
    "shortDesc": { "en": "Feudal dynasty whose ritual bronze inscriptions are primary historical sources.",
                   "zh": "封建王朝，其青铜铭文是重要的历史文献。" }
  },
  {
    "id": "dynasty/eastern-zhou",
    "name": { "en": "Eastern Zhou", "zh": "东周" },
    "period": { "start": -770, "end": -256,
                "label": { "en": "770-256 BCE", "zh": "公元前770—前256年" } },
    "predecessor": "dynasty/western-zhou",
    "shortDesc": { "en": "Later Zhou, encompassing the Spring and Autumn and Warring States periods.",
                   "zh": "东迁之后的周朝，包括春秋与战国时期。" }
  },
  {
    "id": "dynasty/warring-states",
    "name": { "en": "Warring States Period", "zh": "战国" },
    "period": { "start": -475, "end": -221,
                "label": { "en": "475-221 BCE", "zh": "公元前475—前221年" } },
    "predecessor": "dynasty/eastern-zhou",
    "successor": "dynasty/qin",
    "shortDesc": { "en": "Era of seven rival states ending with Qin unification.",
                   "zh": "七雄争霸，终以秦统一天下。" }
  },
  {
    "id": "dynasty/qin",
    "name": { "en": "Qin Dynasty", "zh": "秦朝" },
    "period": { "start": -221, "end": -206,
                "label": { "en": "221-206 BCE", "zh": "公元前221—前206年" } },
    "predecessor": "dynasty/warring-states",
    "successor": "dynasty/han",
    "shortDesc": { "en": "First unified Chinese empire; standardized weights, measures, and script.",
                   "zh": "中国首个统一帝国，统一度量衡与文字。" }
  },
  {
    "id": "dynasty/han",
    "name": { "en": "Han Dynasty", "zh": "汉朝" },
    "period": { "start": -206, "end": 220,
                "label": { "en": "206 BCE – 220 CE", "zh": "公元前206—公元220年" } },
    "predecessor": "dynasty/qin",
    "shortDesc": { "en": "Long-lasting empire whose cultural legacy defined Han identity.",
                   "zh": "延续四百余年的帝国，奠定华夏文化认同。" }
  },
  {
    "id": "dynasty/tang",
    "name": { "en": "Tang Dynasty", "zh": "唐朝" },
    "period": { "start": 618, "end": 907,
                "label": { "en": "618-907 CE", "zh": "公元618—907年" } },
    "shortDesc": { "en": "Cosmopolitan golden age of Chinese poetry, painting, and tricolor ceramics.",
                   "zh": "开放繁盛的黄金时代，以诗、画与唐三彩著称。" }
  },
  {
    "id": "dynasty/song",
    "name": { "en": "Song Dynasty", "zh": "宋朝" },
    "period": { "start": 960, "end": 1279,
                "label": { "en": "960-1279 CE", "zh": "公元960—1279年" } },
    "shortDesc": { "en": "Peak of Chinese ceramics and landscape painting.",
                   "zh": "中国陶瓷与山水画的巅峰。" }
  },
  {
    "id": "dynasty/yuan",
    "name": { "en": "Yuan Dynasty", "zh": "元朝" },
    "period": { "start": 1271, "end": 1368,
                "label": { "en": "1271-1368 CE", "zh": "公元1271—1368年" } },
    "successor": "dynasty/ming",
    "shortDesc": { "en": "Mongol-ruled empire that opened China to Eurasian trade.",
                   "zh": "蒙古人统治的帝国，打通欧亚贸易。" }
  },
  {
    "id": "dynasty/ming",
    "name": { "en": "Ming Dynasty", "zh": "明朝" },
    "period": { "start": 1368, "end": 1644,
                "label": { "en": "1368-1644 CE", "zh": "公元1368—1644年" } },
    "predecessor": "dynasty/yuan",
    "successor": "dynasty/qing",
    "shortDesc": { "en": "Era renowned for blue-and-white porcelain and imperial architecture.",
                   "zh": "青花瓷与宫廷建筑的时代。" }
  },
  {
    "id": "dynasty/qing",
    "name": { "en": "Qing Dynasty", "zh": "清朝" },
    "period": { "start": 1644, "end": 1912,
                "label": { "en": "1644-1912 CE", "zh": "公元1644—1912年" } },
    "predecessor": "dynasty/ming",
    "shortDesc": { "en": "Last imperial dynasty, fusion of Manchu and Han cultures.",
                   "zh": "最后一个王朝，满汉文化交融。" }
  }
]
```

- [ ] **Step 2: Validate**

Run:
```bash
python -c "
import json, jsonschema
schema = json.load(open('data/ontology/schemas/dynasty.schema.json'))
data = json.load(open('data/ontology/dynasties.json'))
for item in data:
    jsonschema.validate(item, schema)
print(f'{len(data)} dynasties validated')
"
```
Expected: `11 dynasties validated`

---

### Task 8: Author initial persons.json

**Files:**
- Create: `data/ontology/persons.json`

- [ ] **Step 1: Create file**

```json
[
  {
    "id": "person/king-li-of-zhou",
    "name": { "en": "King Li of Zhou", "zh": "周厉王" },
    "role": { "en": "Ruler", "zh": "君主" },
    "dynastyId": "dynasty/western-zhou",
    "shortDesc": { "en": "Western Zhou king whose reign ended in exile after popular uprising.",
                   "zh": "西周国王，因失政被国人暴动驱逐。" }
  },
  {
    "id": "person/shang-yang",
    "name": { "en": "Shang Yang", "zh": "商鞅" },
    "role": { "en": "Statesman and reformer", "zh": "政治家与改革家" },
    "dynastyId": "dynasty/warring-states",
    "shortDesc": { "en": "Qin minister whose Legalist reforms laid the foundation for Chinese unification.",
                   "zh": "秦国大臣，以法家改革奠定统一基础。" }
  },
  {
    "id": "person/xuande-emperor",
    "name": { "en": "Xuande Emperor", "zh": "明宣宗" },
    "role": { "en": "Ming emperor and artist-patron", "zh": "明代皇帝与艺术赞助人" },
    "dynastyId": "dynasty/ming",
    "shortDesc": { "en": "Ming emperor whose court produced some of China's finest porcelain and bronze incense burners.",
                   "zh": "明代皇帝，其宫廷出产精美的瓷器与宣德炉。" }
  }
]
```

- [ ] **Step 2: Validate schema + cross-references**

Run:
```bash
python -c "
import json, jsonschema
schema  = json.load(open('data/ontology/schemas/person.schema.json'))
persons = json.load(open('data/ontology/persons.json'))
dyn_ids = {d['id'] for d in json.load(open('data/ontology/dynasties.json'))}
for p in persons:
    jsonschema.validate(p, schema)
    assert p['dynastyId'] in dyn_ids, f\"Bad dynastyId on {p['id']}\"
print(f'{len(persons)} persons validated')
"
```
Expected: `3 persons validated`

---

### Task 9: Migrate exhibits.json → artifacts.json

**Files:**
- Create: `data/ontology/artifacts.json`

Convert each of the 5 existing artifacts to the new shape. Structure per the design doc §4.2.

- [ ] **Step 1: Write the migrated file**

Open `data/exhibits.json` for reference, then create `data/ontology/artifacts.json` with all 5 items translated to the new shape. For each existing artifact:
- drop `@context`
- rename `@id` (e.g. `"artifact/da-ke-ding"`) to `id`
- rename `@type` to `type`
- replace `hall: "Bronze Gallery"` with `hallId: "hall/bronze-gallery"`
- replace `dynasty: "Western Zhou"` with `dynastyId: "dynasty/western-zhou"`
- convert `period: "10th century BCE"` to `period: { start, end, label: {en, zh} }`
- convert `dimensions.height: "93.1 cm"` to `dimensions.height: { value: 93.1, unit: "cm" }`
- wrap every nested description string in `{en, zh}`
- convert `quickQuestions: ["..."]` to `quickQuestions: { en: [...], zh: [...] }`
- flatten `storylines.*.keyPoints` arrays into `narrativePoints.entry/deeper/expert`; discard `theme`, `hook`, `focus`
- assign `personIds: ["person/king-li-of-zhou"]` to Da Ke Ding, `["person/shang-yang"]` to Shang Yang Sheng, `["person/xuande-emperor"]` to Xuande Incense Burner
- keep `relationships.sameDynasty` / `sameTechnique` with existing IDs

Here is the complete new `data/ontology/artifacts.json`:

```json
[
  {
    "id": "artifact/da-ke-ding",
    "type": "BronzeWare",
    "name": { "en": "Da Ke Ding", "zh": "大克鼎" },
    "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Da%20Ke%20Ding%20Western%20Zhou%20bronze%20vessel%20ancient%20Chinese%20artifact%20with%20inscriptions%20on%20a%20dark%20background&image_size=landscape_16_9",
    "hallId": "hall/bronze-gallery",
    "dynastyId": "dynasty/western-zhou",
    "personIds": ["person/king-li-of-zhou"],
    "period": {
      "start": -1000, "end": -900,
      "label": { "en": "10th century BCE", "zh": "公元前10世纪" }
    },
    "dimensions": {
      "height": { "value": 93.1, "unit": "cm" },
      "weight": { "value": 201.5, "unit": "kg" }
    },
    "material":   ["bronze", "tin", "lead"],
    "techniques": ["piece-mold casting"],
    "inscriptions": {
      "characterCount": 290,
      "significance": {
        "en": "Records land grants and rituals from the reign of King Li of Zhou.",
        "zh": "记录周厉王时期的土地赐予与礼仪。"
      }
    },
    "culturalContext": {
      "ritualUse": {
        "en": "Ancestral worship and feudal ceremonies.",
        "zh": "祭祖与分封典礼用器。"
      },
      "socialFunction": {
        "en": "Symbol of aristocratic status and family lineage.",
        "zh": "贵族身份与家族血脉的象征。"
      },
      "relatedConcepts": ["ritual bronze system", "Zhou li", "feudal hierarchy"]
    },
    "narrativePoints": {
      "entry":  ["Impressive size and weight over 200 kg", "Basic ritual use in ancestor worship", "Survival through dynasties and war"],
      "deeper": ["What the 290-character inscription actually says", "Land grant system of the Western Zhou", "The Ke family lineage"],
      "expert": ["Piece-mold casting technique analysis", "Alloy composition details", "Stylistic comparisons to other bronzes"]
    },
    "relationships": {
      "sameDynasty":   ["artifact/mao-gong-ding", "artifact/san-shi-pan"],
      "sameTechnique": ["artifact/si-yang-fang-zun"]
    },
    "quickQuestions": {
      "en": ["Tell me about the inscription", "How heavy is it?", "What was it used for?"],
      "zh": ["介绍一下铭文", "有多重？", "用来做什么？"]
    }
  },
  {
    "id": "artifact/shang-yang-sheng",
    "type": "BronzeWare",
    "name": { "en": "Shang Yang Sheng (Standard Measure)", "zh": "商鞅方升" },
    "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Shang%20Yang%20Sheng%20Warring%20States%20bronze%20standard%20measure%20ancient%20Chinese%20artifact%20with%20inscriptions&image_size=landscape_16_9",
    "hallId": "hall/bronze-gallery",
    "dynastyId": "dynasty/warring-states",
    "personIds": ["person/shang-yang"],
    "period": {
      "start": -344, "end": -344,
      "label": { "en": "344 BCE", "zh": "公元前344年" }
    },
    "dimensions": {
      "width": { "value": 18.7, "unit": "cm" },
      "depth": { "value":  6.9, "unit": "cm" }
    },
    "material":   ["bronze"],
    "techniques": ["lost-wax casting"],
    "inscriptions": {
      "characterCount": 32,
      "significance": {
        "en": "Records Shang Yang's standardization of weights and measures.",
        "zh": "记录商鞅推行的度量衡统一。"
      }
    },
    "culturalContext": {
      "ritualUse":       { "en": "State administration.", "zh": "国家行政。" },
      "socialFunction":  { "en": "Standard of measurement for taxation and governance.", "zh": "赋税与施政的度量基准。" },
      "relatedConcepts": ["Qin unification", "Chinese statecraft", "legalism"]
    },
    "narrativePoints": {
      "entry":  ["The measuring cup that helped unify China", "Tiny but historically explosive", "32 characters that changed governance"],
      "deeper": ["Legalist reforms and their economic effect", "Standardization as political tool", "From Qin state to Qin empire"],
      "expert": ["Precision metallurgy in Warring States", "Comparative studies with other sheng", "Inscription paleography"]
    },
    "relationships": {
      "sameDynasty": []
    },
    "quickQuestions": {
      "en": ["Who was Shang Yang?", "Why does this small object matter?", "What does the inscription say?"],
      "zh": ["商鞅是谁？", "这么小的物件为何重要？", "铭文写了什么？"]
    }
  },
  {
    "id": "artifact/si-yang-fang-zun",
    "type": "BronzeWare",
    "name": { "en": "Si Yang Fang Zun (Four-Ram Vessel)", "zh": "四羊方尊" },
    "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Four%20ram%20square%20zun%20Shang%20dynasty%20bronze%20ritual%20vessel%20with%20ram%20heads%20on%20corners&image_size=landscape_16_9",
    "hallId": "hall/bronze-gallery",
    "dynastyId": "dynasty/shang",
    "personIds": [],
    "period": {
      "start": -1200, "end": -1046,
      "label": { "en": "Late Shang, c. 12th–11th century BCE", "zh": "商代晚期，约公元前12—前11世纪" }
    },
    "dimensions": {
      "height": { "value": 58.3, "unit": "cm" },
      "weight": { "value": 34.5, "unit": "kg" }
    },
    "material":   ["bronze"],
    "techniques": ["piece-mold casting"],
    "inscriptions": {
      "characterCount": 0,
      "significance": { "en": "Uninscribed; artistry speaks for itself.", "zh": "无铭文，艺术本身即语言。" }
    },
    "culturalContext": {
      "ritualUse":       { "en": "Wine vessel for offerings.", "zh": "盛酒礼器。" },
      "socialFunction":  { "en": "High-status ritual paraphernalia.", "zh": "高等贵族礼器。" },
      "relatedConcepts": ["Shang bronze art", "ram symbolism", "southern Chu aesthetic"]
    },
    "narrativePoints": {
      "entry":  ["Four rams emerge from the corners", "One of China's most beloved bronzes", "Late Shang masterpiece"],
      "deeper": ["What rams symbolized in ancient ritual", "Regional style differences within the Shang", "How it was rediscovered"],
      "expert": ["Complex piece-mold assembly", "Surface decoration layering", "Comparisons with other four-animal zun"]
    },
    "relationships": {
      "sameDynasty":   [],
      "sameTechnique": ["artifact/da-ke-ding"]
    },
    "quickQuestions": {
      "en": ["Why four rams?", "How was it cast?", "Where was it found?"],
      "zh": ["为何是四只羊？", "如何铸造？", "在哪里出土？"]
    }
  },
  {
    "id": "artifact/xuande-incense-burner",
    "type": "BronzeWare",
    "name": { "en": "Xuande Incense Burner", "zh": "宣德炉" },
    "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Xuande%20bronze%20incense%20burner%20Ming%20dynasty%20polished%20surface%20elegant%20form&image_size=landscape_16_9",
    "hallId": "hall/bronze-gallery",
    "dynastyId": "dynasty/ming",
    "personIds": ["person/xuande-emperor"],
    "period": {
      "start": 1426, "end": 1435,
      "label": { "en": "Xuande reign, 1426-1435", "zh": "明宣德年间（1426—1435）" }
    },
    "dimensions": {
      "height": { "value": 8.5, "unit": "cm" }
    },
    "material":   ["bronze", "gold", "silver"],
    "techniques": ["cire perdue casting", "alloy polishing"],
    "inscriptions": {
      "characterCount": 6,
      "significance": { "en": "Bears the reign mark of the Xuande emperor.", "zh": "镌有宣德款识。" }
    },
    "culturalContext": {
      "ritualUse":       { "en": "Incense burning in scholar's studios and Buddhist altars.", "zh": "文房与佛堂焚香用具。" },
      "socialFunction":  { "en": "Object of literati connoisseurship.", "zh": "文人鉴藏之物。" },
      "relatedConcepts": ["Ming connoisseurship", "incense culture", "Xuande imperial workshops"]
    },
    "narrativePoints": {
      "entry":  ["A palm-sized imperial treasure", "Famously hard to authenticate", "Fragrance vessel for emperors and monks"],
      "deeper": ["The alloy recipe and why imitations abound", "Xuande imperial workshop production", "Literati taste culture"],
      "expert": ["Metallurgical analysis of patina layers", "Dating methods for reign-marked bronzes", "Regional imitation schools"]
    },
    "relationships": {
      "sameDynasty": []
    },
    "quickQuestions": {
      "en": ["Why are Xuande burners famous?", "How do experts spot fakes?", "What was burned in it?"],
      "zh": ["宣德炉为何出名？", "如何辨真伪？", "用来焚烧什么？"]
    }
  },
  {
    "id": "artifact/ming-blue-white-vase",
    "type": "Ceramic",
    "name": { "en": "Ming Blue-and-White Vase", "zh": "明青花瓶" },
    "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Ming%20dynasty%20blue%20and%20white%20porcelain%20vase%20cobalt%20decoration%20elegant&image_size=landscape_16_9",
    "hallId": "hall/ceramics-gallery",
    "dynastyId": "dynasty/ming",
    "personIds": [],
    "period": {
      "start": 1426, "end": 1435,
      "label": { "en": "Xuande reign, 1426-1435", "zh": "明宣德年间（1426—1435）" }
    },
    "dimensions": {
      "height": { "value": 29.0, "unit": "cm" }
    },
    "material":   ["porcelain", "cobalt blue pigment"],
    "techniques": ["underglaze cobalt painting"],
    "culturalContext": {
      "ritualUse":       { "en": "Decorative and ceremonial use at court.", "zh": "宫廷装饰与典礼用器。" },
      "socialFunction":  { "en": "Tribute and trade commodity across Asia.", "zh": "东亚贸易与朝贡品。" },
      "relatedConcepts": ["Jingdezhen kilns", "Islamic cobalt trade", "maritime silk road"]
    },
    "narrativePoints": {
      "entry":  ["The pottery that set a global style", "Cobalt blue from Persia on Chinese porcelain", "A vase that launched a trade network"],
      "deeper": ["Why cobalt had to come from Persia", "Jingdezhen imperial kiln organization", "Ming export networks"],
      "expert": ["Mineral spectroscopy and cobalt sourcing", "Kiln firing temperature control", "Xuande vs. other reign comparisons"]
    },
    "relationships": {
      "sameDynasty": ["artifact/xuande-incense-burner"]
    },
    "quickQuestions": {
      "en": ["Why blue and white?", "Where was it made?", "How was it traded?"],
      "zh": ["为何是青花？", "在哪里烧制？", "如何流通？"]
    }
  }
]
```

- [ ] **Step 2: Validate**

Run:
```bash
python -c "
import json, jsonschema
schema = json.load(open('data/ontology/schemas/artifact.schema.json'))
data   = json.load(open('data/ontology/artifacts.json'))
for item in data:
    jsonschema.validate(item, schema)
print(f'{len(data)} artifacts validated')
"
```
Expected: `5 artifacts validated`

- [ ] **Step 3: Commit data files**

```bash
git add data/ontology/halls.json data/ontology/dynasties.json data/ontology/persons.json data/ontology/artifacts.json
git commit -m "feat(ontology): author halls/dynasties/persons/artifacts initial dataset"
```

---

### Task 10: Add VS Code schema associations

**Files:**
- Create: `.vscode/settings.json`

- [ ] **Step 1: Create file**

```json
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

- [ ] **Step 2: Commit**

```bash
git add .vscode/settings.json
git commit -m "chore: VS Code JSON schema associations for ontology files"
```

---

### Task 11: Add Pydantic models

**Files:**
- Create: `backend/ontology/__init__.py`
- Create: `backend/ontology/models.py`

- [ ] **Step 1: Create package marker**

Create empty `backend/ontology/__init__.py`:

```python
"""Ontology package: load, validate, and resolve references across
hall/dynasty/person/artifact entities."""
```

- [ ] **Step 2: Write the models**

Create `backend/ontology/models.py`:

```python
"""Pydantic v2 models that mirror data/ontology/schemas/*.schema.json."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BilingualString(BaseModel):
    model_config = ConfigDict(extra="forbid")
    en: str = Field(min_length=1)
    zh: str = Field(min_length=1)


class BilingualList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    en: List[str]
    zh: List[str]


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: int
    end: int
    label: BilingualString


class Hall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^hall/[a-z0-9-]+$")
    name: BilingualString
    floor: int = Field(ge=0)
    theme: Optional[BilingualString] = None


class Dynasty(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^dynasty/[a-z0-9-]+$")
    name: BilingualString
    period: Period
    predecessor: Optional[str] = Field(default=None, pattern=r"^dynasty/[a-z0-9-]+$")
    successor:   Optional[str] = Field(default=None, pattern=r"^dynasty/[a-z0-9-]+$")
    shortDesc: Optional[BilingualString] = None


class Person(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^person/[a-z0-9-]+$")
    name: BilingualString
    role: BilingualString
    dynastyId: str = Field(pattern=r"^dynasty/[a-z0-9-]+$")
    shortDesc: Optional[BilingualString] = None


class Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float
    unit: str


class Inscriptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterCount: int = Field(ge=0)
    significance: Optional[BilingualString] = None


class CulturalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ritualUse:        Optional[BilingualString] = None
    socialFunction:   Optional[BilingualString] = None
    relatedConcepts:  List[str] = Field(default_factory=list)


class NarrativePoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry:  List[str] = Field(min_length=2)
    deeper: List[str] = Field(min_length=2)
    expert: List[str] = Field(min_length=2)


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^artifact/[a-z0-9-]+$")
    type: str
    name: BilingualString
    imageUrl: Optional[str] = None
    hallId: str = Field(pattern=r"^hall/[a-z0-9-]+$")
    dynastyId: str = Field(pattern=r"^dynasty/[a-z0-9-]+$")
    personIds: List[str] = Field(default_factory=list)
    period: Optional[Period] = None
    dimensions: Dict[str, Dimension] = Field(default_factory=dict)
    material:   List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    inscriptions: Optional[Inscriptions] = None
    culturalContext: Optional[CulturalContext] = None
    narrativePoints: Optional[NarrativePoints] = None
    relationships: Dict[str, List[str]] = Field(default_factory=dict)
    quickQuestions: Optional[BilingualList] = None
```

- [ ] **Step 3: Smoke-test the models load**

Run: `cd backend && source venv/bin/activate && python -c "from ontology import models; print('OK')"`
Expected: `OK`

---

### Task 12: Write the ontology loader

**Files:**
- Create: `backend/ontology/loader.py`

- [ ] **Step 1: Create loader**

```python
"""Load, schema-validate, and backfill ontology data at startup.

Fails fast with a descriptive message on any inconsistency. Exposes
dicts keyed by entity id for O(1) lookup at runtime.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import jsonschema
from pydantic import ValidationError

from . import models

ONTOLOGY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "ontology"
SCHEMAS_DIR  = ONTOLOGY_DIR / "schemas"


def _load_json(path: Path) -> list:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_schema(items: list, schema_name: str, source: Path) -> None:
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for i, item in enumerate(items):
        errors = sorted(validator.iter_errors(item), key=lambda e: list(e.path))
        if errors:
            msgs = "\n".join(f"  - {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in errors)
            raise RuntimeError(f"Schema violation in {source.name} item #{i} (id={item.get('id','?')}):\n{msgs}")


class Ontology:
    """Loaded, validated, and indexed ontology."""

    def __init__(
        self,
        halls: Dict[str, models.Hall],
        dynasties: Dict[str, models.Dynasty],
        persons: Dict[str, models.Person],
        artifacts: Dict[str, models.Artifact],
    ) -> None:
        self.halls = halls
        self.dynasties = dynasties
        self.persons = persons
        self.artifacts = artifacts

    def artifact_ids(self) -> List[str]:
        return list(self.artifacts.keys())


def load() -> Ontology:
    """Load all four entity files, validate against schemas + Pydantic,
    ensure cross-references resolve, and backfill bidirectional relations.
    """
    pairs = [
        ("halls.json",    "hall.schema.json",    models.Hall),
        ("dynasties.json","dynasty.schema.json", models.Dynasty),
        ("persons.json",  "person.schema.json",  models.Person),
        ("artifacts.json","artifact.schema.json",models.Artifact),
    ]
    parsed: Dict[str, Dict[str, object]] = {}
    for filename, schema, model_cls in pairs:
        path = ONTOLOGY_DIR / filename
        raw = _load_json(path)
        _validate_schema(raw, schema, path)
        try:
            items = [model_cls.model_validate(item) for item in raw]
        except ValidationError as exc:
            raise RuntimeError(f"Pydantic validation failed in {filename}:\n{exc}") from exc
        parsed[filename] = {it.id: it for it in items}

    halls     = parsed["halls.json"]
    dynasties = parsed["dynasties.json"]
    persons   = parsed["persons.json"]
    artifacts = parsed["artifacts.json"]

    # Cross-reference integrity.
    for p in persons.values():
        if p.dynastyId not in dynasties:
            raise RuntimeError(f"Person {p.id} references missing dynasty {p.dynastyId}")
    for a in artifacts.values():
        if a.hallId not in halls:
            raise RuntimeError(f"Artifact {a.id} references missing hall {a.hallId}")
        if a.dynastyId not in dynasties:
            raise RuntimeError(f"Artifact {a.id} references missing dynasty {a.dynastyId}")
        for pid in a.personIds:
            if pid not in persons:
                raise RuntimeError(f"Artifact {a.id} references missing person {pid}")
        for kind, targets in a.relationships.items():
            for target in targets:
                if target not in artifacts:
                    raise RuntimeError(f"Artifact {a.id}.relationships.{kind} -> missing {target}")

    # Backfill bidirectional relationships so authors only need to write one side.
    for a in list(artifacts.values()):
        for kind, targets in list(a.relationships.items()):
            for target in targets:
                target_rel = artifacts[target].relationships.setdefault(kind, [])
                if a.id not in target_rel:
                    target_rel.append(a.id)

    return Ontology(halls=halls, dynasties=dynasties, persons=persons, artifacts=artifacts)


def load_or_exit() -> Ontology:
    """Entry point for main.py startup: print error and exit on failure."""
    try:
        return load()
    except Exception as exc:
        print(f"[ontology] FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 2: Smoke-test the loader**

Run:
```bash
cd backend && source venv/bin/activate && python -c "
from ontology.loader import load
ont = load()
print(f'halls={len(ont.halls)} dynasties={len(ont.dynasties)} persons={len(ont.persons)} artifacts={len(ont.artifacts)}')
da_ke = ont.artifacts['artifact/da-ke-ding']
print('da-ke-ding.hallId:', da_ke.hallId)
print('da-ke-ding.relationships:', dict(da_ke.relationships))
# Backfill check: mao-gong-ding does not exist in our dataset, so we test with an existing pair.
siyang = ont.artifacts['artifact/si-yang-fang-zun']
print('si-yang-fang-zun.relationships:', dict(siyang.relationships))
"
```
Expected output includes `halls=2 dynasties=11 persons=3 artifacts=5` and shows that `si-yang-fang-zun.relationships.sameTechnique` contains `artifact/da-ke-ding` (authored) and that the backfill mirrored it on `da-ke-ding.sameTechnique`.

Note: artifacts.json references `artifact/mao-gong-ding` and `artifact/san-shi-pan` in Da Ke Ding's `sameDynasty` — these don't exist in the 5-artifact dataset. Fix now by removing those entries from Da Ke Ding's `relationships.sameDynasty` so integrity passes. Replace the line:

```json
"sameDynasty":   ["artifact/mao-gong-ding", "artifact/san-shi-pan"],
```

with:

```json
"sameDynasty":   [],
```

Re-run the smoke test. Expected: no error.

- [ ] **Step 3: Commit loader + models**

```bash
git add backend/ontology/ data/ontology/artifacts.json
git commit -m "feat(ontology): add Pydantic models and validating loader"
```

---

### Task 13: Write integrity test suite

**Files:**
- Create: `backend/test_ontology_integrity.py`

- [ ] **Step 1: Write the test**

```python
"""Ontology data integrity tests.

Run: python test_ontology_integrity.py
"""
from __future__ import annotations

import sys


def test_loads_without_errors():
    from ontology.loader import load
    ont = load()
    assert len(ont.halls) >= 2
    assert len(ont.dynasties) >= 4
    assert len(ont.persons) >= 3
    assert len(ont.artifacts) >= 5
    print(f"PASS load: halls={len(ont.halls)} dynasties={len(ont.dynasties)} persons={len(ont.persons)} artifacts={len(ont.artifacts)}")


def test_narrative_points_non_empty():
    from ontology.loader import load
    ont = load()
    for a in ont.artifacts.values():
        if a.narrativePoints is None:
            continue
        for depth in ("entry", "deeper", "expert"):
            points = getattr(a.narrativePoints, depth)
            assert len(points) >= 2, f"{a.id}.narrativePoints.{depth} has {len(points)} items, need >=2"
    print("PASS narrative_points non-empty")


def test_bilingual_fields_complete():
    from ontology.loader import load
    ont = load()
    for a in ont.artifacts.values():
        assert a.name.en and a.name.zh, f"{a.id}.name missing translation"
        if a.quickQuestions:
            assert a.quickQuestions.en and a.quickQuestions.zh, f"{a.id}.quickQuestions missing translation"
    for d in ont.dynasties.values():
        assert d.name.en and d.name.zh, f"{d.id}.name missing translation"
    print("PASS bilingual fields")


def test_bidirectional_relationships_symmetric():
    from ontology.loader import load
    ont = load()
    for a in ont.artifacts.values():
        for kind, targets in a.relationships.items():
            for target in targets:
                other = ont.artifacts[target].relationships.get(kind, [])
                assert a.id in other, f"{target}.relationships.{kind} missing back-ref to {a.id}"
    print("PASS bidirectional backfill")


if __name__ == "__main__":
    failures = 0
    for t in (test_loads_without_errors, test_narrative_points_non_empty,
              test_bilingual_fields_complete, test_bidirectional_relationships_symmetric):
        try:
            t()
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failures += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            failures += 1
    sys.exit(1 if failures else 0)
```

- [ ] **Step 2: Run tests**

Run: `cd backend && source venv/bin/activate && python test_ontology_integrity.py`
Expected: 4 PASS lines and exit 0.

- [ ] **Step 3: Commit**

```bash
git add backend/test_ontology_integrity.py
git commit -m "test(ontology): integrity tests for data and bidirectional refs"
```

---

### Task 14: Wire loader into main.py and delete old exhibits.json

**Files:**
- Modify: `backend/main.py`
- Delete: `data/exhibits.json`

- [ ] **Step 1: Replace the exhibits loading and endpoints**

In `backend/main.py`, locate the block near the top:

```python
# Load exhibit data
DATA_PATH = Path(__file__).parent.parent / "data" / "exhibits.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    EXHIBITS = json.load(f)

# Create simplified ID mapping for easier API usage
EXHIBIT_ID_MAP = {ex["@id"]: ex for ex in EXHIBITS}
EXHIBIT_SHORT_ID_MAP = {ex["@id"].replace("/", "-"): ex for ex in EXHIBITS}
```

Replace it with:

```python
# Ontology-backed exhibit store.
from ontology.loader import load_or_exit
ONTOLOGY = load_or_exit()

def _artifact_list() -> list[dict]:
    """Backward-compatible list shape for GET /exhibits."""
    out = []
    for a in ONTOLOGY.artifacts.values():
        hall = ONTOLOGY.halls[a.hallId]
        dyn  = ONTOLOGY.dynasties[a.dynastyId]
        out.append({
            "id": a.id,
            "originalId": a.id,
            "type": a.type,
            "name": a.name.model_dump(),
            "imageUrl": a.imageUrl,
            "hallId": a.hallId,
            "dynastyId": a.dynastyId,
            "personIds": a.personIds,
            # legacy flat fields, deprecated but returned for one cycle
            "hall": hall.name.en,
            "dynasty": dyn.name.en,
            "period": a.period.label.en if a.period else None,
            "quickQuestions": a.quickQuestions.en if a.quickQuestions else [],
        })
    return out
```

Then locate the existing `/exhibits` GET handler and the artifact lookup helper(s). Replace them so all exhibit ID lookups go through `ONTOLOGY.artifacts` rather than `EXHIBIT_ID_MAP`. Search `main.py` for usages of `EXHIBIT_ID_MAP`, `EXHIBIT_SHORT_ID_MAP`, and `EXHIBITS`, and rewrite each to use `ONTOLOGY.artifacts[id]`. For the `/exhibits` list endpoint, call `_artifact_list()`.

- [ ] **Step 2: Verify the server still boots**

Run: `cd backend && source venv/bin/activate && python -c "from main import app; print('OK')"`
Expected: `OK`.

- [ ] **Step 3: Smoke-test GET /exhibits via the ASGI client**

Run:
```bash
cd backend && source venv/bin/activate && python -c "
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
async def run():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://t') as c:
        r = await c.get('/exhibits')
        print('status:', r.status_code)
        data = r.json()
        print('count:', len(data))
        print('first id:', data[0]['id'])
asyncio.run(run())
"
```
Expected: `status: 200`, `count: 5`, `first id: artifact/da-ke-ding`.

- [ ] **Step 4: Delete the old file**

```bash
git rm data/exhibits.json
```

- [ ] **Step 5: Commit phase 1 completion**

```bash
git add backend/main.py
git commit -m "feat(ontology): boot from new ontology package; drop exhibits.json"
```

---

## Phase 2 — Resolver and new endpoints

### Task 15: Write the resolver

**Files:**
- Create: `backend/ontology/resolver.py`

- [ ] **Step 1: Create resolver**

```python
"""One-level reference expansion for artifact detail responses."""
from __future__ import annotations

from typing import Any, Dict

from . import models


def _bilingual(b: models.BilingualString | None) -> Dict[str, str] | None:
    return b.model_dump() if b else None


def expand_artifact(artifact: models.Artifact, ontology) -> Dict[str, Any]:
    """Return the artifact serialized with hall / dynasty / persons
    objects substituted in place of bare ID fields.

    Does NOT recurse further: nested objects appear as summaries only,
    not with their own fully-expanded references.
    """
    hall = ontology.halls[artifact.hallId]
    dyn  = ontology.dynasties[artifact.dynastyId]
    persons_full = [ontology.persons[pid] for pid in artifact.personIds]

    data = artifact.model_dump()
    data.pop("hallId", None)
    data.pop("dynastyId", None)
    data.pop("personIds", None)

    data["hall"] = {
        "id":   hall.id,
        "name": hall.name.model_dump(),
        "floor": hall.floor,
        "theme": _bilingual(hall.theme),
    }
    data["dynasty"] = {
        "id": dyn.id,
        "name":   dyn.name.model_dump(),
        "period": dyn.period.model_dump(),
        "predecessor": dyn.predecessor,
        "successor":   dyn.successor,
        "shortDesc":   _bilingual(dyn.shortDesc),
    }
    data["persons"] = [
        {
            "id":   p.id,
            "name": p.name.model_dump(),
            "role": p.role.model_dump(),
            "dynastyId": p.dynastyId,
            "shortDesc": _bilingual(p.shortDesc),
        }
        for p in persons_full
    ]
    return data
```

- [ ] **Step 2: Smoke-test resolver**

Run:
```bash
cd backend && source venv/bin/activate && python -c "
from ontology.loader import load
from ontology.resolver import expand_artifact
ont = load()
out = expand_artifact(ont.artifacts['artifact/da-ke-ding'], ont)
import json
print(json.dumps({
    'id': out['id'],
    'hall_id': out['hall']['id'],
    'dynasty_id': out['dynasty']['id'],
    'persons': [p['id'] for p in out['persons']],
    'hallId_dropped': 'hallId' not in out,
}, indent=2))
"
```
Expected: `hall_id='hall/bronze-gallery'`, `dynasty_id='dynasty/western-zhou'`, `persons=['person/king-li-of-zhou']`, `hallId_dropped=True`.

---

### Task 16: Add /ontology/* entity list endpoints

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Append endpoints**

Add below the existing endpoints in `main.py`:

```python
@app.get("/ontology/halls")
async def list_halls():
    return [h.model_dump() for h in ONTOLOGY.halls.values()]


@app.get("/ontology/dynasties")
async def list_dynasties():
    return [d.model_dump() for d in ONTOLOGY.dynasties.values()]


@app.get("/ontology/persons")
async def list_persons():
    return [p.model_dump() for p in ONTOLOGY.persons.values()]


@app.get("/ontology/halls/{hall_id:path}/artifacts")
async def list_hall_artifacts(hall_id: str):
    if hall_id not in ONTOLOGY.halls:
        raise HTTPException(status_code=404, detail="hall_not_found")
    return [a.model_dump() for a in ONTOLOGY.artifacts.values() if a.hallId == hall_id]


@app.get("/ontology/dynasties/{dynasty_id:path}/artifacts")
async def list_dynasty_artifacts(dynasty_id: str):
    if dynasty_id not in ONTOLOGY.dynasties:
        raise HTTPException(status_code=404, detail="dynasty_not_found")
    return [a.model_dump() for a in ONTOLOGY.artifacts.values() if a.dynastyId == dynasty_id]


@app.get("/ontology/persons/{person_id:path}/artifacts")
async def list_person_artifacts(person_id: str):
    if person_id not in ONTOLOGY.persons:
        raise HTTPException(status_code=404, detail="person_not_found")
    return [a.model_dump() for a in ONTOLOGY.artifacts.values() if person_id in a.personIds]
```

- [ ] **Step 2: Smoke test**

Run:
```bash
cd backend && source venv/bin/activate && python -c "
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
async def run():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://t') as c:
        for p in ['/ontology/halls', '/ontology/dynasties', '/ontology/persons',
                  '/ontology/dynasties/dynasty/western-zhou/artifacts']:
            r = await c.get(p)
            print(p, r.status_code, 'count=', len(r.json()))
asyncio.run(run())
"
```
Expected: four lines all `200` and counts > 0.

---

### Task 17: Expand /exhibits/{id} detail endpoint

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Replace / add the detail handler**

Find or create `@app.get("/exhibits/{exhibit_id:path}")`. Implement:

```python
from ontology.resolver import expand_artifact

@app.get("/exhibits/{exhibit_id:path}")
async def get_exhibit_detail(exhibit_id: str):
    if exhibit_id not in ONTOLOGY.artifacts:
        raise HTTPException(status_code=404, detail="exhibit_not_found")
    return expand_artifact(ONTOLOGY.artifacts[exhibit_id], ONTOLOGY)
```

- [ ] **Step 2: Smoke-test detail endpoint**

Run:
```bash
cd backend && source venv/bin/activate && python -c "
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
async def run():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://t') as c:
        r = await c.get('/exhibits/artifact/da-ke-ding')
        d = r.json()
        print('status:', r.status_code)
        print('hall.id:', d['hall']['id'])
        print('dynasty.id:', d['dynasty']['id'])
        print('persons:', [p['id'] for p in d['persons']])
asyncio.run(run())
"
```
Expected: `status: 200`, `hall.id: hall/bronze-gallery`, `dynasty.id: dynasty/western-zhou`, `persons: ['person/king-li-of-zhou']`.

---

### Task 18: Write resolver + API contract tests

**Files:**
- Create: `backend/test_ontology_resolver.py`
- Create: `backend/test_api_ontology.py`

- [ ] **Step 1: Write resolver test**

```python
"""Resolver behavior tests. Run: python test_ontology_resolver.py"""
from __future__ import annotations
import sys


def test_expand_drops_id_fields():
    from ontology.loader import load
    from ontology.resolver import expand_artifact
    ont = load()
    out = expand_artifact(ont.artifacts["artifact/da-ke-ding"], ont)
    assert "hallId" not in out
    assert "dynastyId" not in out
    assert "personIds" not in out
    assert out["hall"]["id"] == "hall/bronze-gallery"
    assert out["dynasty"]["id"] == "dynasty/western-zhou"
    assert [p["id"] for p in out["persons"]] == ["person/king-li-of-zhou"]
    print("PASS expand drops ids, adds resolved objects")


def test_expand_no_recursion():
    """Person objects in the expansion should not themselves be expanded."""
    from ontology.loader import load
    from ontology.resolver import expand_artifact
    ont = load()
    out = expand_artifact(ont.artifacts["artifact/da-ke-ding"], ont)
    person = out["persons"][0]
    assert "dynastyId" in person, "Person should keep its dynastyId string (no recursion)"
    assert "dynasty" not in person, "Person must not be further expanded"
    print("PASS expansion stops at one level")


if __name__ == "__main__":
    failures = 0
    for t in (test_expand_drops_id_fields, test_expand_no_recursion):
        try:
            t()
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failures += 1
    sys.exit(1 if failures else 0)
```

- [ ] **Step 2: Write API contract test**

Create `backend/test_api_ontology.py`:

```python
"""API contract tests for /ontology/* and /exhibits/* endpoints.

Run: python test_api_ontology.py
"""
from __future__ import annotations
import asyncio, sys


async def _get(c, path):
    r = await c.get(path)
    assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text}"
    return r.json()


async def run():
    from httpx import AsyncClient, ASGITransport
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        halls = await _get(c, "/ontology/halls")
        assert any(h["id"] == "hall/bronze-gallery" for h in halls)

        dynasties = await _get(c, "/ontology/dynasties")
        assert any(d["id"] == "dynasty/western-zhou" for d in dynasties)

        persons = await _get(c, "/ontology/persons")
        assert any(p["id"] == "person/king-li-of-zhou" for p in persons)

        wz_arts = await _get(c, "/ontology/dynasties/dynasty/western-zhou/artifacts")
        assert any(a["id"] == "artifact/da-ke-ding" for a in wz_arts)

        detail = await _get(c, "/exhibits/artifact/da-ke-ding")
        assert detail["hall"]["id"] == "hall/bronze-gallery"
        assert detail["dynasty"]["id"] == "dynasty/western-zhou"
        assert len(detail["persons"]) == 1

        missing = await c.get("/ontology/halls/hall/does-not-exist/artifacts")
        assert missing.status_code == 404

    print("PASS api contract")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except AssertionError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
```

- [ ] **Step 3: Run both tests**

Run:
```bash
cd backend && source venv/bin/activate && python test_ontology_resolver.py && python test_api_ontology.py
```
Expected: `PASS` lines from both, exit 0.

- [ ] **Step 4: Commit phase 2**

```bash
git add backend/ontology/resolver.py backend/main.py backend/test_ontology_resolver.py backend/test_api_ontology.py
git commit -m "feat(ontology): resolver, /ontology/* endpoints, expanded /exhibits detail"
```

---

## Phase 3 — Persona refactor

### Task 19: Extend persona file with depthTemplates

**Files:**
- Modify: `data/persona/current.json`

- [ ] **Step 1: Add depthTemplates to both `en` and `zh` persona blocks**

Insert inside `persona.en` (after `cultural_translator`):

```json
    "depthTemplates": {
      "entry": {
        "opener": "Start with a vivid hook — an analogy, a surprising comparison, or a concrete sensory image.",
        "focus":  "Emotion and imagination over precision; make it feel real and present.",
        "sentenceStyle": "Conversational, warm, 2–4 sentences before inviting a follow-up."
      },
      "deeper": {
        "opener": "Decode one specific detail (inscription, technique, or context) and explain why it matters.",
        "focus":  "Historical context and social meaning; connect the object to the world that made it.",
        "sentenceStyle": "Narrative but informative, 3–5 sentences; cite the fact you are interpreting."
      },
      "expert": {
        "opener": "Compare to other artifacts, or discuss craft, material, or scholarly debate.",
        "focus":  "Technique, material science, art history — precise and analytical.",
        "sentenceStyle": "Scholarly but accessible, 4–6 sentences; acknowledge uncertainty where appropriate."
      }
    },
```

Insert inside `persona.zh` (after `cultural_translator`):

```json
    "depthTemplates": {
      "entry": {
        "opener": "以生动的钩子开场——一个类比、令人惊讶的比较，或具象的感官意象。",
        "focus":  "感受与想象重于精确；让文物显得真实而当下。",
        "sentenceStyle": "对话式，温暖，2—4 句后抛出引导性追问。"
      },
      "deeper": {
        "opener": "解读一个具体细节（铭文、工艺或语境），并说明它为何重要。",
        "focus":  "历史语境与社会意义；把文物与孕育它的世界联系起来。",
        "sentenceStyle": "叙事但信息密集，3—5 句；指出你在解读哪一个事实。"
      },
      "expert": {
        "opener": "将此物与其他文物比较，或讨论工艺、材料、学术争论。",
        "focus":  "工艺、材料科学、艺术史——精确而分析性。",
        "sentenceStyle": "学术但易懂，4—6 句；对不确定之处明确标注。"
      }
    },
```

Bump `version` from `"v2.0"` to `"v2.1"`.

- [ ] **Step 2: Validate JSON parses**

Run: `python -c "import json; json.load(open('data/persona/current.json')); print('OK')"`
Expected: `OK`.

---

### Task 20: Rewrite persona.build_system_prompt

**Files:**
- Modify: `backend/persona.py`

- [ ] **Step 1: Add depth template accessor and new prompt builder**

Replace the existing `build_system_prompt` method. Locate the method in `persona.py` and swap it for this implementation:

```python
    def get_depth_template(self, language: str, depth_level: str) -> Dict:
        persona = self.get_persona(language)
        templates = persona.get("depthTemplates", {})
        return templates.get(depth_level) or templates.get("entry") or {
            "opener": "",
            "focus": "",
            "sentenceStyle": "",
        }

    def build_system_prompt(
        self,
        language: str = "en",
        depth_level: str = "entry",
        artifact_expanded: Optional[Dict] = None,
    ) -> str:
        persona = self.get_persona(language)
        dt = self.get_depth_template(language, depth_level)

        parts: list[str] = [
            persona["identity"],
            "",
            "### Personality",
            persona["personality"],
            "",
            "### Guiding Principles",
            *(f"- {p}" for p in persona["principles"]),
            "",
            "### Cultural Translator",
            *(f"- {i}" for i in persona.get("cultural_translator", [])),
            "",
            "### Boundaries",
            *(f"- {b}" for b in persona["boundaries"]),
            "",
            f"### How to respond at this depth level ({depth_level})",
            f"- {dt['opener']}",
            f"- Focus: {dt['focus']}",
            f"- Sentence style: {dt['sentenceStyle']}",
            "",
            f"### Fallback",
            persona["fallback"],
            "",
            f"### Tone",
            persona["tone"],
        ]

        if artifact_expanded:
            parts += ["", "### Current artifact (facts only — do not invent beyond this)"]
            parts.append(self._format_artifact_facts(artifact_expanded, language))

            nps = (artifact_expanded.get("narrativePoints") or {}).get(depth_level) or []
            if nps:
                parts += ["", "### Narrative points you may draw from"]
                parts += [f"- {p}" for p in nps]

            related = self._format_related_entities(artifact_expanded, language)
            if related:
                parts += ["", "### Related entities the visitor can ask about next", related]

        return "\n".join(parts)

    def _format_artifact_facts(self, a: Dict, language: str) -> str:
        lang = language if language in ("en", "zh") else "en"
        def bi(obj):
            return obj.get(lang) if isinstance(obj, dict) else obj

        lines = [f"- Name: {bi(a['name'])}"]
        hall = a.get("hall") or {}
        dyn  = a.get("dynasty") or {}
        if dyn:
            lines.append(f"- Dynasty: {bi(dyn.get('name'))} ({bi((dyn.get('period') or {}).get('label'))})")
        if hall:
            lines.append(f"- Hall: {bi(hall.get('name'))}, floor {hall.get('floor')}")
        if a.get("period"):
            lines.append(f"- Period: {bi(a['period'].get('label'))}")
        dims = a.get("dimensions") or {}
        if dims:
            dim_parts = [f"{k} {v['value']} {v['unit']}" for k, v in dims.items()]
            lines.append(f"- Dimensions: {', '.join(dim_parts)}")
        if a.get("material"):
            lines.append(f"- Material: {', '.join(a['material'])}")
        if a.get("techniques"):
            lines.append(f"- Techniques: {', '.join(a['techniques'])}")
        insc = a.get("inscriptions") or {}
        if insc:
            sig = bi(insc.get("significance")) if insc.get("significance") else ""
            lines.append(f"- Inscriptions: {insc.get('characterCount', 0)} characters. {sig}")
        ctx = a.get("culturalContext") or {}
        if ctx.get("ritualUse"):
            lines.append(f"- Ritual use: {bi(ctx.get('ritualUse'))}")
        if ctx.get("socialFunction"):
            lines.append(f"- Social function: {bi(ctx.get('socialFunction'))}")
        return "\n".join(lines)

    def _format_related_entities(self, a: Dict, language: str) -> str:
        lang = language if language in ("en", "zh") else "en"
        def bi(x):
            return x.get(lang) if isinstance(x, dict) else x

        chunks = []
        persons = a.get("persons") or []
        if persons:
            chunks.append("- Persons: " + ", ".join(bi(p["name"]) for p in persons))
        rels = a.get("relationships") or {}
        for kind, targets in rels.items():
            if targets:
                chunks.append(f"- {kind}: {', '.join(targets)}")
        return "\n".join(chunks)
```

Ensure `from typing import Dict, Optional` is imported at the top of the file.

- [ ] **Step 2: Smoke test**

Run:
```bash
cd backend && source venv/bin/activate && python -c "
from ontology.loader import load
from ontology.resolver import expand_artifact
from persona import persona_manager
ont = load()
exp = expand_artifact(ont.artifacts['artifact/da-ke-ding'], ont)
prompt = persona_manager.build_system_prompt('en', 'entry', exp)
print(prompt)
"
```
Expected: A prompt including sections `### How to respond at this depth level (entry)`, `### Current artifact (facts only...)`, `### Narrative points you may draw from`, and `### Related entities...`. No `storylines` key anywhere.

---

### Task 21: Update /chat endpoints to pass depth level

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Pass depth into build_system_prompt**

Find every call site of `persona_manager.build_system_prompt(...)` in `main.py`. Each currently passes `(language, exhibit_data)`. Update to pass `(language, depth_level, artifact_expanded)`:

```python
from ontology.resolver import expand_artifact  # at top if not yet imported

# In the /chat and /chat/stream handlers:
artifact = ONTOLOGY.artifacts.get(exhibit_id)
if artifact is None:
    raise HTTPException(status_code=404, detail="exhibit_not_found")
artifact_expanded = expand_artifact(artifact, ONTOLOGY)
system_prompt = persona_manager.build_system_prompt(
    language=language,
    depth_level=depth_level,
    artifact_expanded=artifact_expanded,
)
```

`depth_level` is already part of the request body (`body.get("depthLevel", "entry")`).

- [ ] **Step 2: Manual smoke test**

Run the server (`python main.py` in a separate terminal — Port 8080 free) and in another terminal:

```bash
curl -s -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"plan-test","exhibitId":"artifact/da-ke-ding","userInput":"Tell me about this","language":"en","depthLevel":"entry"}' \
  | python3 -m json.tool
```

Expected: A 200 response with a reply that reads like a museum storyteller hook (contains an analogy or sensory image). No schema errors.

Stop the server.

---

### Task 22: Prompt snapshot tests

**Files:**
- Create: `backend/test_prompt_snapshot.py`
- Create: `backend/tests/__snapshots__/.gitkeep`

- [ ] **Step 1: Create snapshots dir**

Run: `mkdir -p backend/tests/__snapshots__ && touch backend/tests/__snapshots__/.gitkeep`

- [ ] **Step 2: Write snapshot test**

Create `backend/test_prompt_snapshot.py`:

```python
"""Prompt snapshot tests.

On first run, approves the current prompt as the baseline. Later runs
diff against the baseline; mismatches fail (intentional changes are
approved by deleting the relevant snapshot file).

Run: python test_prompt_snapshot.py
Approve all:   python test_prompt_snapshot.py --update
"""
from __future__ import annotations
import difflib, os, sys
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "tests" / "__snapshots__"


def _check(name: str, actual: str, update: bool) -> bool:
    path = SNAPSHOT_DIR / f"{name}.txt"
    if not path.exists() or update:
        path.write_text(actual, encoding="utf-8")
        print(f"APPROVED {name}")
        return True
    expected = path.read_text(encoding="utf-8")
    if expected == actual:
        print(f"PASS     {name}")
        return True
    diff = "\n".join(difflib.unified_diff(
        expected.splitlines(), actual.splitlines(),
        fromfile=f"{name} (snapshot)", tofile=f"{name} (current)", lineterm=""
    ))
    print(f"FAIL     {name}\n{diff}")
    return False


def run(update: bool) -> int:
    from ontology.loader import load
    from ontology.resolver import expand_artifact
    from persona import persona_manager

    ont = load()
    exp = expand_artifact(ont.artifacts["artifact/da-ke-ding"], ont)

    ok = True
    for lang in ("en", "zh"):
        for level in ("entry", "deeper", "expert"):
            prompt = persona_manager.build_system_prompt(lang, level, exp)
            ok &= _check(f"da-ke-ding__{lang}__{level}", prompt, update)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run(update="--update" in sys.argv))
```

- [ ] **Step 3: Establish baseline**

Run: `cd backend && source venv/bin/activate && python test_prompt_snapshot.py`
Expected on first run: 6 `APPROVED` lines (one per language × depth).

- [ ] **Step 4: Commit phase 3**

```bash
git add data/persona/current.json backend/persona.py backend/main.py \
        backend/test_prompt_snapshot.py backend/tests/
git commit -m "feat(persona): decouple narrative templates; depth-aware prompt + snapshot tests"
```

---

## Phase 4 — Frontend integration

### Task 23: Update TypeScript types and list-view consumption

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Replace the `Exhibit` interface**

Locate the existing `Exhibit` interface near the top of `App.tsx` and replace it with:

```typescript
interface Bilingual { en: string; zh: string }
interface BilingualList { en: string[]; zh: string[] }

interface Exhibit {
  id: string
  originalId?: string
  type?: string
  name: Bilingual
  imageUrl?: string
  hallId: string
  dynastyId: string
  personIds: string[]
  // Legacy fields returned during the deprecation window:
  hall?: string
  dynasty?: string
  period?: string | { start: number; end: number; label: Bilingual }
  quickQuestions?: string[] | BilingualList
}

interface Hall    { id: string; name: Bilingual; floor: number; theme?: Bilingual }
interface Dynasty {
  id: string; name: Bilingual
  period: { start: number; end: number; label: Bilingual }
  predecessor?: string | null
  successor?:   string | null
  shortDesc?:   Bilingual | null
}
interface Person  {
  id: string; name: Bilingual; role: Bilingual
  dynastyId: string; shortDesc?: Bilingual | null
}
```

- [ ] **Step 2: Normalize the quickQuestions reads**

Find all places where `exhibit.quickQuestions` is used. Wrap with:

```typescript
const questions: string[] = Array.isArray(currentExhibit.quickQuestions)
  ? currentExhibit.quickQuestions
  : (currentExhibit.quickQuestions?.[language] ?? [])
```

Then use `questions` for rendering.

- [ ] **Step 3: Verify frontend compiles**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: ends with `✓ built in ...` and zero errors.

---

### Task 24: Add EntityChip component and chip rendering

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add drawer state inside `App` component**

Near the other `useState` declarations at the top of the `App` function, add:

```typescript
const [drawerTarget, setDrawerTarget] =
  useState<{ type: "hall" | "dynasty" | "person"; id: string } | null>(null)

const [halls,     setHalls]     = useState<Record<string, Hall>>({})
const [dynasties, setDynasties] = useState<Record<string, Dynasty>>({})
const [persons,   setPersons]   = useState<Record<string, Person>>({})
```

- [ ] **Step 2: Fetch the entity caches on mount**

Find the `useEffect` block that loads exhibits. Add a second effect:

```typescript
useEffect(() => {
  const toMap = <T extends { id: string }>(arr: T[]) =>
    Object.fromEntries(arr.map(x => [x.id, x]))
  Promise.all([
    fetch(`${API_BASE_URL}/ontology/halls`).then(r => r.json()),
    fetch(`${API_BASE_URL}/ontology/dynasties`).then(r => r.json()),
    fetch(`${API_BASE_URL}/ontology/persons`).then(r => r.json()),
  ]).then(([h, d, p]) => {
    setHalls(toMap(h)); setDynasties(toMap(d)); setPersons(toMap(p))
  }).catch(err => console.error("Failed to load ontology entities", err))
}, [])
```

- [ ] **Step 3: Add an inline EntityChip component above `function App()`**

```typescript
function EntityChip({
  label, onClick,
}: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center px-3 py-1 mr-2 mb-2 rounded-full text-sm bg-amber-50 text-amber-900 border border-amber-200 hover:bg-amber-100 transition"
    >
      {label}
    </button>
  )
}
```

- [ ] **Step 4: Render chips in the artifact detail view**

Locate the artifact detail JSX (search for `currentExhibit` being rendered as a detail card). Near the artifact name/image block, insert:

```tsx
{currentExhibit && (
  <div className="my-3">
    {currentExhibit.hallId && halls[currentExhibit.hallId] && (
      <EntityChip
        label={halls[currentExhibit.hallId].name[language]}
        onClick={() => setDrawerTarget({ type: "hall", id: currentExhibit.hallId })}
      />
    )}
    {currentExhibit.dynastyId && dynasties[currentExhibit.dynastyId] && (
      <EntityChip
        label={dynasties[currentExhibit.dynastyId].name[language]}
        onClick={() => setDrawerTarget({ type: "dynasty", id: currentExhibit.dynastyId })}
      />
    )}
    {(currentExhibit.personIds || []).map(pid => persons[pid] && (
      <EntityChip
        key={pid}
        label={persons[pid].name[language]}
        onClick={() => setDrawerTarget({ type: "person", id: pid })}
      />
    ))}
  </div>
)}
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: `✓ built in ...` with zero errors.

---

### Task 25: Add EntityDrawer component

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add the drawer component (inline)**

Above `function App()`:

```tsx
function EntityDrawer({
  target, onClose, language, halls, dynasties, persons, onPickExhibit,
}: {
  target: { type: "hall" | "dynasty" | "person"; id: string } | null
  onClose: () => void
  language: "en" | "zh"
  halls: Record<string, Hall>
  dynasties: Record<string, Dynasty>
  persons: Record<string, Person>
  onPickExhibit: (ex: Exhibit) => void
}) {
  const [relatedArtifacts, setRelatedArtifacts] = useState<Exhibit[]>([])

  useEffect(() => {
    if (!target) { setRelatedArtifacts([]); return }
    const { type, id } = target
    const base = `${API_BASE_URL}/ontology/${type}s/${id}/artifacts`
    fetch(base).then(r => r.json()).then(setRelatedArtifacts).catch(() => setRelatedArtifacts([]))
  }, [target])

  if (!target) return null
  const { type, id } = target

  let body: React.ReactNode = null
  if (type === "hall" && halls[id]) {
    const h = halls[id]
    body = (
      <>
        <h2 className="text-2xl font-semibold mb-2">{h.name[language]}</h2>
        <p className="text-sm text-gray-600 mb-4">
          {language === "en" ? `Floor ${h.floor}` : `${h.floor} 层`}
        </p>
        {h.theme && <p className="mb-4 italic">{h.theme[language]}</p>}
      </>
    )
  } else if (type === "dynasty" && dynasties[id]) {
    const d = dynasties[id]
    body = (
      <>
        <h2 className="text-2xl font-semibold mb-2">{d.name[language]}</h2>
        <p className="text-sm text-gray-600 mb-2">{d.period.label[language]}</p>
        <p className="text-sm text-gray-500 mb-4">
          {d.predecessor ? `← ${d.predecessor}` : ""} {d.successor ? `→ ${d.successor}` : ""}
        </p>
        {d.shortDesc && <p className="mb-4">{d.shortDesc[language]}</p>}
      </>
    )
  } else if (type === "person" && persons[id]) {
    const p = persons[id]
    body = (
      <>
        <h2 className="text-2xl font-semibold mb-2">{p.name[language]}</h2>
        <p className="text-sm text-gray-600 mb-4">{p.role[language]}</p>
        {p.shortDesc && <p className="mb-4">{p.shortDesc[language]}</p>}
      </>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <div className="w-full sm:w-96 bg-white p-6 shadow-xl overflow-y-auto">
        <button className="text-gray-500 mb-4" onClick={onClose}>✕</button>
        {body}
        <h3 className="text-lg font-medium mt-6 mb-2">
          {language === "en" ? "Related artifacts" : "相关展品"}
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {relatedArtifacts.map(ex => (
            <button
              key={ex.id}
              onClick={() => { onPickExhibit(ex); onClose() }}
              className="border rounded-lg p-2 text-left hover:bg-gray-50"
            >
              <div className="text-sm font-medium">{ex.name[language]}</div>
              <div className="text-xs text-gray-500">{ex.id.replace("artifact/", "")}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Mount EntityDrawer at the end of App's returned JSX**

Inside the main return, just before the closing wrapper (`</div>` of the outermost container), add:

```tsx
<EntityDrawer
  target={drawerTarget}
  onClose={() => setDrawerTarget(null)}
  language={language}
  halls={halls}
  dynasties={dynasties}
  persons={persons}
  onPickExhibit={(ex) => selectExhibit(ex)}
/>
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: `✓ built in ...` with zero errors.

- [ ] **Step 4: Manual browser smoke test**

Start backend (`cd backend && python main.py`), start frontend (`cd frontend && npm run dev`), open http://localhost:3000. Click into an artifact; three chips should appear; click each one; drawer slides in showing entity details + related artifacts; clicking a related artifact closes the drawer and switches the currently selected artifact.

- [ ] **Step 5: Commit phase 4**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): EntityChip + EntityDrawer for hall/dynasty/person"
```

---

## Phase 5 — Data expansion (5 → 15 artifacts)

Each of Tasks 26–30 adds a small batch and runs `test_ontology_integrity.py`. If the integrity test fails, the commit does not happen until the error is fixed.

### Task 26: Expand halls

**Files:**
- Modify: `data/ontology/halls.json`

- [ ] **Step 1: Add one more hall** (Chinese Painting Gallery).

Append to the array:

```json
,
{
  "id": "hall/painting-gallery",
  "name": { "en": "Chinese Painting Gallery", "zh": "中国书画馆" },
  "floor": 3,
  "theme": { "en": "A thousand years of Chinese painting and calligraphy",
             "zh": "千年中国书画艺术" }
}
```

- [ ] **Step 2: Run integrity test**

Run: `cd backend && source venv/bin/activate && python test_ontology_integrity.py`
Expected: 4 PASS.

---

### Task 27: Expand persons

**Files:**
- Modify: `data/ontology/persons.json`

- [ ] **Step 1: Add four more persons**

Append to the array:

```json
,
{
  "id": "person/qin-shi-huang",
  "name": { "en": "Qin Shi Huang", "zh": "秦始皇" },
  "role": { "en": "First emperor of unified China", "zh": "中国首位皇帝" },
  "dynastyId": "dynasty/qin",
  "shortDesc": { "en": "Unifier of China whose standardized script and measures built the imperial template.",
                 "zh": "统一中国的皇帝，标准化文字与度量，奠定帝国模板。" }
},
{
  "id": "person/han-wudi",
  "name": { "en": "Emperor Wu of Han", "zh": "汉武帝" },
  "role": { "en": "Han emperor and expansionist", "zh": "汉代皇帝与扩张者" },
  "dynastyId": "dynasty/han",
  "shortDesc": { "en": "Expanded Han territory and opened the Silk Road.",
                 "zh": "拓展汉疆，开通丝绸之路。" }
},
{
  "id": "person/song-huizong",
  "name": { "en": "Emperor Huizong of Song", "zh": "宋徽宗" },
  "role": { "en": "Song emperor and painter", "zh": "宋代皇帝与画家" },
  "dynastyId": "dynasty/song",
  "shortDesc": { "en": "Aesthete emperor whose patronage defined Song court art.",
                 "zh": "审美至上的皇帝，赞助定义了宋代宫廷艺术。" }
},
{
  "id": "person/kangxi-emperor",
  "name": { "en": "Kangxi Emperor", "zh": "康熙帝" },
  "role": { "en": "Qing emperor and cultural patron", "zh": "清代皇帝与文化赞助人" },
  "dynastyId": "dynasty/qing",
  "shortDesc": { "en": "Long-reigning emperor who consolidated Qing culture and sponsored scholarship.",
                 "zh": "在位最久的皇帝，巩固清代文化，扶持学术。" }
}
```

- [ ] **Step 2: Integrity test**

Run: `cd backend && source venv/bin/activate && python test_ontology_integrity.py`
Expected: 4 PASS.

---

### Task 28: Add artifacts batch 1 (Shang, Han, Tang)

**Files:**
- Modify: `data/ontology/artifacts.json`

- [ ] **Step 1: Append three new artifacts**

Append to the array:

```json
,
{
  "id": "artifact/zi-long-ding",
  "type": "BronzeWare",
  "name": { "en": "Zi Long Ding", "zh": "子龙鼎" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Shang%20dynasty%20Zi%20Long%20Ding%20bronze%20ritual%20cauldron%20with%20dragon%20motif&image_size=landscape_16_9",
  "hallId": "hall/bronze-gallery",
  "dynastyId": "dynasty/shang",
  "personIds": [],
  "period": { "start": -1200, "end": -1046,
              "label": { "en": "Late Shang, c. 12th–11th century BCE", "zh": "商代晚期" } },
  "dimensions": { "height": { "value": 103.0, "unit": "cm" }, "weight": { "value": 230.0, "unit": "kg" } },
  "material":   ["bronze"],
  "techniques": ["piece-mold casting"],
  "inscriptions": { "characterCount": 1, "significance":
                    { "en": "Bears the single-character clan mark 'Zi Long'.",
                      "zh": "带有族徽‘子龙’二字。" } },
  "culturalContext": {
    "ritualUse":       { "en": "Ancestral sacrifice.", "zh": "祭祖。" },
    "socialFunction":  { "en": "Clan identity and political authority.", "zh": "族群认同与政治权威。" },
    "relatedConcepts": ["Shang clan system", "totemic marks"]
  },
  "narrativePoints": {
    "entry":  ["One of the largest surviving Shang ding", "A dragon motif older than Chinese writing", "Once lost for centuries, recovered in 2006"],
    "deeper": ["Why clan marks matter for Shang social structure", "The long journey this vessel took abroad and back", "What the dragon motif represented"],
    "expert": ["Comparative analysis with other Shang ding", "Dating by alloy composition", "Authentication challenges for recovered artifacts"]
  },
  "relationships": {
    "sameDynasty":   ["artifact/si-yang-fang-zun"],
    "sameTechnique": ["artifact/da-ke-ding"]
  },
  "quickQuestions": {
    "en": ["Why is it called Zi Long?", "How was it rediscovered?", "How does it compare to Da Ke Ding?"],
    "zh": ["为何叫‘子龙’？", "如何重见天日？", "与大克鼎相比如何？"]
  }
},
{
  "id": "artifact/han-bronze-mirror",
  "type": "BronzeWare",
  "name": { "en": "Han TLV Bronze Mirror", "zh": "汉代规矩镜" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Han%20dynasty%20TLV%20bronze%20mirror%20with%20cosmic%20design&image_size=landscape_16_9",
  "hallId": "hall/bronze-gallery",
  "dynastyId": "dynasty/han",
  "personIds": ["person/han-wudi"],
  "period": { "start": -100, "end": 100,
              "label": { "en": "c. 100 BCE – 100 CE", "zh": "约公元前100年—公元100年" } },
  "dimensions": { "diameter": { "value": 18.2, "unit": "cm" } },
  "material":   ["bronze"],
  "techniques": ["piece-mold casting", "relief carving"],
  "inscriptions": { "characterCount": 24, "significance":
                    { "en": "Auspicious phrases about longevity and cosmic order.",
                      "zh": "长寿与宇宙秩序的吉语。" } },
  "culturalContext": {
    "ritualUse":       { "en": "Personal reflection and cosmological symbolism.", "zh": "照容与宇宙象征。" },
    "socialFunction":  { "en": "Everyday object for the elite.", "zh": "上层日用器。" },
    "relatedConcepts": ["Han cosmology", "TLV pattern", "wuxing"]
  },
  "narrativePoints": {
    "entry":  ["A mirror that shows the whole universe", "The letters T, L, V were here 2000 years before the Latin alphabet reached China", "Imagine reading your future in the reflection"],
    "deeper": ["What the T/L/V pattern encodes about Han cosmology", "Inscription conventions on Han mirrors", "From daily object to burial good"],
    "expert": ["Typology of TLV mirrors", "Alloy composition and reflectivity", "Iconographic evolution across the Han"]
  },
  "relationships": { "sameDynasty": [] },
  "quickQuestions": {
    "en": ["What do the T/L/V shapes mean?", "Who used it?", "Why is it reflective?"],
    "zh": ["T/L/V 形状含义？", "谁使用它？", "为何能照影？"]
  }
},
{
  "id": "artifact/tang-sancai-horse",
  "type": "Ceramic",
  "name": { "en": "Tang Sancai Horse", "zh": "唐三彩马" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Tang%20dynasty%20sancai%20three%20color%20glazed%20horse%20figurine%20vivid&image_size=landscape_16_9",
  "hallId": "hall/ceramics-gallery",
  "dynastyId": "dynasty/tang",
  "personIds": [],
  "period": { "start": 700, "end": 800,
              "label": { "en": "8th century CE", "zh": "公元8世纪" } },
  "dimensions": { "height": { "value": 66.5, "unit": "cm" } },
  "material":   ["earthenware", "lead glaze"],
  "techniques": ["three-color glazing", "mold-assembled figurine"],
  "culturalContext": {
    "ritualUse":       { "en": "Tomb burial good (mingqi).", "zh": "随葬明器。" },
    "socialFunction":  { "en": "Ostentatious display of elite status.", "zh": "炫耀贵族身份。" },
    "relatedConcepts": ["Tang cosmopolitanism", "Silk Road horses", "mingqi tradition"]
  },
  "narrativePoints": {
    "entry":  ["The most loved Tang ceramic figure", "Made to serve the dead in the afterlife", "Its colors have not faded in 1300 years"],
    "deeper": ["Why horses mattered so much in Tang society", "Sancai glaze chemistry", "What tomb excavations reveal about Tang life"],
    "expert": ["Lead glaze stability and firing temperatures", "Regional kiln origins of sancai", "Iconographic variations (camels, warriors, musicians)"]
  },
  "relationships": { "sameDynasty": [] },
  "quickQuestions": {
    "en": ["Why three colors?", "Was it buried in a tomb?", "Where was it made?"],
    "zh": ["为何三色？", "是随葬品吗？", "在哪里烧造？"]
  }
}
```

- [ ] **Step 2: Integrity test**

Run: `cd backend && source venv/bin/activate && python test_ontology_integrity.py`
Expected: 4 PASS. Artifact count is now 8.

---

### Task 29: Add artifacts batch 2 (Song, Yuan, Ming, Qing, Calligraphy)

**Files:**
- Modify: `data/ontology/artifacts.json`

- [ ] **Step 1: Append four more artifacts to round out the dataset**

```json
,
{
  "id": "artifact/ru-ware-bowl",
  "type": "Ceramic",
  "name": { "en": "Ru-ware Bowl", "zh": "汝窑碗" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Song%20dynasty%20Ru%20ware%20celadon%20bowl%20pale%20blue%20delicate&image_size=landscape_16_9",
  "hallId": "hall/ceramics-gallery",
  "dynastyId": "dynasty/song",
  "personIds": ["person/song-huizong"],
  "period": { "start": 1086, "end": 1125,
              "label": { "en": "Late 11th – early 12th century", "zh": "11世纪末至12世纪初" } },
  "dimensions": { "diameter": { "value": 12.5, "unit": "cm" }, "height": { "value": 5.2, "unit": "cm" } },
  "material":   ["porcelain", "iron-based glaze"],
  "techniques": ["imperial kiln firing", "celadon glaze"],
  "culturalContext": {
    "ritualUse":       { "en": "Scholar's tea wares and imperial use.", "zh": "文人茶具与宫廷器。" },
    "socialFunction":  { "en": "Supreme object of Song connoisseurship.", "zh": "宋代鉴藏之冠。" },
    "relatedConcepts": ["Song aesthetics", "imperial kiln", "ice crackle"]
  },
  "narrativePoints": {
    "entry":  ["Fewer than a hundred Ru pieces survive worldwide", "A color that poets compared to 'sky after rain'", "Held tea for Song emperors"],
    "deeper": ["Why Emperor Huizong obsessed over celadon", "The fragile politics of imperial kilns", "Crackle patterns as aesthetic signature"],
    "expert": ["Iron-titanium glaze chemistry", "Firing atmosphere control", "Scientific authentication methods"]
  },
  "relationships": {
    "sameDynasty": []
  },
  "quickQuestions": {
    "en": ["Why is Ru ware so rare?", "Who used it?", "What is the signature color?"],
    "zh": ["为何汝窑珍稀？", "谁使用？", "标志性颜色？"]
  }
},
{
  "id": "artifact/yuan-blue-white-plate",
  "type": "Ceramic",
  "name": { "en": "Yuan Blue-and-White Plate", "zh": "元青花盘" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Yuan%20dynasty%20blue%20and%20white%20porcelain%20plate%20cobalt%20dragon&image_size=landscape_16_9",
  "hallId": "hall/ceramics-gallery",
  "dynastyId": "dynasty/yuan",
  "personIds": [],
  "period": { "start": 1300, "end": 1368,
              "label": { "en": "14th century CE", "zh": "公元14世纪" } },
  "dimensions": { "diameter": { "value": 45.0, "unit": "cm" } },
  "material":   ["porcelain", "cobalt blue pigment"],
  "techniques": ["underglaze cobalt painting"],
  "culturalContext": {
    "ritualUse":       { "en": "Export ware and court use.", "zh": "外销与宫廷用。" },
    "socialFunction":  { "en": "Prestige object traded across Eurasia.", "zh": "横跨欧亚的贵重商品。" },
    "relatedConcepts": ["Persian cobalt trade", "Yuan globalization", "Jingdezhen pioneers"]
  },
  "narrativePoints": {
    "entry":  ["The ancestor of all blue-and-white porcelain", "Made for Persian and Middle Eastern tastes", "A single piece once sold for over $20M"],
    "deeper": ["How Persian patterns shaped Chinese decoration", "Yuan kiln organization at Jingdezhen", "Export networks across the Mongol empire"],
    "expert": ["Cobalt mineralogy and sourcing", "Comparative dating with Ming wares", "Archaeological finds in shipwrecks"]
  },
  "relationships": {
    "sameDynasty":   [],
    "sameTechnique": ["artifact/ming-blue-white-vase"]
  },
  "quickQuestions": {
    "en": ["Why was it made for export?", "Where was the cobalt from?", "How is it different from Ming?"],
    "zh": ["为何外销？", "钴料来自哪里？", "与明代有何不同？"]
  }
},
{
  "id": "artifact/huai-su-autobiography",
  "type": "Calligraphy",
  "name": { "en": "Huai Su Autobiography (Facsimile)", "zh": "怀素自叙帖（摹本）" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Huai%20Su%20cursive%20calligraphy%20scroll%20Tang%20dynasty%20wild%20ink&image_size=landscape_16_9",
  "hallId": "hall/painting-gallery",
  "dynastyId": "dynasty/tang",
  "personIds": [],
  "period": { "start": 777, "end": 777,
              "label": { "en": "777 CE", "zh": "公元777年" } },
  "dimensions": { "length": { "value": 755.0, "unit": "cm" } },
  "material":   ["ink", "paper"],
  "techniques": ["wild cursive script (kuangcao)"],
  "culturalContext": {
    "ritualUse":       { "en": "Personal artistic expression.", "zh": "个人艺术表达。" },
    "socialFunction":  { "en": "Model for subsequent Chinese calligraphic tradition.", "zh": "奠定后世草书典范。" },
    "relatedConcepts": ["kuangcao", "Tang Buddhism", "Zen spontaneity"]
  },
  "narrativePoints": {
    "entry":  ["Writing so wild it looks like abstract art", "A monk's personal storyscroll", "One of the most influential scrolls in Chinese history"],
    "deeper": ["Why Huai Su's cursive broke the rules", "How Zen influenced his style", "The scroll's thousand-year provenance"],
    "expert": ["Brush dynamics and ink concentration", "Transmission and authentication", "Comparisons with Zhang Xu"]
  },
  "relationships": {
    "sameDynasty": []
  },
  "quickQuestions": {
    "en": ["Can you even read it?", "Who was Huai Su?", "Why is it so celebrated?"],
    "zh": ["真的能读懂吗？", "怀素是谁？", "为何如此出名？"]
  }
},
{
  "id": "artifact/qianlong-jade-scroll",
  "type": "Jade",
  "name": { "en": "Qianlong-inscribed Jade Scroll", "zh": "清乾隆御题玉册" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Qing%20dynasty%20Qianlong%20inscribed%20jade%20scroll%20ornate%20carving&image_size=landscape_16_9",
  "hallId": "hall/painting-gallery",
  "dynastyId": "dynasty/qing",
  "personIds": ["person/kangxi-emperor"],
  "period": { "start": 1755, "end": 1796,
              "label": { "en": "Qianlong reign, 1735-1796", "zh": "清乾隆年间" } },
  "dimensions": { "length": { "value": 27.0, "unit": "cm" }, "width": { "value": 12.0, "unit": "cm" } },
  "material":   ["nephrite jade", "gold inlay"],
  "techniques": ["jade carving", "gold inlay inscription"],
  "inscriptions": { "characterCount": 120, "significance":
                    { "en": "Qianlong's own poem praising a Song painting.",
                      "zh": "乾隆为一幅宋画所题的御诗。" } },
  "culturalContext": {
    "ritualUse":       { "en": "Imperial commentary on classical art.", "zh": "帝王对经典艺术的题跋。" },
    "socialFunction":  { "en": "Display of imperial connoisseurship and power.", "zh": "展示帝王鉴藏与权威。" },
    "relatedConcepts": ["Qing imperial collecting", "text as artifact", "Qianlong's aesthetic program"]
  },
  "narrativePoints": {
    "entry":  ["The emperor who left poems on everything", "A piece of jade carrying imperial handwriting", "Part of Qianlong's massive art collecting project"],
    "deeper": ["Why Qianlong inscribed so many artworks", "Jade as medium for imperial text", "The tension between reverence and vandalism in Qing collecting"],
    "expert": ["Jade sourcing and carving techniques", "Gold inlay preservation", "Studies of Qianlong's inscription patterns"]
  },
  "relationships": {
    "sameDynasty": []
  },
  "quickQuestions": {
    "en": ["Why jade for an inscription?", "Who was the emperor Qianlong?", "Is this considered vandalism today?"],
    "zh": ["为何刻在玉上？", "乾隆是谁？", "这算不算破坏文物？"]
  }
}
```

- [ ] **Step 2: Integrity test**

Run: `cd backend && source venv/bin/activate && python test_ontology_integrity.py`
Expected: 4 PASS. Artifact count is now 12.

---

### Task 30: Add three more artifacts to reach 15

**Files:**
- Modify: `data/ontology/artifacts.json`

- [ ] **Step 1: Append three more artifacts**

```json
,
{
  "id": "artifact/warring-states-coin",
  "type": "Coin",
  "name": { "en": "Warring States Knife Coin", "zh": "战国刀币" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Warring%20states%20bronze%20knife%20money%20coin%20ancient%20China&image_size=landscape_16_9",
  "hallId": "hall/bronze-gallery",
  "dynastyId": "dynasty/warring-states",
  "personIds": [],
  "period": { "start": -475, "end": -221,
              "label": { "en": "475–221 BCE", "zh": "公元前475—前221年" } },
  "dimensions": { "length": { "value": 18.0, "unit": "cm" } },
  "material":   ["bronze"],
  "techniques": ["mold casting"],
  "culturalContext": {
    "ritualUse":       { "en": "Everyday trade.", "zh": "日常贸易。" },
    "socialFunction":  { "en": "Pre-unification regional currency.", "zh": "统一前区域货币。" },
    "relatedConcepts": ["pre-Qin economy", "regional currencies", "mint variation"]
  },
  "narrativePoints": {
    "entry":  ["Money shaped like a knife", "Each state had its own currency before Qin unified them", "A tool, a weapon, a wallet — all in one shape"],
    "deeper": ["Regional currency systems before unification", "Why Qi and Yan chose knife shapes", "From barter to metal money"],
    "expert": ["Typology of knife coin variants", "Alloy composition by mint", "Circulation patterns in archaeology"]
  },
  "relationships": {
    "sameDynasty": ["artifact/shang-yang-sheng"]
  },
  "quickQuestions": {
    "en": ["Why was money shaped like a knife?", "Who used it?", "How did Qin change this?"],
    "zh": ["为何钱币做成刀形？", "谁使用？", "秦统一后如何变？"]
  }
},
{
  "id": "artifact/qing-lacquer-box",
  "type": "Lacquer",
  "name": { "en": "Qing Carved Lacquer Box", "zh": "清剔红漆盒" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Qing%20dynasty%20carved%20red%20lacquer%20box%20intricate%20pattern&image_size=landscape_16_9",
  "hallId": "hall/painting-gallery",
  "dynastyId": "dynasty/qing",
  "personIds": [],
  "period": { "start": 1700, "end": 1800,
              "label": { "en": "18th century CE", "zh": "公元18世纪" } },
  "dimensions": { "diameter": { "value": 22.0, "unit": "cm" }, "height": { "value": 8.0, "unit": "cm" } },
  "material":   ["wood core", "lacquer"],
  "techniques": ["carved red lacquer (tihong)", "polishing"],
  "culturalContext": {
    "ritualUse":       { "en": "Imperial gift-giving and storage.", "zh": "宫廷馈赠与贮物。" },
    "socialFunction":  { "en": "High-status gift.", "zh": "高端礼品。" },
    "relatedConcepts": ["tihong", "Qing workshops", "gift economy"]
  },
  "narrativePoints": {
    "entry":  ["Hundred-layer lacquer, each polished by hand", "A box built over years, not hours", "Hidden patterns appear only after carving"],
    "deeper": ["How many months a single layer took to cure", "Imperial workshop organization", "Why red was the preferred color"],
    "expert": ["Lacquer tree biology and sap composition", "Cure time and temperature control", "Authentication via layer analysis"]
  },
  "relationships": {
    "sameDynasty": ["artifact/qianlong-jade-scroll"]
  },
  "quickQuestions": {
    "en": ["How many lacquer layers?", "Why red?", "Who made it?"],
    "zh": ["几层漆？", "为何是红色？", "谁制作？"]
  }
},
{
  "id": "artifact/neolithic-jade-cong",
  "type": "Jade",
  "name": { "en": "Neolithic Liangzhu Jade Cong", "zh": "良渚玉琮" },
  "imageUrl": "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Neolithic%20Liangzhu%20culture%20jade%20cong%20tube%20ritual%20object&image_size=landscape_16_9",
  "hallId": "hall/bronze-gallery",
  "dynastyId": "dynasty/shang",
  "personIds": [],
  "period": { "start": -3300, "end": -2200,
              "label": { "en": "Liangzhu culture, 3300–2200 BCE", "zh": "良渚文化，公元前3300—前2200年" } },
  "dimensions": { "height": { "value": 31.0, "unit": "cm" }, "width": { "value": 7.0, "unit": "cm" } },
  "material":   ["nephrite jade"],
  "techniques": ["abrasive carving"],
  "culturalContext": {
    "ritualUse":       { "en": "Interface between earth and heaven; burial goods.", "zh": "天地沟通，葬仪礼器。" },
    "socialFunction":  { "en": "Elite ritual monopoly.", "zh": "上层仪式垄断。" },
    "relatedConcepts": ["Liangzhu culture", "jade ritual", "pre-dynastic China"]
  },
  "narrativePoints": {
    "entry":  ["Five thousand years old — older than Chinese writing", "A tube carved without metal tools", "We still do not fully know what it meant"],
    "deeper": ["What Liangzhu burials tell us about social stratification", "How jade was carved using only string and sand", "The mystery of the taotie-like mask pattern"],
    "expert": ["Dating techniques for Neolithic jade", "Comparative Liangzhu cong typology", "Ongoing debates about symbolic meaning"]
  },
  "relationships": {},
  "quickQuestions": {
    "en": ["How is it carved without metal?", "What did it mean?", "How old is it really?"],
    "zh": ["没有金属工具如何雕刻？", "有何含义？", "到底多老？"]
  }
}
```

Note: the Liangzhu jade cong predates the Shang dynasty but our dynasty list starts at Shang. We intentionally attach it to `dynasty/shang` with period `-3300 to -2200` to avoid introducing a "Neolithic" entry; the narrative points acknowledge this.

- [ ] **Step 2: Integrity + other tests**

Run:
```bash
cd backend && source venv/bin/activate
python test_ontology_integrity.py
python test_ontology_resolver.py
python test_api_ontology.py
```
Expected: all PASS. Artifact count is now 15.

- [ ] **Step 3: Update prompt snapshots (data changes cascade through prompts)**

Run: `python test_prompt_snapshot.py`
Expected: either PASS (if prompts unchanged for da-ke-ding, which should be the case since we did not touch it) or intentional FAIL with diff. If diff, inspect — likely related entities changed. Approve with: `python test_prompt_snapshot.py --update`.

- [ ] **Step 4: Commit phase 5**

```bash
git add data/ontology/
git commit -m "feat(data): expand dataset to 15 artifacts across 4 halls, 11 dynasties, 7 persons"
```

---

## Phase 6 — Wrap-up

### Task 31: Final verification sweep

- [ ] **Step 1: Full test run**

```bash
cd backend && source venv/bin/activate
python test_ontology_integrity.py
python test_ontology_resolver.py
python test_api_ontology.py
python test_prompt_snapshot.py
python test_voice_suite.py          # existing voice tests still pass
```
Expected: all PASS.

- [ ] **Step 2: Frontend production build**

```bash
cd frontend && npm run build
```
Expected: `✓ built in ...`.

- [ ] **Step 3: End-to-end smoke test**

Start backend and frontend, open http://localhost:3000:
1. Pick any artifact; chips render.
2. Click a Dynasty chip; drawer shows period + related artifacts; click one — selected artifact switches.
3. Send chat message at depth `entry`; response reads like a hook-first storyteller.
4. Switch depth to `expert`; next reply is analytical and cites technique/material.
5. `GET http://localhost:8080/voice/metrics` still returns; ontology did not break voice.

- [ ] **Step 4: Commit any last-mile fixes**

```bash
git status
# if any tweaks were needed:
git commit -am "fix: polish after end-to-end verification"
```

---

## Self-review (done by plan author, not during execution)

**Spec coverage** — every section of `docs/plans/2026-04-23-ontology-redesign-design.md` maps to tasks:

| Design section | Implementing tasks |
|----------------|-------------------|
| §2 Three-layer architecture | Tasks 11–12, 19–21 |
| §4 Data model + field mapping | Tasks 6–9, 26–30 |
| §5 Schema validation | Tasks 1–5, 10, 11–13 |
| §6 API design | Tasks 14–18 |
| §7 Prompt construction | Tasks 19–22 |
| §8 Frontend interaction | Tasks 23–25 |
| §9 Data expansion (5→15) | Tasks 26–30 |
| §10 Testing strategy | Tasks 13, 18, 22, 31 |
| §11 File change list | Reflected in File Structure header and per-task files |
| §12 Phased rollout | Phases 1–6 in this plan |

**No placeholder scan** — no `TBD`, `TODO`, `implement later`, or `similar to task N`. Every task has concrete code, file paths, commands.

**Type consistency** — `expand_artifact(artifact, ontology)` signature is used identically in Tasks 15, 17, 18, 21. `persona_manager.build_system_prompt(language, depth_level, artifact_expanded)` signature consistent across Tasks 20, 21, 22. Pydantic model names (`Hall`, `Dynasty`, `Person`, `Artifact`) match across models.py, loader.py, resolver.py, and tests.
