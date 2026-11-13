"""Package the multilingual 50-page sample; preserve image bytes and text provenance."""
import argparse
import collections
import hashlib
import filecmp
import json
import shutil
from pathlib import Path

try:
    from data_tools.manga_source_alignment import apply_alignment
except ModuleNotFoundError:
    from manga_source_alignment import apply_alignment

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / 'agent/manga_tryout/manga_agent/baselines/multilingual_50'
DEFAULT_REFERENCES = ROOT.parent / 'data/manga/open-mantra-dataset/annotation.json'
LANGUAGES = [('ar', 'Arabic', 'العربية'), ('en', 'English', 'English'), ('hi', 'Hindi', 'हिन्दी'),
             ('ka', 'Georgian', 'ქართული'), ('ru', 'Russian', 'Русский'),
             ('vi', 'Vietnamese', 'Tiếng Việt'), ('zh', 'Simplified Chinese', '简体中文')]


def checked_image(root, relative, expected_hash=None):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f'Missing or unsafe image: {relative}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_hash and digest != expected_hash:
        raise ValueError(f'Image hash mismatch: {relative}')
    return path, digest


def prepare(source=DEFAULT_SOURCE, references=DEFAULT_REFERENCES, alignments=None):
    source = Path(source).resolve()
    alignment_path = Path(alignments) if alignments else ROOT / 'public/data/demo/manga_multilingual.alignments.json'
    source_matches = json.loads(alignment_path.read_text()).get('pages', {}) if alignment_path.is_file() else {}
    manifest = json.loads((source / 'manifest.json').read_text())
    originals = {}
    for page in manifest['pages']:
        key = page['id']
        if key in originals:
            raise ValueError(f'Duplicate original page: {key}')
        relative = Path(key)
        if len(relative.parts) != 3 or relative.parts[1] != 'ja' or not relative.stem.isdigit():
            raise ValueError(f'Invalid source page identity: {key}')
        path, digest = checked_image(source, page['original'], page['sha256'])
        originals[key] = (path, digest)
    if not originals:
        raise ValueError('No original pages')
    refs = {}
    for book in json.loads(Path(references).read_text()):
        for page in book['pages']:
            path = Path(page['image_paths']['ja'])
            refs['/'.join(path.parts[-3:])] = page['text']
    missing = set(originals) - set(refs)
    if missing:
        raise ValueError(f'Missing human references for {sorted(missing)}')
    # Validate the complete input before copying assets.
    translations, unavailable = {}, []
    for code, label, native in LANGUAGES:
        text = json.loads((source / code / 'translated_text.json').read_text())
        pages = {}
        for page in text['pages']:
            key = page['image']
            if key in pages:
                raise ValueError(f'Duplicate {code} page: {key}')
            if key not in originals:
                raise ValueError(f'Unknown {code} page: {key}')
            relative = Path(key)
            if page.get('manga', relative.parts[0]) != relative.parts[0] or page.get('page_index', int(relative.stem)) != int(relative.stem):
                raise ValueError(f'Conflicting {code} page identity: {key}')
            path, digest = checked_image(source / code, key, page.get('image_sha256'))
            complete = page.get('status') == 'complete' and isinstance(page.get('regions'), list)
            if complete and any(not isinstance(r.get('text'), str) for r in page['regions']):
                raise ValueError(f'Invalid {code} text: {key}')
            if not complete:
                unavailable.append({'language': code, 'page': key, 'error': page.get('error', 'Text unavailable')})
            pages[key] = (page, path, digest, complete, text.get('model'))
        if set(pages) != set(originals):
            raise ValueError(f'{code} page coverage does not match originals')
        translations[code] = pages
    asset_root = ROOT / 'evaluation_assets/multilingual_50'
    tasks = []
    total_bytes = 0
    for key, (original_path, original_hash) in originals.items():
        dest = asset_root / 'originals' / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.is_file() or not filecmp.cmp(original_path, dest, shallow=False):
            shutil.copyfile(original_path, dest)
        total_bytes += dest.stat().st_size
    for code, label, native in LANGUAGES:
        for key, (original_path, original_hash) in originals.items():
            page, path, digest, complete, model = translations[code][key]
            dest = asset_root / code / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file() or not filecmp.cmp(path, dest, shallow=False):
                shutil.copyfile(path, dest)
            total_bytes += dest.stat().st_size
            regions = [dict(id=f'{code}:{i+1}', target=r['text'], kind=r.get('kind', 'other'),
                            uncertain=r.get('uncertain', False), quality_score=None, edits=[])
                       for i, r in enumerate(page['regions'])] if complete else None
            task = dict(id=f'multilingual50:{code}:{key}', page_key=key, language=code, language_label=label,
                        original_image=(asset_root / 'originals' / key).relative_to(ROOT).as_posix(),
                        translated_image=dest.relative_to(ROOT).as_posix(),
                        reference_texts=[r['text_en'] for r in refs[key]],
                        reference_texts_ja=[r['text_ja'] for r in refs[key]], translation_regions=regions,
                        fidelity_score=None, presentation_score=None, edits=[],
                        metadata=dict(book_title=Path(key).parts[0], page_index=int(Path(key).stem)+1,
                                      filename_stem=Path(key).stem, language=code, system_id='baseline',
                                      original_sha256=original_hash, translated_sha256=digest,
                                      text_origin='image_transcription', transcription_model=model,
                                      transcription_status='complete' if complete else 'unavailable',
                                      transcription_notes=page.get('notes', ''),
                                      transcription_error=page.get('error') if not complete else None))
            if task['id'] in source_matches:
                apply_alignment(task, source_matches[task['id']])
            tasks.append(task)
    license_path = ROOT / 'public/data/manga/fst_try/LICENSE.md'
    if license_path.is_file():
        shutil.copyfile(license_path, asset_root / 'LICENSE.md')
    output = ROOT / 'public/data/demo/manga_multilingual.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = dict(original_pages=len(originals), tasks=len(tasks), languages=[l[0] for l in LANGUAGES],
                  pages_per_language=dict(collections.Counter(h['language'] for h in tasks)),
                  unavailable_text=unavailable, asset_bytes=total_bytes,
                  source_alignment_counts=dict(collections.Counter(r.get('source_alignment', 'pending')
                      for task in tasks for r in task.get('translation_regions') or [])),
                  asset_directory=asset_root.relative_to(ROOT).as_posix())
    output.with_suffix('.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return tasks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--alignments', type=Path, help='Japanese region mapping JSON (auto-detected beside task JSON)')
    parser.add_argument('--references', type=Path, default=DEFAULT_REFERENCES)
    args = parser.parse_args()
    prepare(args.source_root, args.references, args.alignments)
