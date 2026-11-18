#!/usr/bin/env python3
"""Package existing subtitle outputs; no inference or video re-encoding.

Default media are ignored local symlinks. Use --media-mode copy to stage files
for a public host, retaining the same relative URL layout.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/coc/pskynet6/gguo37/agentic_translation')
MODELS = ('qwen27b', 'gemma31b', 'cohere', 'gpt', 'translategemma27b')
LANGUAGES = ('en', 'vi', 'ka', 'ar', 'hi', 'ru')
MEDIA_PREFIX = 'evaluation_assets/subtitle_evaluation/'
CONTEXT_SOURCE = ROOT / 'data/monkey_king/subtitle_records.json'


def english_context(records, subtitle_records, window=5):
    """Resolve English neighbors by record ID on the same chronological track.

    Verify every neighbor against the existing Chinese context before attaching
    its paired English subtitle. Repeated lines are never matched by text alone.
    """
    rows = sorted(subtitle_records, key=lambda row: row['time_order'])
    positions = {str(row['id']): i for i, row in enumerate(rows)}
    if len(positions) != len(rows) or len({row['time_order'] for row in rows}) != len(rows):
        raise ValueError('Duplicate subtitle record IDs or chronological positions')
    tracks = {(row.get('source_document'), row.get('target_document')) for row in rows}
    if len(tracks) != 1:
        raise ValueError('English context must come from one subtitle track')
    result = {}
    for record in records:
        rid = str(record['source_record_id'])
        if rid not in positions:
            raise ValueError(f'No subtitle context record for {rid}')
        index = positions[rid]
        if re.sub(r'\s+', '', rows[index]['target_text']) != re.sub(r'\s+', '', record['zh_CN']):
            raise ValueError(f'Source text does not match subtitle record {rid}')
        result[rid] = {}
        for key, neighbors in [('context_before', rows[max(0, index-window):index]),
                               ('context_after', rows[index+1:index+1+window])]:
            if [row['target_text'] for row in neighbors] != record.get(key, []):
                raise ValueError(f'{key} does not match chronological subtitle records for {rid}')
            if any(not isinstance(row.get('source_text'), str) or not row['source_text'].strip() for row in neighbors):
                raise ValueError(f'Missing English {key} for {rid}')
            result[rid][key + '_en'] = [row['source_text'] for row in neighbors]
    return result


def parse_srt(text):
    """Read actual rendered cue boundaries, including multiline/Unicode text."""
    cues = []
    pattern = re.compile(r'^(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})$')
    def seconds(value):
        match = pattern.fullmatch(value.strip())
        if not match:
            raise ValueError(f'Invalid SRT timestamp: {value}')
        h, m, s, ms = map(int, match.groups())
        if m >= 60 or s >= 60:
            raise ValueError(f'Invalid SRT timestamp: {value}')
        return h * 3600 + m * 60 + s + ms / 1000
    for block in re.split(r'\n\s*\n', text.lstrip('\ufeff').replace('\r\n', '\n').strip()):
        if not block.strip():
            continue
        lines = block.splitlines()
        if lines[0].strip().isdigit():
            lines = lines[1:]
        if len(lines) < 2 or ' --> ' not in lines[0]:
            raise ValueError('Invalid SRT cue')
        start, end = map(seconds, lines[0].split(' --> '))
        if end <= start or (cues and start < cues[-1]['end_seconds'] - 0.001):
            raise ValueError('Invalid or overlapping SRT interval')
        target = '\n'.join(lines[1:]).strip()
        if not target:
            raise ValueError('Empty SRT cue')
        cues.append({'id': str(len(cues) + 1), 'start_seconds': start, 'end_seconds': end, 'target': target})
    if not cues:
        raise ValueError('No SRT cues')
    return cues


def candidate_order(record_id):
    # Stable across languages; adding other clips does not change any labels.
    return sorted(MODELS, key=lambda model: hashlib.sha256(f'subtitle-v1:{record_id}:{model}'.encode()).hexdigest())


def stage_media(source, relative, media_dir, mode):
    source = Path(source)
    size = source.stat().st_size
    if not size:
        raise ValueError(f'Empty video: {source}')
    target = media_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.resolve() == source.resolve() and (mode == 'link' or not target.is_symlink()):
        return MEDIA_PREFIX + relative, size
    if target.is_symlink() and (mode == 'copy' or target.resolve() != source.resolve()):
        target.unlink()
    if mode == 'link':
        if target.is_file() and not target.is_symlink():
            target.unlink()
        if not target.exists():
            target.symlink_to(source.resolve())
    elif not target.exists() or target.stat().st_size != size or target.stat().st_mtime_ns != source.stat().st_mtime_ns:
        shutil.copy2(source, target)
    return MEDIA_PREFIX + relative, size


def load_candidate(runs, model, language, record, media_dir, mode):
    rid = str(record['source_record_id'])
    folder = runs / model / ('' if language == 'en' else language) / rid
    state_path = folder / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    result = {'id': model, 'available': False, 'fidelity_score': None, 'presentation_score': None,
              'translation_regions': [], 'metadata': {'system': model, 'model': state.get('model')}}
    if state.get('status') != 'completed':
        result['unavailable_reason'] = 'Translation unavailable.'
        return result
    video = folder / 'translated.mp4'
    srt = folder / 'translation.srt'
    if not video.is_file() or not srt.is_file():
        raise ValueError(f'Completed output is missing media/text: {folder}')
    cues = parse_srt(srt.read_text(encoding='utf-8-sig'))
    for cue in cues:
        # These runs translate one source passage per clip. For multi-cue output,
        # source is clip-level context, not an invented word-level alignment.
        cue.update(source=record['zh_CN'], source_scope='clip', quality_score=None, presentation_score=None, edits=[])
    url, size = stage_media(video, f'{model}/{language}/{rid}.mp4', media_dir, mode)
    result.update(available=True, translated_video=url, translation=state['translation'], translation_regions=cues)
    result['metadata'].update(render_identity=state.get('render_identity'), translation_identity=state.get('translation_identity'),
                              video_bytes=size, subtitle_sha256=hashlib.sha256(srt.read_bytes()).hexdigest())
    return result


def prepare(dataset, runs, output, media_dir, mode='link', workers=12, context_source=CONTEXT_SOURCE):
    records = json.loads(dataset.read_text())
    if len({r['source_record_id'] for r in records}) != len(records):
        raise ValueError('Duplicate source record IDs')
    contexts = english_context(records, json.loads(context_source.read_text()))
    # Source media location is declared by the run config, never guessed by name.
    config = json.loads((runs / 'gpt/config.json').read_text())
    clips_dir = Path(config['clips_dir'])
    source_media = {}
    for record in records:
        relative = record['clip_path']
        original = clips_dir / Path(relative).name
        url, size = stage_media(original, f'original/{record["source_record_id"]}.mp4', media_dir, mode)
        source_media[str(record['source_record_id'])] = (url, size)
    def task(pair):
        language, index, record = pair
        rid = str(record['source_record_id'])
        url, size = source_media[rid]
        candidates = [load_candidate(runs, model, language, record, media_dir, mode) for model in candidate_order(rid)]
        refs = [{'language': code, 'text': record[code]} for code in ('en', 'vi', 'ru') if record.get(code)]
        return {'id': f'subtitle-{language}-{rid}', 'task_type': 'subtitle_evaluation', 'schema_version': 1,
                'language': language, 'clip_id': rid, 'clip_index': index + 1, 'title': record.get('title', ''),
                'source_language': 'zh', 'source': record['zh_CN'], 'original_video': url,
                'duration_seconds': record['clip_duration_ms'] / 1000, 'references': refs,
                'context_before': record.get('context_before', []), 'context_after': record.get('context_after', []),
                **contexts[rid],
                'bookmark': False, 'candidates': candidates,
                'metadata': {'original_video_bytes': size, 'source_record_id': record['source_record_id'],
                             'source_dataset': dataset.name, 'source_interval_ms': record.get('subtitle_interval_ms'),
                             'candidate_order_seed': 'subtitle-v1', 'source_sha256': hashlib.sha256(record['zh_CN'].encode()).hexdigest()}}
    pairs = [(language, index, record) for language in LANGUAGES for index, record in enumerate(records)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        data = list(pool.map(task, pairs))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    available = sum(c['available'] for hit in data for c in hit['candidates'])
    print(f'Wrote {len(data)} tasks, {len(records)} clips/language, {available}/{len(data) * len(MODELS)} rendered candidates: {output}')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, default=ROOT / 'agent/subtitle_tryout/subtitle_agent/runs')
    parser.add_argument('--dataset', type=Path, default=ROOT / 'data/final/processed/monkey_king.json')
    parser.add_argument('--context-source', type=Path, default=CONTEXT_SOURCE)
    parser.add_argument('--output', type=Path, default=REPO / 'public/data/demo/subtitle_multilingual.json')
    parser.add_argument('--media-dir', type=Path, default=REPO / MEDIA_PREFIX)
    parser.add_argument('--media-mode', choices=['link', 'copy'], default='link')
    parser.add_argument('--workers', type=int, default=12)
    args = parser.parse_args()
    prepare(args.dataset, args.runs, args.output, args.media_dir, args.media_mode, args.workers, args.context_source)


if __name__ == '__main__':
    main()
