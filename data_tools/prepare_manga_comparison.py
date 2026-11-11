"""Package the shared agent/baseline pages without changing the single-system task."""
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT.parent / 'agent/manga_tryout/manga_agent/baselines/rendered_results'


def prepare(baseline_root=DEFAULT_BASELINE):
    baseline_root = Path(baseline_root)
    baseline = json.loads((baseline_root / 'translated_text.json').read_text())
    pages = {}
    for page in baseline['pages']:
        key = (page['manga'], f"{page['page_index']:03d}")
        if key in pages:
            raise ValueError(f'Duplicate baseline page: {key}')
        image = baseline_root / page['image']
        if image.parent != baseline_root or not image.is_file():
            raise ValueError(f'Invalid baseline image: {image}')
        if page['status'] != 'complete' or hashlib.sha256(image.read_bytes()).hexdigest() != page['image_sha256']:
            raise ValueError(f'Incomplete or changed baseline image: {image}')
        pages[key] = page
    original = json.loads((ROOT / 'public/data/demo/manga_translation.json').read_text())
    tasks, missing = [], []
    assets = ROOT / 'public/data/manga/comparison/baseline'
    for hit in original:
        key = (hit['metadata']['book_title'], hit['metadata']['filename_stem'])
        if key not in pages:
            missing.append(hit['id'])
            continue
        page = pages[key]
        destination = assets / page['image']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(baseline_root / page['image'], destination)
        agent = {k: copy.deepcopy(hit[k]) for k in ('translated_image', 'translation_regions', 'metadata')}
        agent.update(id='agent', fidelity_score=None, presentation_score=None)
        for region in agent['translation_regions']:
            region.update(quality_score=None, edits=[])
        other = dict(id='baseline', translated_image=destination.relative_to(ROOT / 'public').as_posix(),
                     fidelity_score=None, presentation_score=None,
                     metadata={'text_origin': 'image_transcription', 'transcription_notes': page.get('notes', '')},
                     translation_regions=[dict(id=f'baseline:{i+1}', target=r['text'], kind=r['kind'],
                                               uncertain=r.get('uncertain', False), quality_score=None, edits=[])
                                          for i, r in enumerate(page['regions'])])
        task = {k: copy.deepcopy(hit[k]) for k in ('original_image', 'reference_texts', 'reference_texts_ja', 'metadata')}
        # Stable, balanced A/B order; exported candidate IDs retain system identity.
        candidates = [agent, other]
        if int(hashlib.sha256(hit['id'].encode()).hexdigest(), 16) % 2:
            candidates.reverse()
        task.update(id=hit['id'].replace('openmantra:', 'comparison:', 1), candidates=candidates, edits=[])
        tasks.append(task)
    output = ROOT / 'public/data/demo/manga_comparison.json'
    output.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + '\n')
    report = dict(pages=len(tasks), excluded_agent_pages=missing, baseline_pages=len(pages),
                  unused_baseline_pages=len(pages)-len(tasks), candidate_order='stable SHA-256 parity per page')
    output.with_suffix('.report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return tasks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root', type=Path, default=DEFAULT_BASELINE)
    prepare(parser.parse_args().baseline_root)
