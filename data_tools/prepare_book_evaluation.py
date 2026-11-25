"""Build the multilingual fable evaluation from indexed baseline run outputs."""

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO.parent
PROFILES = ("cohere", "gemma31b", "gpt", "qwen27b", "translategemma27b")
LANGUAGES = ("ar", "hi", "ka", "ru", "vi", "zh-CN")
REFERENCE = "human_reference"


def build(runs, source):
    source_bytes = source.read_bytes()
    stories = json.loads(source_bytes)
    digest = hashlib.sha256(source_bytes).hexdigest()
    records = []
    for language in LANGUAGES:
        outputs = {}
        for profile in PROFILES:
            path = runs / profile / f"{language}.json"
            run = json.loads(path.read_bytes())
            meta = run["run"]
            if (meta["dataset_sha256"] != digest or meta["profile"] != profile
                    or not meta["target_language"].endswith(f"({language})")):
                raise ValueError(f"Source dataset, profile or language does not match: {path}")
            translations = {}
            for row in run["translations"]:
                index = row["source_index"]
                if (type(index) is not int or not 0 <= index < len(stories)
                        or index in translations or row["title_en"] != stories[index]["title_en"]):
                    raise ValueError(f"Invalid or duplicate story index {index}: {path}")
                translations[index] = row["translation"]
            outputs[profile] = (meta["model"], translations)
        if language == "zh-CN":
            references = {}
            for index, story in enumerate(stories):
                title, text = story.get("title_cn"), story.get("text_cn")
                if not all(isinstance(value, str) and value.strip() for value in (title, text)):
                    raise ValueError(f"Missing Chinese reference for story {index}")
                references[index] = f"{title.strip()}\n\n{text.strip()}"
            outputs[REFERENCE] = (None, references)
        for index, story in enumerate(stories):
            # Keep model order consistent, with the Chinese reference inserted by the same hash.
            order = sorted(outputs, key=lambda profile: hashlib.sha256(
                f"book:{index}:{profile}".encode()).digest())
            candidates = []
            for profile in order:
                model, translations = outputs[profile]
                text = translations.get(index)
                available = isinstance(text, str) and bool(text.strip())
                candidates.append({
                    "id": profile, "model": model, "available": available,
                    **({"metadata": {"translation_type": REFERENCE, "reference_fields": ["title_cn", "text_cn"]}}
                       if profile == REFERENCE else {}),
                    "translation_regions": [{
                        "id": f"fable-{index}", "target": text,
                        "quality_score": None, "presentation_score": None, "edits": [],
                    }] if available else [],
                })
            records.append({
                "task_type": "book_evaluation", "schema_version": 1,
                "id": f"book-{language}-{index}", "language": language, "source_index": index,
                "source_language": "en", "title": story["title_en"].strip(),
                "source": story["text_en"].strip(), "post_edit": "", "post_edit_origin": None,
                "candidates": candidates,
            })
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=PROJECT / "agent/book_tryout/baseline_infer/runs/unwrapped")
    parser.add_argument("--source", type=Path, default=PROJECT / "data/final/processed/aesop_en_zh_clean_with_difficulty.json")
    parser.add_argument("--output", type=Path, default=REPO / "public/data/demo/book_multilingual.json")
    args = parser.parse_args()
    records = build(args.runs, args.source)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for language in LANGUAGES:
        rows = [row for row in records if row["language"] == language]
        counts = [sum(candidate["available"] for candidate in row["candidates"]) for row in rows]
        print(f"{language}: {len(rows)} fables, {sum(counts)} available translations, "
              f"{sum(count >= 2 for count in counts)} fables with comparable outputs")


if __name__ == "__main__":
    main()
