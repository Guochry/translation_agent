import { regionSpans } from './manga-span-util.js';

export const cloneSubtitleData = value => JSON.parse(JSON.stringify(value));
export const validSubtitleScore = value => typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 100 && value % 5 === 0;
export const SUBTITLE_FIDELITY = { name: 'quality_score', label: 'Subtitle fidelity', min: 0, max: 100, step: 5 };
export const SUBTITLE_PRESENTATION = { name: 'presentation_score', label: 'Subtitle presentation', min: 0, max: 100, step: 5 };
export const SUBTITLE_ISSUES = {
    omission: 'Missing meaning',
    uncertain_source: 'Unclear source meaning',
    render_mismatch: 'Text differs from video',
    other: 'Other',
};
export const subtitleRegionRated = region => validSubtitleScore(region.quality_score) && validSubtitleScore(region.presentation_score);
export const subtitleCandidateRated = candidate => candidate.available !== false && candidate.translation_regions.length > 0
    && candidate.translation_regions.every(subtitleRegionRated);
export const subtitleClipRated = hit => hit.candidates.some(c => c.available !== false) && hit.candidates.filter(c => c.available !== false).every(subtitleCandidateRated);

function postEditOrigin(hit, text, origin) {
    if (!text.trim()) return null;
    // An older draft has no reliable starting-point information.
    if (origin == null) return { type: 'unknown' };
    if (origin.type === 'manual' || origin.type === 'unknown') return { type: origin.type };
    if (origin.type === 'candidate') {
        const index = hit.candidates.findIndex(candidate => candidate.id === origin.candidate_id && candidate.available !== false);
        const label = `Translation ${String.fromCharCode(65 + index)}`;
        if (index >= 0 && origin.candidate_label === label) return { type: 'candidate', candidate_id: origin.candidate_id, candidate_label: label };
    }
    throw new Error('Post-edit starting point does not match a translation candidate.');
}

export function updateSubtitlePostEdit(hit, text) {
    if (typeof text !== 'string') throw new Error('Post-edit must be text.');
    const origin = !(hit.post_edit || '').trim() ? { type: 'manual' } : hit.post_edit_origin;
    return { ...hit, post_edit: text, post_edit_origin: postEditOrigin(hit, text, origin) };
}

export function startSubtitlePostEdit(hit, candidateId) {
    if ((hit.post_edit || '').trim()) return hit;
    const index = hit.candidates.findIndex(candidate => candidate.id === candidateId && candidate.available !== false);
    if (index < 0) throw new Error('Translation candidate is unavailable.');
    const text = hit.candidates[index].translation_regions.map(region => region.target).join('\n');
    return { ...hit, post_edit: text, post_edit_origin: postEditOrigin(hit, text,
        { type: 'candidate', candidate_id: candidateId, candidate_label: `Translation ${String.fromCharCode(65 + index)}` }) };
}

// Explicit immutable content signature; an upload restores annotations onto the
// current dataset, never replacing its source, media URLs, timing, or model IDs.
// English context is supplementary reference data, restored from the current
// dataset so annotation files downloaded before it was added still import.
function content(hit) {
    return JSON.stringify([hit.task_type, hit.schema_version, hit.id, hit.language, hit.clip_id, hit.source_language, hit.source,
        hit.original_video, hit.duration_seconds, hit.references.map(r => [r.language, r.text]), hit.context_before, hit.context_after,
        hit.metadata?.source_sha256, hit.metadata?.original_video_bytes,
        hit.candidates.map(c => [c.id, c.available, c.translated_video, c.translation, c.metadata?.render_identity,
            c.metadata?.translation_identity, c.metadata?.video_bytes, c.metadata?.subtitle_sha256,
            c.translation_regions.map(r => [r.id, r.source, r.source_scope, r.target, r.start_seconds, r.end_seconds])])]);
}

export function validateSubtitleDataset(data, languages) {
    if (!Array.isArray(data) || !data.length) throw new Error('No subtitle tasks found.');
    const ids = new Set();
    for (const hit of data) {
        if (hit.task_type !== 'subtitle_evaluation' || hit.schema_version !== 1 || typeof hit.id !== 'string' || ids.has(hit.id)
            || !languages.includes(hit.language) || typeof hit.source !== 'string' || !hit.original_video
            || !Number.isFinite(hit.duration_seconds) || hit.duration_seconds <= 0
            || !Array.isArray(hit.references) || !Array.isArray(hit.context_before) || !Array.isArray(hit.context_after)
            || !Array.isArray(hit.candidates) || !hit.candidates.length) throw new Error('Invalid subtitle task or duplicate ID.');
        ids.add(hit.id);
        if (Object.hasOwn(hit, 'post_edit') && typeof hit.post_edit !== 'string') throw new Error('Post-edit must be text.');
        if (Object.hasOwn(hit, 'post_edit_origin')) postEditOrigin(hit, hit.post_edit || '', hit.post_edit_origin);
        for (const field of ['context_before', 'context_after']) {
            if (!Array.isArray(hit[field + '_en']) || hit[field + '_en'].length !== hit[field].length
                || hit[field + '_en'].some(line => typeof line !== 'string' || !line.trim()))
                throw new Error('English dialogue context is missing or does not match the source context.');
        }
        const candidates = new Set();
        for (const candidate of hit.candidates) {
            if (!candidate.id || candidates.has(candidate.id) || typeof candidate.available !== 'boolean' || !Array.isArray(candidate.translation_regions))
                throw new Error('Invalid subtitle candidate.');
            candidates.add(candidate.id);
            if (candidate.available && (!candidate.translated_video || !candidate.translation_regions.length)) throw new Error('Available candidate is missing video or subtitles.');
            const regions = new Set();
            for (const region of candidate.translation_regions) {
                if (!region.id || regions.has(region.id) || typeof region.source !== 'string' || typeof region.target !== 'string'
                    || !region.target.trim() || !Number.isFinite(region.start_seconds) || !Number.isFinite(region.end_seconds)
                    || region.start_seconds < 0 || region.end_seconds <= region.start_seconds) throw new Error('Invalid subtitle cue.');
                regions.add(region.id);
            }
        }
    }
    for (const language of languages) if (!data.some(hit => hit.language === language)) throw new Error(`No clips for language ${language}.`);
}

function restoreScore(value) {
    if (value == null || value === '') return null;
    if (!validSubtitleScore(value)) throw new Error('Scores must be 0–100 in steps of 5.');
    return value;
}

export function restoreSubtitleAnnotations(canonical, saved) {
    if (!Array.isArray(saved) || !saved.length) throw new Error('Upload an annotation JSON file from this subtitle task.');
    const byId = new Map(canonical.map(hit => [hit.id, hit]));
    const seen = new Set();
    return saved.map(hit => {
        const expected = byId.get(hit?.id);
        if (!expected || seen.has(hit.id)) throw new Error('The file contains unknown or duplicate clips.');
        seen.add(hit.id);
        let matches = false;
        try { matches = content(hit) === content(expected); } catch { /* incomplete upload */ }
        if (!matches) throw new Error('The file belongs to different subtitle content, video version, or candidate order.');
        const result = cloneSubtitleData(expected);
        if (Object.hasOwn(hit, 'post_edit') && typeof hit.post_edit !== 'string') throw new Error('Post-edit must be text.');
        result.post_edit = hit.post_edit ?? '';
        result.post_edit_origin = postEditOrigin(expected, result.post_edit, hit.post_edit_origin);
        result.bookmark = hit.bookmark === true;
        result.comment = typeof hit.comment === 'string' ? hit.comment : '';
        for (let i = 0; i < result.candidates.length; i++) {
            const target = result.candidates[i], source = hit.candidates[i];
            // Clip-level scores from older exports are obsolete; keep subtitle ratings.
            delete target.fidelity_score;
            delete target.presentation_score;
            target.comment = typeof source.comment === 'string' ? source.comment : '';
            const issue = source.annotation_issue;
            if (issue != null && (!Object.hasOwn(SUBTITLE_ISSUES, issue.category) || typeof issue.note !== 'string'))
                throw new Error('Invalid subtitle issue flag.');
            target.annotation_issue = issue == null ? null : { category: issue.category, note: issue.note };
            for (let j = 0; j < target.translation_regions.length; j++) {
                const region = target.translation_regions[j], savedRegion = source.translation_regions[j];
                region.quality_score = restoreScore(savedRegion.quality_score);
                region.presentation_score = restoreScore(savedRegion.presentation_score);
                const edits = savedRegion.edits ?? [];
                if (!Array.isArray(edits)) throw new Error('Invalid span annotations.');
                const spans = regionSpans({ target: region.target, edits });
                if (edits.some(edit => !['strength', 'error'].includes(edit.category) || !Number.isInteger(edit.id)
                    || !Array.isArray(edit.output_idx) || !edit.output_idx.length)
                    || spans.length !== edits.reduce((n, edit) => n + edit.output_idx.length, 0)
                    || new Set(edits.map(edit => edit.id)).size !== edits.length)
                    throw new Error('Invalid span annotations.');
                const ordered = [...spans].sort((a, b) => a.start - b.start);
                if (ordered.some((span, index) => index > 0 && span.start < ordered[index - 1].end)) throw new Error('Overlapping span annotations.');
                region.edits = cloneSubtitleData(edits);
            }
        }
        return result;
    });
}

export function resetSubtitleClip(hit) {
    const result = cloneSubtitleData(hit);
    result.post_edit = '';
    result.post_edit_origin = null;
    for (const candidate of result.candidates) {
        delete candidate.fidelity_score;
        delete candidate.presentation_score;
        candidate.comment = '';
        candidate.annotation_issue = null;
        for (const region of candidate.translation_regions) {
            region.quality_score = null;
            region.presentation_score = null;
            region.edits = [];
        }
    }
    return result;
}

export function subtitleMediaUrl(path, { dev = false, base = '/', prefix = 'evaluation_assets/subtitle_evaluation/', mediaBase = '' } = {}) {
    if (!path) return '';
    if (/^https?:\/\//i.test(path)) return path;
    if (dev) return '/' + path.replace(/^\/+/, '');
    if (mediaBase && path.startsWith(prefix)) return mediaBase.replace(/\/?$/, '/') + path.slice(prefix.length).split('/').map(encodeURIComponent).join('/');
    return '';
}
