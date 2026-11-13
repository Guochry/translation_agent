"""Add validated Japanese mappings to the multilingual extracted-text JSON files.

Translation text, extraction status, usage, notes, and images are preserved.
Existing JSON files are backed up before atomic replacement. No API calls.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

try:
    from data_tools.manga_source_alignment import apply_alignment
except ModuleNotFoundError:
    from manga_source_alignment import apply_alignment

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / 'agent/manga_tryout/manga_agent/baselines/multilingual_50'


def enrich_document(code, document, tasks, alignments):
    """Return an enriched copy, refusing stale or mismatched target text."""
    output = json.loads(json.dumps(document, ensure_ascii=False))
    expected = {hit['page_key']: hit for hit in tasks if hit['language'] == code}
    pages = output.get('pages')
    if not expected or not isinstance(pages, list):
        raise ValueError(f'{code}: missing task data or extracted pages')
    if len(pages) != len(expected) or {page.get('image') for page in pages} != set(expected):
        raise ValueError(f'{code}: extracted page coverage differs from the platform task')
    totals = Counter()
    for page in pages:
        hit = json.loads(json.dumps(expected[page['image']], ensure_ascii=False))
        targets = hit.get('translation_regions')
        extracted = page.get('regions')
        if targets is None:
            if page.get('status') == 'complete' or extracted:
                raise ValueError(f'{code}/{page["image"]}: extraction availability differs')
            page_state = 'extraction_unavailable'
        else:
            if page.get('status') != 'complete' or not isinstance(extracted, list):
                raise ValueError(f'{code}/{page["image"]}: extraction is incomplete')
            if len(extracted) != len(targets) or any(r.get('text') != t['target'] for r, t in zip(extracted, targets)):
                raise ValueError(f'{code}/{page["image"]}: extracted translation text differs')
            if page.get('image_sha256') != hit['metadata']['translated_sha256']:
                raise ValueError(f'{code}/{page["image"]}: translated image hash differs')
            if targets:
                record = alignments.get(hit['id'])
                if not record:
                    raise ValueError(f'{code}/{page["image"]}: Japanese alignment is missing')
                apply_alignment(hit, record)
                for region, matched in zip(extracted, hit['translation_regions']):
                    region['source_text'] = matched['source']
                    region['source_reference_indices'] = matched['source_reference_indices']
                    region['source_alignment'] = matched['source_alignment']
                    totals[matched['source_alignment']] += 1
                page_state = 'aligned'
            else:
                page_state = 'no_extracted_regions'
        page['reference_texts_ja'] = hit['reference_texts_ja']
        page['japanese_alignment'] = {
            'status': page_state,
            'original_image': 'originals/' + page['image'],
            'original_sha256': hit['metadata']['original_sha256'],
            'source_language': 'ja',
            'reference_origin': 'OpenMantra Japanese annotations',
            'model': alignments.get(hit['id'], {}).get('model'),
            'input_fingerprint': alignments.get(hit['id'], {}).get('fingerprint'),
        }
    output['japanese_alignment_summary'] = {
        'source_language': 'ja', 'target_language_code': code,
        'pages': len(pages), 'regions': sum(totals.values()), 'region_status_counts': dict(totals),
        'method': 'Semantic matching to existing Japanese references; Japanese text is copied verbatim.',
        'unmatched_note': 'Empty source_text means no source match was established; it does not prove the translation was added.',
    }
    return output


def export(source_root=DEFAULT_SOURCE, dataset=None, alignment_file=None):
    source_root = Path(source_root)
    dataset = Path(dataset) if dataset else ROOT / 'public/data/demo/manga_multilingual.json'
    alignment_file = Path(alignment_file) if alignment_file else ROOT / 'public/data/demo/manga_multilingual.alignments.json'
    tasks = json.loads(dataset.read_text(encoding='utf-8'))
    alignments = json.loads(alignment_file.read_text(encoding='utf-8'))['pages']
    changes, reports = [], {}
    for code in sorted({hit['language'] for hit in tasks}):
        path = source_root / code / 'translated_text.json'
        original = json.loads(path.read_text(encoding='utf-8'))
        updated = enrich_document(code, original, tasks, alignments)
        reports[code] = updated['japanese_alignment_summary']['region_status_counts']
        if updated != original:
            changes.append((code, path, updated))
    # Validate every language before writing any file, then back up all changed files.
    backup = None
    if changes:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        backup = source_root / 'japanese_alignment_backups' / stamp
        for code, path, updated in changes:
            saved = backup / code / 'translated_text.json'
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
        for code, path, updated in changes:
            temporary = path.with_name(path.name + '.japanese-alignment.tmp')
            temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temporary.replace(path)
    report = {'updated_languages': [code for code, _, _ in changes],
              'backup_directory': str(backup) if backup else None, 'region_status_counts': reports}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--alignments', type=Path)
    args = parser.parse_args()
    export(args.source_root, args.dataset, args.alignments)
