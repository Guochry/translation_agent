#!/usr/bin/env python3
"""Order subtitle tasks by movie clip timestamps and publish 60/60/remaining batches."""
import argparse
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEM = 'subtitle_multilingual'
SOURCE_RECORDS = Path('/coc/pskynet6/gguo37/agentic_translation/data/final/processed/monkey_king.json')


def chronological_tasks(tasks, intervals=None):
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('Expected a nonempty subtitle task list')
    groups, seen = {}, set()
    for task in tasks:
        if task.get('id') in seen:
            raise ValueError('Duplicate task identity')
        seen.add(task['id'])
        groups.setdefault(task['language'], []).append(task)
    reference = {task['clip_id'] for task in next(iter(groups.values()))}
    for language, group in groups.items():
        if len(group) != len(reference) or {task['clip_id'] for task in group} != reference:
            raise ValueError(f'Clip coverage differs or duplicates exist for {language}')
    timeline = {}
    for clip_id in reference:
        source = (intervals or {}).get(clip_id)
        for group in groups.values():
            task = next(t for t in group if t['clip_id'] == clip_id)
            interval = source or task.get('metadata', {}).get('movie_interval_ms')
            if not isinstance(interval, dict) or any(not isinstance(interval.get(k), (int, float)) or isinstance(interval.get(k), bool)
                or not math.isfinite(interval[k]) for k in ('start', 'end')) or interval['start'] < 0 or interval['end'] <= interval['start']:
                raise ValueError(f'Missing or invalid movie interval for {clip_id}')
            if clip_id in timeline and timeline[clip_id] != interval:
                raise ValueError(f'Movie interval differs across languages for {clip_id}')
            timeline[clip_id] = copy.deepcopy(interval)
    order = sorted(reference, key=lambda clip_id: (timeline[clip_id]['start'], timeline[clip_id]['end'], clip_id))
    ordered = []
    for group in groups.values():
        by_clip = {task['clip_id']: task for task in group}
        for index, clip_id in enumerate(order, 1):
            record = copy.deepcopy(by_clip[clip_id])
            metadata = record.setdefault('metadata', {})
            metadata.setdefault('original_task_index', record['clip_index'])
            metadata.update(movie_interval_ms=timeline[clip_id], movie_order_index=index)
            record['clip_index'] = index
            ordered.append(record)
    return ordered, order, list(groups)


def split_tasks(tasks, sizes=(60, 60), intervals=None):
    ordered, order, languages = chronological_tasks(tasks, intervals)
    if len(sizes) != 2 or any(not isinstance(n, int) or isinstance(n, bool) or n <= 0 for n in sizes) or sum(sizes) >= len(order):
        raise ValueError('Two positive batch sizes must leave clips for the third part')
    boundaries = [0, sizes[0], sum(sizes), len(order)]
    parts = [[], [], []]
    for record in ordered:
        index = record['clip_index']
        number = 0 if index <= boundaries[1] else 1 if index <= boundaries[2] else 2
        item = copy.deepcopy(record)
        item['clip_index'] = index - boundaries[number]
        item['metadata'].update(evaluation_batch=f'part{number+1}', batch_clip_index=item['clip_index'])
        parts[number].append(item)
    return ordered, parts, order, languages, boundaries


def prepare(root=ROOT, input_path=None, source_records=SOURCE_RECORDS, sizes=(60, 60)):
    root = Path(root)
    input_path = Path(input_path) if input_path else root / f'public/data/demo/{STEM}.json'
    tasks = json.loads(input_path.read_text())
    intervals = None
    if any(not task.get('metadata', {}).get('movie_interval_ms') for task in tasks):
        rows = json.loads(Path(source_records).read_text())
        intervals = {str(row['source_record_id']): row['video_interval_ms'] for row in rows}
    ordered, parts, order, languages, bounds = split_tasks(tasks, sizes, intervals)
    input_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + '\n')
    template = (root / f'public/templates/demo/{STEM}.yml').read_text()
    report = {'order_basis': 'video_interval_ms.start in the original movie', 'clips_per_language': len(order), 'languages': languages, 'parts': []}
    for number, part in enumerate(parts, 1):
        start, end = bounds[number-1]+1, bounds[number]
        stem = f'{STEM}_part{number}'
        (root / f'public/data/demo/{stem}.json').write_text(json.dumps(part, ensure_ascii=False, indent=2) + '\n')
        title = f'Multilingual Subtitle Evaluation — Part {number} (clips {start}–{end})'
        config = template.replace(f'demo_{STEM}', f'demo_{stem}').replace(f'data/demo/{STEM}.json', f'data/demo/{stem}.json')
        config = config.replace('template_label: Multilingual Subtitle Evaluation', f'template_label: {title}')
        config += f'\nevaluation_title: "{title}"\nevaluation_batch: part{number}\n'
        (root / f'public/templates/demo/{stem}.yml').write_text(config)
        first = next(task for task in part if task['language'] == languages[0])
        last = [task for task in part if task['language'] == languages[0]][-1]
        report['parts'].append({'part': number, 'clips_per_language': end-start+1, 'movie_order_range': [start, end],
                                'first_clip_id': first['clip_id'], 'last_clip_id': last['clip_id'],
                                'movie_start_ms': first['metadata']['movie_interval_ms']['start'],
                                'movie_end_ms': last['metadata']['movie_interval_ms']['end'], 'task_records': len(part)})
    (root / f'public/data/demo/{STEM}_split.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--source-records', type=Path, default=SOURCE_RECORDS)
    parser.add_argument('--first-count', type=int, default=60)
    parser.add_argument('--second-count', type=int, default=60)
    args = parser.parse_args()
    prepare(input_path=args.input, source_records=args.source_records, sizes=(args.first_count, args.second_count))
