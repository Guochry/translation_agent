export const SPAN_CATEGORIES = Object.freeze(['strength', 'okay', 'error']);

export function regionSpans(region) {
    const target = typeof region.target === 'string' ? region.target : '';
    return (region.edits || []).filter(edit => SPAN_CATEGORIES.includes(edit.category)).flatMap(edit =>
        (Array.isArray(edit.output_idx) ? edit.output_idx : []).filter(span => Array.isArray(span) && span.length === 2
            && Number.isInteger(span[0]) && Number.isInteger(span[1]) && span[0] >= 0 && span[1] > span[0] && span[1] <= target.length)
            .map(([start, end]) => ({ start, end, id: edit.id, category: edit.category })));
}

export function labelRegionSpan(region, start, end, category) {
    if (!SPAN_CATEGORIES.includes(category) || !Number.isInteger(start) || !Number.isInteger(end)
        || start < 0 || end <= start || end > region.target.length || !region.target.slice(start, end).trim()) return region;
    const spans = regionSpans(region);
    const exact = spans.find(span => span.start === start && span.end === end);
    if (exact) return { ...region, edits: region.edits.map(edit => edit.id === exact.id && edit.category === exact.category
        ? { ...edit, category } : edit) };
    if (spans.some(span => span.start < end && span.end > start)) throw new Error('Remove the overlapping highlight first.');
    const id = Math.max(0, ...(region.edits || []).map(edit => edit.id).filter(Number.isInteger)) + 1;
    return { ...region, edits: [...(region.edits || []), { category, id, annotation: null, output_idx: [[start, end]] }] };
}
