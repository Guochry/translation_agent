"""Validate Japanese source mappings without assuming region-list order."""
import hashlib
import json


def fingerprint(hit):
    content = {'page_key': hit.get('page_key'), 'language': hit.get('language'),
               'sources': hit.get('reference_texts_ja', []), 'references': hit.get('reference_texts', []),
               'regions': [{'id': r['id'], 'target': r['target']} for r in hit.get('translation_regions') or []]}
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def apply_alignment(hit, record):
    if record.get('fingerprint') != fingerprint(hit):
        raise ValueError(f'Stale Japanese alignment for {hit["id"]}')
    regions = hit.get('translation_regions') or []
    rows = record.get('regions')
    if not isinstance(rows, list) or len(rows) != len(regions):
        raise ValueError(f'Incomplete Japanese alignment for {hit["id"]}')
    mapped = {}
    sources = hit.get('reference_texts_ja', [])
    for row in rows:
        region_id = row.get('region_id')
        indices = row.get('source_indices')
        status = row.get('status')
        if region_id in mapped or not isinstance(indices, list) or len(set(indices)) != len(indices):
            raise ValueError('Invalid or duplicate source mapping')
        if any(type(i) is not int or not 0 <= i < len(sources) for i in indices):
            raise ValueError('Source index outside Japanese references')
        if status not in ('matched', 'uncertain', 'unmatched') or (status == 'matched' and not indices) or (status == 'unmatched' and indices):
            raise ValueError('Invalid source mapping status')
        mapped[region_id] = row
    if set(mapped) != {r['id'] for r in regions}:
        raise ValueError('Source mapping region identities differ')
    for region in regions:
        row = mapped[region['id']]
        indices = [i for i in row['source_indices'] if sources[i].strip()]
        region['source_reference_indices'] = indices
        region['source'] = '\n'.join(sources[i] for i in indices)
        region['source_alignment'] = row['status'] if indices else 'unmatched'
    hit.setdefault('metadata', {})['source_alignment_model'] = record.get('model')
    hit['metadata']['source_alignment_fingerprint'] = record['fingerprint']
    return hit
