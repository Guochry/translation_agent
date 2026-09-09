"""Extend Geyang's round-0 strength export without changing existing annotations.

Run from this project checkout: python thresh/data_tools/add_hy_candidates.py
Hy inference files are JSON Lines despite their .json extensions.
"""
import copy
import hashlib
import json
from pathlib import Path


def extend(original, model_rows):
    result = copy.deepcopy(original)
    assert len({r['id'] for r in original}) == len(original)
    for model, records in model_rows.items():
        index = {}
        for r in records:
            language = 'zh_CN' if r['title'] == 'Havoc in Heaven' else 'en'
            key = (r['title'], language, r[language])
            if key in index:
                raise ValueError(f'{model}: duplicate source identity')
            index[key] = r
        for r in result:
            metadata = r['metadata']
            source = r['candidates'][0]['source']
            assert all(c['source'] == source for c in r['candidates'])
            assert model not in {c['id'] for c in r['candidates']}
            key = (metadata['title'], metadata['source_language'], source)
            if key not in index:
                raise ValueError(f'{model}: missing translation for {r["id"]}')
            inference = index[key]
            target = inference.get('llm_completion')
            if not isinstance(target, str) or not target.strip():
                raise ValueError(f'{model}: empty translation for {r["id"]}')
            # Check the matching human reference too; never join by line number.
            human = next(c for c in r['candidates'] if c['id'] == 'human_reference')
            assert inference[metadata['target_language']] == human['target']
            r['candidates'].append(dict(id=model, source=source, target=target,
                metadata=dict(kind='model', model=model), edits=[], overall_score=None))
    for before, after in zip(original, result):
        assert after['candidates'][:len(before['candidates'])] == before['candidates']
        assert {k: v for k, v in after.items() if k != 'candidates'} == {
            k: v for k, v in before.items() if k != 'candidates'}
    return result


def main():
    thresh = Path(__file__).resolve().parents[1]
    root = thresh.parent
    source = root / 'annotation_data/strength-geyang-round_0.json'
    original_bytes = source.read_bytes()
    original = json.loads(original_bytes)
    model_rows = {}
    for model in ['hy-mt2-7b', 'hy-mt2-30b-a3b']:
        path = root / f'data/llm_infer/res/{model}.json'
        model_rows[model] = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    result = extend(original, model_rows)
    assert len(result) == 50
    assert all(len(r['candidates']) == 8 for r in result)
    output = thresh / 'public/data/strength_geyang_round_0_with_hy.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    assert json.loads(output.read_text()) == result
    assert source.read_bytes() == original_bytes
    print(f'{output}: {len(result)} items, eight candidates each')
    print('Preserved all original candidates, scores, edits, timing, and improved translations.')
    print('Original export SHA-256:', hashlib.sha256(original_bytes).hexdigest())


if __name__ == '__main__':
    main()
