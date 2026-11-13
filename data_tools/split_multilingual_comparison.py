"""Split the current multilingual comparison into consecutive page batches per language."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEM = 'manga_multilingual_comparison'


def split_tasks(tasks, first_count=30):
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('Expected a nonempty comparison task list')
    groups = {}
    ids = set()
    for task in tasks:
        if task['id'] in ids:
            raise ValueError('Duplicate task identity')
        ids.add(task['id'])
        groups.setdefault(task['language'], []).append(task)
    reference = [task['page_key'] for task in next(iter(groups.values()))]
    if len(set(reference)) != len(reference):
        raise ValueError('Duplicate source page')
    if not 0 < first_count < len(reference):
        raise ValueError('Split must leave at least one source page in each batch')
    for language, group in groups.items():
        if [task['page_key'] for task in group] != reference:
            raise ValueError(f'Page order or coverage differs for {language}')
    parts = [[], []]
    for group in groups.values():
        for index, task in enumerate(group):
            part = 0 if index < first_count else 1
            record = copy.deepcopy(task)
            record.setdefault('metadata', {}).update(evaluation_batch=f'part{part + 1}', original_task_index=index + 1)
            parts[part].append(record)
    return parts, len(reference), list(groups)


def prepare(root=ROOT, input_path=None, first_count=30):
    root = Path(root)
    input_path = Path(input_path) if input_path else root / f'public/data/demo/{STEM}.json'
    tasks = json.loads(input_path.read_text(encoding='utf-8'))
    parts, total, languages = split_tasks(tasks, first_count)
    template = (root / f'public/templates/demo/{STEM}.yml').read_text(encoding='utf-8')
    reports = []
    for number, part in enumerate(parts, 1):
        start, end = (1, first_count) if number == 1 else (first_count + 1, total)
        count = end - start + 1
        stem = f'{STEM}_part{number}'
        output = root / f'public/data/demo/{stem}.json'
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(part, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(output)
        config = template.replace(f'demo_{STEM}', f'demo_{stem}').replace(f'data/demo/{STEM}.json', f'data/demo/{stem}.json')
        config = config.replace('template_label: Multilingual Manga Comparison', f'template_label: Multilingual Manga Comparison — Part {number} ({count} pages)')
        config = config.replace('## Multilingual Manga Comparison', f'## Multilingual Manga Comparison — Part {number} (pages {start}–{end})')
        config = config.replace(f'of {total} manga pages', f'of {count} manga pages')
        (root / f'public/templates/demo/{stem}.yml').write_text(config, encoding='utf-8')
        reports.append(dict(part=number, original_positions=[start, end], pages_per_language=count,
                            languages=languages, task_records=len(part), dataset=output.relative_to(root).as_posix()))
    report = dict(source=input_path.name, total_pages_per_language=total, parts=reports,
                  identity_note='Page/candidate IDs and A–F order are retained; original_task_index is one-based in the full task.')
    (root / f'public/data/demo/{STEM}_split.report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--first-count', type=int, default=30)
    args = parser.parse_args()
    prepare(input_path=args.input, first_count=args.first_count)
