"""Package six-candidate multilingual evaluation with exact source pairs and pixel-identical WebP images."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / 'agent/manga_tryout/manga_agent/runs/multilingual_results'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def checked_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f'Missing or unsafe source path: {relative}')
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def lossless_asset(source, destination, expected_hash, previous=None):
    if sha(source) != expected_hash:
        raise ValueError(f'Rendered source image hash mismatch: {source.name}')
    if previous and previous.get('source_sha256') == expected_hash and destination.is_file() and sha(destination) == previous.get('sha256'):
        return previous
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as original:
        pixels = original.convert('RGBA')
        pixel_hash = hashlib.sha256(pixels.tobytes()).hexdigest()
        # Lossless WebP preserves every decoded pixel, including hidden alpha values.
        temporary = destination.with_suffix('.tmp')
        original.save(temporary, format='WEBP', lossless=True, quality=100, method=4, exact=True)
        with Image.open(temporary) as packed:
            if packed.size != original.size or packed.convert('RGBA').tobytes() != pixels.tobytes():
                raise ValueError(f'Lossless image verification failed: {source.name}')
        temporary.replace(destination)
    return dict(source_sha256=expected_hash, sha256=sha(destination), pixel_sha256=pixel_hash,
                source_bytes=source.stat().st_size, asset_bytes=destination.stat().st_size)


def prepare(source_root=DEFAULT_SOURCE, baseline_json=None, workers=8, include_baseline=True):
    source_root = Path(source_root).resolve()
    baseline_json = Path(baseline_json) if baseline_json else ROOT / 'public/data/demo/manga_multilingual.json'
    baseline = read_json(baseline_json)
    manifest = read_json(source_root / 'manifest.json')
    profiles = manifest['scope']['profiles']
    languages = manifest['scope']['languages']
    if len(profiles) != len(set(profiles)) or not profiles:
        raise ValueError('Model profiles must be distinct and nonempty')
    if set(languages) != {hit['language'] for hit in baseline}:
        raise ValueError('Language coverage differs from the existing multilingual task')
    base = {(hit['language'], hit['page_key']): hit for hit in baseline}
    if len(base) != len(baseline):
        raise ValueError('Duplicate baseline page/language identity')
    page_keys = {hit['page_key'] for hit in baseline}
    originals = {}
    for row in manifest['originals']:
        path = checked_path(source_root, row['text_json'])
        document = read_json(path)
        key = document['original_image']
        if key in originals or key not in page_keys:
            raise ValueError(f'Duplicate or unknown original page: {key}')
        image = checked_path(source_root, row['image'])
        if sha(image) != row['sha256']:
            raise ValueError(f'Original hash mismatch: {key}')
        for language in languages:
            task = base[(language, key)]
            if task['metadata']['original_sha256'] != row['sha256'] or sha(ROOT / task['original_image']) != row['sha256']:
                raise ValueError(f'Original differs from the baseline task: {key}')
        regions = {r['region_id']: r for r in document['regions']}
        if len(regions) != len(document['regions']):
            raise ValueError(f'Duplicate Japanese annotation: {key}')
        originals[key] = (row, document, regions)
    if set(originals) != page_keys:
        raise ValueError('Original page coverage differs from baseline')
    completed = {}
    for row in manifest['images']:
        identity = (row['profile'], row['target_language'], row['original_dataset_image'])
        profile, language, key = identity
        if identity in completed or profile not in profiles or language not in languages or key not in originals:
            raise ValueError(f'Duplicate or unknown translated identity: {identity}')
        text_path = checked_path(source_root, row['text_json'])
        if sha(text_path) != row['text_json_sha256']:
            raise ValueError(f'Text hash mismatch: {identity}')
        document = read_json(text_path)
        original_row, source, original_regions = originals[key]
        if (document['profile'], document['target_language'], document['original_dataset_image']) != identity or document['status'] != 'completed':
            raise ValueError(f'Translation identity or status mismatch: {identity}')
        if document['page_id'] != source['page_id'] or document['page_index'] != source['page_index']:
            raise ValueError(f'Translation page index mismatch: {identity}')
        regions = document['regions']
        if {r['region_id'] for r in regions} != set(original_regions) or len(regions) != len(original_regions):
            raise ValueError(f'Japanese region identities differ: {identity}')
        for region in regions:
            original = original_regions[region['region_id']]
            if region['text_ja'] != original['text_ja'] or region['text_bounding_box'] != original['text_bounding_box']:
                raise ValueError(f'Japanese text or bounding box mismatch: {identity}')
            if not isinstance(region['text_translated'], str) or not isinstance(region['rendered_text'], str):
                raise ValueError(f'Invalid translated text: {identity}')
        order = document.get('reading_order')
        if order:
            if len(order) != len(regions) or set(order) != set(original_regions):
                raise ValueError(f'Invalid reading order: {identity}')
            by_id = {r['region_id']: r for r in regions}
            regions = [by_id[region_id] for region_id in order]
        completed[identity] = (row, document, regions)
    missing = {}
    for row in manifest['missing_pages']:
        identity = (row['profile'], row['target_language'], row['original_dataset_image'])
        if identity in missing or identity in completed:
            raise ValueError(f'Duplicate or contradictory missing page: {identity}')
        missing[identity] = row
    expected = {(profile, language, key) for profile in profiles for language in languages for key in page_keys}
    if set(completed) | set(missing) != expected:
        raise ValueError('Manifest does not account for every expected output')
    assets = ROOT / 'evaluation_assets/multilingual_comparison'
    cache_path = assets / 'manifest.json'
    previous = read_json(cache_path).get('images', {}) if cache_path.is_file() else {}
    image_cache = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {}
        for identity, (row, document, regions) in completed.items():
            relative = Path(row['image']).with_suffix('.webp').as_posix()
            destination = assets / relative
            if not destination.resolve().is_relative_to(assets.resolve()):
                raise ValueError('Unsafe asset destination')
            job = pool.submit(lossless_asset, checked_path(source_root, row['image']), destination,
                              row['sha256'], previous.get(relative))
            jobs[job] = relative
        for index, future in enumerate(as_completed(jobs), 1):
            image_cache[jobs[future]] = future.result()
            if index % 100 == 0 or index == len(jobs):
                write_json(cache_path, {'format': 'pixel-identical lossless WebP', 'images': image_cache})
                print(f'{index}/{len(jobs)} images packaged and verified', flush=True)
    tasks = []
    for original_task in baseline:
        language, key = original_task['language'], original_task['page_key']
        task = {name: copy.deepcopy(original_task[name]) for name in ['page_key', 'language', 'language_label', 'original_image', 'reference_texts', 'reference_texts_ja', 'metadata']}
        task['id'] = f'multilingual-comparison50:{language}:{key}'
        task['metadata'].pop('translated_sha256', None)
        candidates = []
        if include_baseline:
            candidate = {name: copy.deepcopy(original_task[name]) for name in ['translated_image', 'translation_regions', 'metadata']}
            candidate.update(id='baseline', available=True, fidelity_score=None, presentation_score=None)
            for region in candidate.get('translation_regions') or []:
                region.update(quality_score=None, presentation_score=None, edits=[])
            candidates.append(candidate)
        for profile in profiles:
            identity = (profile, language, key)
            if identity not in completed:
                candidates.append(dict(id=profile, available=False, translated_image=None, translation_regions=[],
                                       fidelity_score=None, presentation_score=None,
                                       metadata={'missing_reason': missing[identity]['reason']}))
                continue
            row, document, regions = completed[identity]
            relative = Path(row['image']).with_suffix('.webp').as_posix()
            packed = image_cache[relative]
            candidate = dict(id=profile, available=True, translated_image=(assets / relative).relative_to(ROOT).as_posix(),
                             fidelity_score=None, presentation_score=None, translation_regions=[],
                             metadata=dict(model=document['model'], target_language=language,
                                           translated_sha256=packed['sha256'], source_render_sha256=row['sha256'],
                                           pixel_sha256=packed['pixel_sha256'], source_text_json=row['text_json'],
                                           source_text_sha256=row['text_json_sha256'],
                                           translation_input_mode=row.get('translation_input_mode'),
                                           translation_fallback_used=row.get('translation_fallback_used')))
            for region in regions:
                candidate['translation_regions'].append(dict(id=region['region_id'], source=region['text_ja'],
                    target=region['text_translated'], rendered_text=region['rendered_text'],
                    bbox=region['text_bounding_box'], kind='text', source_alignment='exact_annotation',
                    render_status=region['render_status'], render_reason=region.get('render_reason'),
                    font_size=region.get('font_size'), quality_score=None, presentation_score=None, edits=[]))
            candidates.append(candidate)
        # A-F are stable for a source page across languages; model identities remain in exports.
        candidates.sort(key=lambda candidate: hashlib.sha256(f'{key}:{candidate["id"]}'.encode()).hexdigest())
        task.update(candidates=candidates, edits=[])
        tasks.append(task)
    license_path = ROOT / 'public/data/manga/fst_try/LICENSE.md'
    if license_path.is_file():
        shutil.copyfile(license_path, assets / 'LICENSE.md')
    output = ROOT / 'public/data/demo/manga_multilingual_comparison.json'
    write_json(output, tasks)
    report = dict(pages_per_language=dict(Counter(h['language'] for h in tasks)), tasks=len(tasks),
                  candidate_ids=['baseline'] + profiles if include_baseline else profiles,
                  completed_new_candidates=len(completed), missing_new_candidates=len(missing),
                  missing_by_language=dict(Counter(identity[1] for identity in missing)),
                  skipped_regions=sum(r['render_status'] == 'skipped' for _, _, regions in completed.values() for r in regions),
                  source_image_bytes=sum(i['source_bytes'] for i in image_cache.values()),
                  packaged_image_bytes=sum(i['asset_bytes'] for i in image_cache.values()),
                  missing_outputs=[dict(profile=i[0], language=i[1], page_key=i[2], reason=row['reason']) for i, row in missing.items()])
    write_json(output.with_suffix('.report.json'), report)
    print(json.dumps({k:v for k,v in report.items() if k != 'missing_outputs'}, indent=2), flush=True)
    return tasks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--baseline-json', type=Path)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--without-baseline', action='store_true')
    args = parser.parse_args()
    if args.workers < 1: parser.error('Workers must be positive')
    prepare(args.source_root, args.baseline_json, args.workers, not args.without_baseline)
