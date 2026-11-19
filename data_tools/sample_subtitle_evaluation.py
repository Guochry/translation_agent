#!/usr/bin/env python3
"""Randomly select 80 clips favoring longer source text, then order by movie time."""
import argparse
import copy
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / 'data_tools/datasets/subtitle_multilingual_pool.json'


def sample_tasks(tasks, count=80, seed=20261119):
    groups, ids = {}, set()
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('Expected a nonempty task pool')
    for task in tasks:
        if task['id'] in ids:
            raise ValueError('Duplicate task ID')
        ids.add(task['id'])
        groups.setdefault(task['language'], []).append(task)
    reference = next(iter(groups.values()))
    by_clip = {task['clip_id']: task for task in reference}
    if not isinstance(count, int) or isinstance(count, bool) or count < 3 or count > len(by_clip):
        raise ValueError('Sample count must be between three and the number of clips')
    for language, rows in groups.items():
        if len(rows) != len(by_clip) or {row['clip_id'] for row in rows} != set(by_clip):
            raise ValueError(f'Clip coverage differs or duplicates exist for {language}')
        for row in rows:
            expected = by_clip[row['clip_id']]
            if row['source'] != expected['source'] or row['metadata']['movie_interval_ms'] != expected['metadata']['movie_interval_ms']:
                raise ValueError('Source or movie timestamp differs across languages')
    length = lambda clip_id: len(re.sub(r'\s+', '', by_clip[clip_id]['source']))
    ranked = sorted(by_clip, key=lambda clip_id: (length(clip_id), clip_id))
    n = len(ranked)
    strata = [ranked[:n//3], ranked[n//3:2*n//3], ranked[2*n//3:]]
    quotas = [min(len(stratum), max(1, int(count * weight))) for stratum, weight in zip(strata, [.2, .3, .5])]
    remaining = count - sum(quotas)
    while remaining > 0:
        for index in [2, 1, 0]:
            if remaining and quotas[index] < len(strata[index]):
                quotas[index] += 1
                remaining -= 1
    rng = random.Random(seed)
    selected = set()
    reports = []
    for name, stratum, quota in zip(['short', 'medium', 'long'], strata, quotas):
        picked = rng.sample(stratum, quota)
        selected.update(picked)
        reports.append({'group': name, 'pool_size': len(stratum), 'selected_count': quota,
                        'source_character_range': [min(map(length, stratum)), max(map(length, stratum))]})
    order = sorted(selected, key=lambda clip_id: (by_clip[clip_id]['metadata']['movie_interval_ms']['start'],
                    by_clip[clip_id]['metadata']['movie_interval_ms']['end'], clip_id))
    output = []
    for rows in groups.values():
        lookup = {row['clip_id']: row for row in rows}
        for index, clip_id in enumerate(order, 1):
            row = copy.deepcopy(lookup[clip_id])
            row['clip_index'] = index
            for field in ['evaluation_batch', 'batch_clip_index']:
                row['metadata'].pop(field, None)
            row['metadata'].update(selection_index=index, sampling_seed=seed, sampling_method='source_length_stratified_random')
            output.append(row)
    report = {'selection_count_per_language': count, 'pool_clips_per_language': n, 'seed': seed,
              'sampling_method': 'Random sampling within source-length strata, favoring longer text (20% short, 30% medium, 50% long)' ,
              'length_measure': 'Chinese source characters excluding whitespace',
              'order_basis': 'Original movie video_interval_ms.start', 'strata': reports,
              'selected_clip_ids_in_movie_order': order, 'languages': list(groups), 'task_records': len(output)}
    return output, report


def prepare(pool=POOL, count=80, seed=20261119, root=ROOT):
    root = Path(root)
    data, report = sample_tasks(json.loads(Path(pool).read_text()), count, seed)
    (root / 'public/data/demo/subtitle_multilingual.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    (root / 'public/data/demo/subtitle_multilingual_sample.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pool', type=Path, default=POOL)
    parser.add_argument('--count', type=int, default=80)
    parser.add_argument('--seed', type=int, default=20261119)
    args = parser.parse_args()
    prepare(args.pool, args.count, args.seed)
