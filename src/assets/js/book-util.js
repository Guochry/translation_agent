import { restoreTranslationAnnotations } from './subtitle-util.js';

export const BOOK_FIDELITY = { name: 'quality_score', label: 'Fidelity to the English fable', min: 0, max: 100, step: 5 };
export const BOOK_PROSE = { name: 'presentation_score', label: 'Prose quality in the target language', min: 0, max: 100, step: 5 };

function bookContent(hit) {
    return JSON.stringify([hit.task_type, hit.schema_version, hit.id, hit.language, hit.source_index,
        hit.source_language, hit.title, hit.source, hit.candidates.map(candidate =>
            [candidate.id, candidate.model, candidate.available,
                candidate.translation_regions.map(region => [region.id, region.target])])]);
}

export function restoreBookAnnotations(canonical, saved) {
    const savedById = new Map(Array.isArray(saved) ? saved.map(hit => [hit?.id, hit]) : []);
    const legacy = new Map();
    const compatible = canonical.map(hit => {
        const oldCandidates = savedById.get(hit.id)?.candidates;
        const referenceIndex = hit.language === 'zh-CN' ? hit.candidates.findIndex(c => c.id === 'human_reference') : -1;
        if (referenceIndex < 0 || !Array.isArray(oldCandidates) || oldCandidates.length !== hit.candidates.length - 1)
            return hit;
        legacy.set(hit.id, { referenceIndex, reference: hit.candidates[referenceIndex] });
        return { ...hit, candidates: hit.candidates.filter((_, index) => index !== referenceIndex) };
    });
    return restoreTranslationAnnotations(compatible, saved, bookContent, 'book').map(hit => {
        const upgrade = legacy.get(hit.id);
        if (!upgrade) return hit;
        const reference = JSON.parse(JSON.stringify(upgrade.reference));
        hit.candidates.splice(upgrade.referenceIndex, 0, { ...reference, comment: '', annotation_issue: null });
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
