"""Package matched OpenMantra pages for the manga translation rating task.

Run from the repository root: python data_tools/prepare_manga_evaluation.py
Only the output JSON, conversion report, and copied public assets are written.
"""

import argparse
import json
import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
PUBLIC_ROOT = REPO_ROOT / "public"
DEFAULT_DATASET_ROOT = WORKSPACE_ROOT / "data/manga/open-mantra-dataset"
DEFAULT_RENDERED_ROOT = (
    WORKSPACE_ROOT / "agent/manga_tryout/manga_agent/runs/fst_try/rendered_results"
)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _component(value, label):
    if not isinstance(value, str) or not SAFE_COMPONENT.fullmatch(value):
        raise ValueError(f"{label} must be a nonempty filename-safe identifier")
    return value


def _read_sources(dataset_root):
    annotation_path = dataset_root / "annotation.json"
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    if not isinstance(annotation, list):
        raise ValueError("annotation.json must contain a list of books")

    sources = {}
    book_order = []
    for book in annotation:
        if not isinstance(book, dict):
            raise ValueError("Each annotation book must be an object")
        title = _component(book.get("book_title"), "book_title")
        if title not in book_order:
            book_order.append(title)
        pages = book.get("pages")
        if not isinstance(pages, list):
            raise ValueError(f"{title}: pages must be a list")
        for page in pages:
            if not isinstance(page, dict):
                raise ValueError(f"{title}: each page must be an object")
            page_index = page.get("page_index")
            if type(page_index) is not int or page_index < 1:
                raise ValueError(f"{title}: page_index must be a positive integer")
            image_paths = page.get("image_paths")
            image_path = image_paths.get("ja") if isinstance(image_paths, dict) else None
            if not isinstance(image_path, str):
                raise ValueError(f"{title}, page {page_index}: image_paths.ja is required")
            relative = Path(image_path)
            if (
                relative.is_absolute()
                or len(relative.parts) != 4
                or relative.parts[:3] != ("images", title, "ja")
            ):
                raise ValueError(f"Invalid Japanese image path: {image_path}")
            stem = _component(relative.stem, "image filename stem")
            key = (title, stem)
            if key in sources:
                raise ValueError(f"Duplicate source identity: {title}/{stem}")
            original = (dataset_root / relative).resolve()
            if not original.is_relative_to(dataset_root) or not original.is_file():
                raise ValueError(f"Missing or invalid original image: {image_path}")
            regions = page.get("text")
            if not isinstance(regions, list):
                raise ValueError(f"{title}/{stem}: text must be a list")
            references = []
            for region in regions:
                if not isinstance(region, dict) or not isinstance(region.get("text_en"), str):
                    raise ValueError(f"{title}/{stem}: every text region needs a string text_en")
                references.append(region["text_en"])
            sources[key] = {
                "path": original,
                "page_index": page_index,
                "references": references,
            }
    return sources, book_order


def _read_renders(rendered_root, sources):
    if not rendered_root.is_dir():
        raise ValueError(f"Rendered-results directory does not exist: {rendered_root}")
    renders = {}
    for path in sorted(rendered_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        relative = path.relative_to(rendered_root)
        if len(relative.parts) != 2:
            raise ValueError(f"Expected rendered image <book>/<stem>.<extension>: {relative}")
        title = _component(relative.parts[0], "rendered book title")
        stem = _component(path.stem, "rendered filename stem")
        key = (title, stem)
        if key in renders:
            raise ValueError(f"Duplicate rendered identity: {title}/{stem}")
        if key not in sources:
            raise ValueError(f"Unknown rendered image: {title}/{path.name}")
        if not path.resolve().is_relative_to(rendered_root):
            raise ValueError(f"Rendered image points outside its source directory: {relative}")
        renders[key] = path
    if not renders:
        raise ValueError("No matched rendered images were found")
    return renders


def prepare(dataset_root, rendered_root, run_id, output_json, assets_dir, *, public_root=PUBLIC_ROOT):
    """Validate all inputs, then copy unchanged images and write tasks/report.

    Assets must be beneath public_root so every image URL works with Vite's
    deployment base path. The optional public_root is useful for fixture tests.
    """
    dataset_root = Path(dataset_root).resolve()
    rendered_root = Path(rendered_root).resolve()
    output_json = Path(output_json).resolve()
    assets_dir = Path(assets_dir).resolve()
    public_root = Path(public_root).resolve()
    _component(run_id, "run_id")
    if not assets_dir.is_relative_to(public_root) or assets_dir == public_root:
        raise ValueError("assets-dir must be a subdirectory of the repository public directory")
    for destination in (assets_dir, output_json):
        if any(destination.is_relative_to(source) for source in (dataset_root, rendered_root)):
            raise ValueError("Outputs must not be written inside either source directory")

    sources, book_order = _read_sources(dataset_root)
    renders = _read_renders(rendered_root, sources)
    license_path = dataset_root / "LICENSE.md"
    if not license_path.is_file():
        raise ValueError(f"Dataset attribution license is missing: {license_path}")
    base_url = assets_dir.relative_to(public_root).as_posix()
    order = {title: index for index, title in enumerate(book_order)}
    ordered = sorted(sources, key=lambda key: (order[key[0]], sources[key]["page_index"], key[1]))
    tasks, copies, missing = [], [], []
    books = {title: {"source_pages": 0, "matched_pages": 0} for title in book_order}
    for title, stem in ordered:
        key = (title, stem)
        source = sources[key]
        books[title]["source_pages"] += 1
        metadata = {
            "book_title": title,
            "page_index": source["page_index"],
            "run_id": run_id,
            "filename_stem": stem,
        }
        if key not in renders:
            missing.append(metadata)
            continue
        books[title]["matched_pages"] += 1
        original_asset = Path("original") / title / source["path"].name
        translated_asset = Path("translated") / title / renders[key].name
        tasks.append({
            "id": f"openmantra:{run_id}:{title}:{stem}",
            "original_image": f"{base_url}/{original_asset.as_posix()}",
            "translated_image": f"{base_url}/{translated_asset.as_posix()}",
            "reference_texts": source["references"],
            "metadata": metadata,
            "edits": [],
            "fidelity_score": None,
            "presentation_score": None,
        })
        copies.extend(((source["path"], original_asset), (renders[key], translated_asset)))

    report = {
        "run_id": run_id,
        "source_pages": len(sources),
        "matched_pages": len(tasks),
        "reference_text_count": sum(len(task["reference_texts"]) for task in tasks),
        "pages_without_reference_text": sum(not task["reference_texts"] for task in tasks),
        "missing_render_count": len(missing),
        "missing_rendered_pages": missing,
        "books": books,
        "assets_base_url": base_url,
        "attribution": {
            "dataset": "OpenMantra",
            "source": "https://github.com/mantra-inc/open-mantra-dataset",
            "license": "CC BY-NC 4.0",
            "license_file": f"{base_url}/LICENSE.md",
            "citation": (
                "Ryota Hinami, Shonosuke Ishiwatari, Kazuhiko Yasuda, and Yusuke Matsui. "
                "Towards Fully Automated Manga Translation. AAAI 2021."
            ),
        },
    }

    # Input validation completes before any output directories or files are made.
    for source, relative in copies:
        destination = assets_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    shutil.copyfile(license_path, assets_dir / "LICENSE.md")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = output_json.with_name(f"{output_json.stem}.report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return tasks, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--rendered-results-root", type=Path, default=DEFAULT_RENDERED_ROOT)
    parser.add_argument("--run-id", default="fst_try")
    parser.add_argument("--output-json", type=Path, default=PUBLIC_ROOT / "data/demo/manga_translation.json")
    parser.add_argument("--assets-dir", type=Path, default=PUBLIC_ROOT / "data/manga/fst_try")
    args = parser.parse_args()
    try:
        tasks, report = prepare(
            args.dataset_root, args.rendered_results_root, args.run_id,
            args.output_json, args.assets_dir,
        )
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"Wrote {len(tasks)} tasks to {args.output_json}")
    print(f"Copied unchanged images and dataset license to {args.assets_dir}")
    print(f"Missing rendered pages: {report['missing_render_count']} (listed in conversion report)")


if __name__ == "__main__":
    main()
