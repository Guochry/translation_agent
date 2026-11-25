import { cloneSubtitleData, restoreTranslationAnnotations } from './subtitle-util.js';

export const BOOK_FIDELITY = { name: 'quality_score', label: 'Fidelity to the English fable', min: 0, max: 100, step: 5 };
export const BOOK_PROSE = { name: 'presentation_score', label: 'Prose quality in the target language', min: 0, max: 100, step: 5 };

const SMALL_TITLE_WORDS = new Set(['a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'in', 'nor', 'of', 'on', 'or', 'the', 'to', 'with']);

export function bookDisplayTitle(title) {
    if (title !== title.toUpperCase()) return title;
    return title.toLowerCase().replace(/[a-z]+(?:['’][a-z]+)*/g, (word, offset, text) => {
        if (offset > 0 && offset + word.length < text.length && SMALL_TITLE_WORDS.has(word)) return word;
        return word[0].toUpperCase() + word.slice(1);
    });
}

export function bookCandidateDisplayText(candidate) {
    const text = candidate.translation_regions[0]?.target ?? '';
    if (candidate.id !== 'human_reference') return text;
    // References join the title and body with a blank line. The body can contain
    // blank lines in the middle of words, so reflow every break after the title.
    const titleEnd = text.indexOf('\n\n');
    const bodyStart = titleEnd < 0 ? 0 : titleEnd + 2;
    // Keep the original character offsets for saved and newly marked spans.
    return text.slice(0, bodyStart) + text.slice(bodyStart).replace(/[\n\r\u2028\u2029]/g, '\u200b');
}

function bookContent(hit) {
    return JSON.stringify([hit.task_type, hit.schema_version, hit.id, hit.language, hit.source_index,
        hit.source_language, hit.title, hit.source, hit.candidates.map(candidate =>
            [candidate.id, candidate.model, candidate.available,
                candidate.translation_regions.map(region => [region.id, region.target])])]);
}

export function restoreBookAnnotations(canonical, saved) {
    const savedById = new Map(Array.isArray(saved) ? saved.map(hit => [hit?.id, hit]) : []);
    const canonicalById = new Map(canonical.map(hit => [hit.id, hit]));
    const compatible = canonical.map(hit => {
        const oldCandidates = savedById.get(hit.id)?.candidates;
        if (!Array.isArray(oldCandidates)) return hit;
        const beforeReference = hit.language === 'zh-CN' && oldCandidates.length === hit.candidates.length - 1;
        const candidates = beforeReference ? hit.candidates.filter(c => c.id !== 'human_reference') : hit.candidates;
        // Validate the export against the old empty slots before adding newly published text.
        return { ...hit, candidates: candidates.map((candidate, index) => candidate.available && oldCandidates[index]?.available === false
            ? { ...candidate, available: false, translation_regions: [] }
            : candidate) };
    });
    return restoreTranslationAnnotations(compatible, saved, bookContent, 'book').map(hit => {
        const restoredById = new Map(hit.candidates.map(candidate => [candidate.id, candidate]));
        hit.candidates = canonicalById.get(hit.id).candidates.map(candidate => {
            const restored = restoredById.get(candidate.id);
            if (restored?.available === candidate.available) return restored;
            return { ...cloneSubtitleData(candidate), comment: '', annotation_issue: null };
        });
        const origin = hit.post_edit_origin;
        if (origin?.type === 'candidate') {
            const index = hit.candidates.findIndex(candidate => candidate.id === origin.candidate_id);
            origin.candidate_label = `Translation ${String.fromCharCode(65 + index)}`;
        }
        return hit;
    });
}

export function validateBookDataset(data, languages) {
    const hasText = value => typeof value === 'string' && !!value.trim();
    if (!Array.isArray(data) || !data.length) throw new Error('No book tasks found.');
    const ids = new Set();
    for (const hit of data) {
        if (hit?.task_type !== 'book_evaluation' || hit.schema_version !== 1
            || !hasText(hit.id) || ids.has(hit.id) || !languages.includes(hit.language)
            || hit.source_language !== 'en' || !hasText(hit.title) || !hasText(hit.source)
            || !Array.isArray(hit.candidates) || !hit.candidates.some(candidate => candidate?.available))
            throw new Error('Invalid book task or duplicate ID.');
        ids.add(hit.id);
        const candidateIds = new Set();
        for (const candidate of hit.candidates) {
            if (!hasText(candidate?.id) || candidateIds.has(candidate.id) || typeof candidate.available !== 'boolean'
                || !Array.isArray(candidate.translation_regions)
                || candidate.translation_regions.length !== Number(candidate.available)
                || candidate.translation_regions.some(region => !hasText(region?.id) || !hasText(region.target)))
                throw new Error('Invalid book translation candidate.');
            candidateIds.add(candidate.id);
        }
    }
    for (const language of languages) if (!data.some(hit => hit.language === language)) throw new Error(`No fables for language ${language}.`);
}
