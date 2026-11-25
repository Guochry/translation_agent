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
    return restoreTranslationAnnotations(canonical, saved, bookContent, 'book');
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
