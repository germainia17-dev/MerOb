"""
memory_auto_review.py
─────────────────────
Automatically processes the extracted memories.

For each validated memory:
  - NEW       → an individual .md note is created in Memories/
  - DUPLICATE → silently skipped
  - UPDATE    → the existing note is updated

Each note contains:
  - The memory text
  - Its capture date
  - A [[Category]] wikilink to its category hub
  - [[Related memory]] wikilinks to the 2 most similar memories
  → The Obsidian graph forms an organic network

Category (hub) notes are updated automatically with the list of
memories they contain.

Zero API calls. Zero human interaction.
"""

from pathlib import Path
from datetime import datetime
from embeddings import Embedder
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
import numpy as np
import json
import re
import os
import sys

# ======================
# CONFIG
# ======================

DOUBLON_THRESHOLD = 0.92   # ≥ → certain duplicate (stricter, since notes are individual)
UPDATE_THRESHOLD  = 0.70   # between the two → update
RELATED_N         = 2      # number of links to nearby memories

# Classification confidence threshold — FALLBACK only.
# Primary categorization comes from the extraction step: Gemini tags each
# memory with a category. This local embedding classifier is the fallback
# for memories that arrive WITHOUT a tag (e.g. via MCP or manual entry):
#   score ≥ threshold → the memory joins the closest fixed category
#   score < threshold → the memory goes to "Unsorted" = discovery pool
# Tuned for English all-MiniLM-L6-v2 cosine scores (in-category ≈ 0.20-0.30).
CONFIDENT_THRESHOLD = 0.18

# --- Phase B: automatic category discovery (hybrid mode) ---
NEW_CAT_MIN_SIZE   = 3     # min number of similar "Unsorted" memories to create a category
NEW_CAT_DISTANCE   = 0.56  # max intra-cluster cosine distance (complete linkage)
# Outlier filter: minimum average similarity to the other cluster members.
# Deliberately low (0.40) — it removes obvious outliers without sacrificing
# genuine members. A truly borderline memory may occasionally join a neighboring
# category: that is fixable in one click and self-corrects with more data.
NEW_CAT_MEMBER_SIM = 0.40

TRIAGE_CAT = "Unsorted"

# The memory folder is resolved dynamically (env / config.json /
# Obsidian auto-detection) — never hardcoded. See config.py.
import config

VAULT = config.resolve_vault()
MEMORIES_DIR   = (VAULT / "Memories")   if VAULT else None  # one note per memory
CATEGORIES_DIR = (VAULT / "Categories") if VAULT else None  # hub note per category

inbox_path = Path(".data/inbox/memories_to_review.md")
log_path   = Path(".data/inbox/last_run.md")

# ======================
# SEMANTIC CATEGORIES
# ======================

CATEGORIES = {
    "Identity": (
        "who the person is: name, age, location, background, occupation, "
        "studies, role, personality, hobbies, passions, interests, "
        "lifestyle, personal tastes and life preferences"
    ),
    "Projects": (
        "a concrete project being built or developed: app, product, website, "
        "prototype, demo, deliverable, side project, startup, "
        "project goal, milestone, deadline, launch"
    ),
    "Ideas": (
        "a decision made, design choice, idea to explore, open question, "
        "strategy, plan, consideration, reasoning, stance, analysis, reflection"
    ),
    "Learnings": (
        "a technical concept learned, lesson understood, reusable principle, "
        "insight, fact worth remembering, how something works, "
        "knowledge gained from experience"
    ),
    "Tools": (
        "a tool or technology the person uses: software, programming language, "
        "framework, library, app, service, platform, hardware, workflow, command"
    ),
    "Habits": (
        "a personal trait, strength, weakness, recurring difficulty, "
        "work habit, routine, or preference in how the person likes to work"
    ),
    "Sources": (
        "an external source: link, URL, article, book, paper, documentation, "
        "video, or reference to read or check later"
    ),
}

# Valid category names the extraction step may tag a memory with.
VALID_CATS = set(CATEGORIES.keys())

# Categories discovered by the tool (hybrid mode), persisted across runs.
# Format: { "CategoryName": "description = concatenated founding memories" }
DISCOVERED_PATH = Path(".data/discovered_categories.json")


def load_discovered() -> dict:
    if DISCOVERED_PATH.exists():
        try:
            return json.loads(DISCOVERED_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_discovered(d: dict) -> None:
    DISCOVERED_PATH.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERED_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


DISCOVERED = load_discovered()

# ======================
# MODEL LOADING
# ======================

model = Embedder()


def build_category_index():
    """Classification index = fixed categories + discovered categories."""
    keys  = list(CATEGORIES.keys()) + list(DISCOVERED.keys())
    descs = list(CATEGORIES.values()) + list(DISCOVERED.values())
    embs  = model.encode(descs)
    return keys, embs


_category_keys, _category_embs = build_category_index()


# ======================
# UTILITIES
# ======================

def slugify(text: str, max_len: int = 50) -> str:
    """Turns a piece of text into a clean filename."""
    # Remove bold/italic markdown
    text = re.sub(r"\*+", "", text)
    # Remove special characters, keep letters/digits/spaces
    text = re.sub(r"[^\w\s\-àâäéèêëïîôùûüçœæ]", " ", text, flags=re.UNICODE)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Truncate cleanly
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
    return text.strip()


def is_junk(memory: str) -> bool:
    """Detects useless fragments: empty headings, '...', lines that are too short."""
    m = memory.strip()
    if not m or m in ("...", "…"):
        return True
    stripped = re.sub(r"\*+", "", m).strip()
    if stripped.endswith(":"):
        return True
    if len(stripped) < 8:
        return True
    return False


# Matches an optional leading category tag: "[Tools] ...", "(tools) - ...", "**[Tools]**: ..."
_CAT_PREFIX = re.compile(r"^\**\s*[\[\(]\s*([A-Za-z]+)\s*[\]\)]\**\s*[:\-]?\s*(.+)$", re.DOTALL)


def parse_category_tag(text: str):
    """Splits an optional leading [Category] tag from a memory line.

    Returns (clean_text, category_or_None). The category is only returned
    when it matches a known category (or maps to Unsorted); otherwise the
    original text is kept untouched so we never eat a real bracket.
    """
    m = _CAT_PREFIX.match(text)
    if not m:
        return text, None
    cand = m.group(1).strip().capitalize()
    body = m.group(2).strip()
    if cand in VALID_CATS:
        return body, cand
    if cand.lower() in ("unsorted", "other", "misc", "none", "uncategorized"):
        return body, TRIAGE_CAT
    return text, None  # not a real category tag → keep original text


def detect_category(memory: str) -> str:
    """Classifies the memory into the closest category.
    Returns TRIAGE_CAT if the score is too low."""
    emb    = model.encode([memory])
    scores = cosine_similarity(emb, _category_embs)[0]
    idx    = int(np.argmax(scores))
    if float(scores[idx]) < CONFIDENT_THRESHOLD:
        return TRIAGE_CAT
    return _category_keys[idx]


# ======================
# PHASE B — CATEGORY DISCOVERY (hybrid)
# ======================

# Common stopwords to ignore when naming a category (English-first, a few FR kept).
_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "has", "had",
    "was", "were", "will", "would", "your", "you", "our", "its", "are", "can",
    "could", "should", "their", "them", "they", "she", "his", "her", "him",
    "about", "into", "over", "than", "then", "when", "what", "which", "who",
    "whom", "user", "wants", "want", "needs", "need", "must", "uses", "use",
    "using", "like", "also", "very", "more", "most", "some", "such",
    "between", "without", "during", "after", "before", "while", "because",
    "dans", "pour", "avec", "cette", "veut", "doit", "peut", "une", "des", "les",
}


def name_cluster(texts: list) -> str:
    """Names a category from the most frequent strong word (0 API).
    A later phase could replace this naming with a Gemini call."""
    counts = {}
    for t in texts:
        for w in re.findall(r"[a-zàâäéèêëïîôùûüçœ]{4,}", t.lower()):
            if w in _STOPWORDS:
                continue
            counts[w] = counts.get(w, 0) + 1
    if not counts:
        return "Misc"
    top = max(counts, key=counts.get)
    return top.capitalize()


def discover_categories(triage_notes: list) -> dict:
    """Looks for dense clusters in the 'Unsorted' pool.
    Returns {category_name: [notes]} for each cluster that is big enough."""
    if len(triage_notes) < NEW_CAT_MIN_SIZE:
        return {}

    texts = [n["memory"] for n in triage_notes]
    embs  = model.encode(texts)

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=NEW_CAT_DISTANCE,
        metric="cosine",
        linkage="complete",
    )
    labels = clustering.fit_predict(embs)

    # Group (note, embedding) by cluster
    clusters = {}
    for note, emb, label in zip(triage_notes, embs, labels):
        clusters.setdefault(int(label), []).append((note, emb))

    discovered = {}
    for items in clusters.values():
        if len(items) < NEW_CAT_MIN_SIZE:
            continue

        # Filter outliers: average similarity of each member to the OTHERS
        # (leave-one-out) — robust, since an outlier cannot inflate its own score
        member_embs = np.array([e for _, e in items])
        sim_matrix  = cosine_similarity(member_embs)
        np.fill_diagonal(sim_matrix, np.nan)
        mean_to_others = np.nanmean(sim_matrix, axis=1)
        kept = [note for (note, _), s in zip(items, mean_to_others) if s >= NEW_CAT_MEMBER_SIM]

        if len(kept) < NEW_CAT_MIN_SIZE:
            continue

        name = name_cluster([m["memory"] for m in kept])
        # avoid a collision with an existing category
        if name in CATEGORIES or name in DISCOVERED or name in discovered:
            name = f"{name} (auto)"
        discovered[name] = kept
    return discovered


# ======================
# NOTE READING / WRITING
# ======================

def get_all_memory_notes() -> list:
    """Reads all existing memory notes.
    Returns a list of {slug, memory, category, date, path}."""
    notes = []
    if not MEMORIES_DIR.exists():
        return notes
    for f in MEMORIES_DIR.rglob("*.md"):
        text = f.read_text(encoding="utf-8")
        lines = text.splitlines()
        # The memory is on the first non-empty, non-frontmatter line
        memory_text = ""
        in_front = False
        for line in lines:
            if line.strip() == "---":
                in_front = not in_front
                continue
            if in_front:
                continue
            if line.strip() and not line.startswith("#") and not line.startswith("[["):
                memory_text = line.strip()
                break
        if memory_text:
            # Extract the category from the wikilinks
            cat_match = re.search(r"\[\[([^\]]+)\]\]", text)
            cat = cat_match.group(1) if cat_match else TRIAGE_CAT
            notes.append({
                "slug": f.stem,
                "memory": memory_text,
                "category": cat,
                "path": f,
            })
    return notes


def memory_to_filename(memory: str) -> str:
    """Generates a unique filename from a memory's text."""
    slug = slugify(memory, max_len=55)
    return slug + ".md"


def find_related(memory: str, all_notes: list, n: int = RELATED_N) -> list:
    """Finds the N closest memories (excluding duplicates)."""
    if not all_notes:
        return []
    texts = [note["memory"] for note in all_notes]
    mem_emb   = model.encode([memory])
    all_embs  = model.encode(texts)
    scores    = cosine_similarity(mem_emb, all_embs)[0]
    # Exclude the memory itself (score = 1.0)
    sorted_idx = np.argsort(scores)[::-1]
    related = []
    for idx in sorted_idx:
        if scores[idx] > 0.98:   # this is the same memory
            continue
        if scores[idx] < 0.30:  # too weakly related
            break
        related.append(all_notes[idx]["slug"])
        if len(related) >= n:
            break
    return related


def write_memory_note(memory: str, category: str, date: str, related_slugs: list) -> Path:
    """Creates or updates a memory note, filed under Memories/<Category>/.

    One subfolder per category means the Obsidian graph can be colored by
    folder (path: query → one color per category), and the file explorer
    stays organized.
    """
    filename = memory_to_filename(memory)
    # If this memory already lives under another category, drop the stale copy
    # (e.g. when Phase B discovery moves it out of 'Unsorted').
    for stale in MEMORIES_DIR.rglob(filename):
        stale.unlink()
    dest_dir = MEMORIES_DIR / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / filename

    related_links = "  ".join(f"[[{s}]]" for s in related_slugs)

    lines = [
        f"> {memory}",
        "",
        f"**Category:** [[{category}]]",
    ]
    if related_links:
        lines.append(f"**Links:** {related_links}")
    lines += [
        "",
        f"*Captured on {date}*",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def update_category_hub(category: str, all_notes: list) -> None:
    """Updates a category's hub note with all its members."""
    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)
    path = CATEGORIES_DIR / f"{category}.md"

    members = [n for n in all_notes if n["category"] == category]

    lines = [f"# {category}", "", f"*{len(members)} memory(ies)*", ""]
    for m in members:
        lines.append(f"- [[{m['slug']}]]")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def reconcile(new_memory: str, existing_notes: list) -> dict:
    """Checks whether the memory is a duplicate or an update."""
    if not existing_notes:
        return {"classification": "NEW", "match": None, "score": 0.0}

    texts = [n["memory"] for n in existing_notes]
    new_emb  = model.encode([new_memory])
    all_embs = model.encode(texts)
    scores   = cosine_similarity(new_emb, all_embs)[0]
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score >= DOUBLON_THRESHOLD:
        return {"classification": "DUPLICATE", "match": existing_notes[best_idx], "score": best_score}
    elif best_score >= UPDATE_THRESHOLD:
        return {"classification": "UPDATE",    "match": existing_notes[best_idx], "score": best_score}
    else:
        return {"classification": "NEW",       "match": None,                     "score": best_score}


# ======================
# MAIN PIPELINE
# ======================

def main():
    if not inbox_path.exists():
        print("No inbox found.")
        return

    if VAULT is None or not VAULT.exists():
        print(config.NO_VAULT_MSG)
        sys.exit(1)

    content = inbox_path.read_text(encoding="utf-8")
    raw_memories = []
    skipped_junk = 0

    for line in content.splitlines():
        if line.startswith("- [ ] "):
            body = line.replace("- [ ] ", "").strip()
            if not body:
                continue
            memory, cat_hint = parse_category_tag(body)
            if is_junk(memory):
                skipped_junk += 1
                continue
            raw_memories.append((memory, cat_hint))

    if not raw_memories:
        print("No memories to process.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n→ {len(raw_memories)} memory(ies) to process (+ {skipped_junk} fragment(s) skipped)")
    print(f"→ Vault: {VAULT.name}")

    # Load existing notes
    existing_notes = get_all_memory_notes()
    print(f"→ {len(existing_notes)} notes already in Memories/\n")

    added_list     = []
    updated_list   = []
    duplicate_list = []

    for memory, cat_hint in raw_memories:
        result         = reconcile(memory, existing_notes)
        classification = result["classification"]
        match          = result["match"]

        if classification == "DUPLICATE":
            duplicate_list.append(memory)
            print(f"  [DUPLICATE]  {memory[:65]}")
            continue

        # Use the category tagged by the extraction step; fall back to the
        # local embedding classifier when there is no (valid) tag.
        category = cat_hint or detect_category(memory)

        if classification == "UPDATE" and match:
            # Remove the old note and rewrite
            if match["path"].exists():
                match["path"].unlink()
            # Update in existing_notes so links stay correct
            for n in existing_notes:
                if n["memory"] == match["memory"]:
                    n["memory"]   = memory
                    n["category"] = category
                    n["slug"]     = slugify(memory, 55)
            updated_list.append({"new": memory, "old": match["memory"], "category": category})
            print(f"  [UPDATE → {category}]  {memory[:55]}")

        if classification == "NEW" or classification == "UPDATE":
            # Links to nearby memories (against the notes existing at this point)
            others  = [n for n in existing_notes if n["memory"] != memory]
            related = find_related(memory, others)

            note_path = write_memory_note(memory, category, today, related)

            if classification == "NEW":
                slug = note_path.stem
                existing_notes.append({"slug": slug, "memory": memory,
                                        "category": category, "path": note_path})
                added_list.append({"memory": memory, "category": category, "slug": slug})
                print(f"  [NEW → {category}]  {memory[:55]}")

    # --- Phase B: let new categories emerge ---
    created_cats = []
    triage_notes = [n for n in existing_notes if n["category"] == TRIAGE_CAT]
    new_cats = discover_categories(triage_notes)

    if new_cats:
        for name, members in new_cats.items():
            # The description feeds future classifications
            DISCOVERED[name] = " / ".join(m["memory"] for m in members)[:500]
            for m in members:
                m["category"] = name
                others  = [x for x in existing_notes if x["memory"] != m["memory"]]
                related = find_related(m["memory"], others)
                write_memory_note(m["memory"], name, today, related)
            created_cats.append((name, len(members)))
            print(f"  [NEW CATEGORY → {name}]  {len(members)} memories grouped")
        save_discovered(DISCOVERED)

    # Update all category hubs
    all_cats = set(n["category"] for n in existing_notes)
    for cat in all_cats:
        update_category_hub(cat, existing_notes)

    # Clean up hubs that became empty (e.g. 'Unsorted' emptied by discovery)
    if CATEGORIES_DIR.exists():
        for hub in CATEGORIES_DIR.glob("*.md"):
            if hub.stem not in all_cats:
                hub.unlink()

    write_log(raw_memories, added_list, updated_list, duplicate_list, created_cats)
    print_summary(raw_memories, added_list, updated_list, duplicate_list, created_cats)


def write_log(raw, added, updated, duplicates, created_cats=None):
    created_cats = created_cats or []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Last run — {now}",
        "",
        f"**Processed**: {len(raw)}  |  "
        f"**Added**: {len(added)}  |  "
        f"**Updated**: {len(updated)}  |  "
        f"**Duplicates skipped**: {len(duplicates)}",
        "",
    ]
    if created_cats:
        lines += ["## 🆕 New categories discovered", ""]
        for name, count in created_cats:
            lines.append(f"- **[[{name}]]** — {count} memories grouped")
        lines.append("")
    if added:
        lines += ["## ✅ New notes", ""]
        for item in added:
            lines.append(f"- **{item['category']}** — [[{item['slug']}]]")
        lines.append("")
    if updated:
        lines += ["## 🔄 Updates", ""]
        for item in updated:
            lines.append(f"- **{item['category']}** — {item['new'][:60]}")
            lines.append(f"  *(replaces: {item['old'][:60]})*")
        lines.append("")
    if duplicates:
        lines += ["## ⏭ Duplicates skipped", ""]
        for m in duplicates:
            lines.append(f"- {m}")
        lines.append("")
    log_path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(raw, added, updated, duplicates, created_cats=None):
    created_cats = created_cats or []
    print(f"\n===== SUMMARY =====")
    print(f"Processed      : {len(raw)}")
    print(f"New notes      : {len(added)}")
    print(f"Updated        : {len(updated)}")
    print(f"Duplicates     : {len(duplicates)}")
    if created_cats:
        print(f"Categories discovered: {len(created_cats)} "
              f"({', '.join(n for n, _ in created_cats)})")
    print(f"API calls      : 0")
    print(f"\nNotes written to: Memories/")
    print(f"Hubs updated in : Categories/")
    print(f"Log: .data/inbox/last_run.md")


if __name__ == "__main__":
    main()
