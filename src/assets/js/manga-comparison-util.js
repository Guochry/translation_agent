import { isValidScore, scoreField } from './score-util.js';
import { isValidTranslationQuality, isRegionRated } from './manga-util.js';

export function comparisonRated(hit, scores) {
    if (!Array.isArray(hit?.candidates)) return false;
    const candidates = hit.candidates.filter(candidate => candidate.available !== false);
    return hit.candidates.length >= 2 && candidates.length > 0 && scores.length > 0
        && candidates.every(candidate => scores.every(score => isValidScore(candidate[scoreField(score)], score))
            && Array.isArray(candidate.translation_regions)
            && candidate.translation_regions.every(region => isRegionRated(region)));
}

export function normalizeComparison(hit, scores) {
    for (const candidate of hit.candidates || []) {
        for (const score of scores) {
            const field = scoreField(score);
            if (!isValidScore(candidate[field], score)) candidate[field] = null;
        }
        for (const region of candidate.translation_regions || []) {
            if (!isValidTranslationQuality(region.quality_score)) region.quality_score = null;
            if (!isValidTranslationQuality(region.presentation_score)) region.presentation_score = null;
            region.edits = region.edits || [];
        }
    }
}

export function resetComparison(hit, scores) {
    for (const candidate of hit.candidates || []) {
        for (const score of scores) candidate[scoreField(score)] = null;
        for (const region of candidate.translation_regions || []) {
            region.quality_score = null;
            region.presentation_score = null;
            region.edits = [];
        }
    }
}


export function candidateContentMatches(candidate, expected) {
    if (!candidate || !expected || candidate.id !== expected.id || candidate.available !== expected.available
        || candidate.translated_image !== expected.translated_image
        || candidate.metadata?.translated_sha256 !== expected.metadata?.translated_sha256) return false;
    if (expected.translation_regions === null) return candidate.translation_regions === null;
    return Array.isArray(candidate.translation_regions) && Array.isArray(expected.translation_regions)
        && candidate.translation_regions.length === expected.translation_regions.length
        && candidate.translation_regions.every((region, i) => region.id === expected.translation_regions[i].id
            && region.target === expected.translation_regions[i].target);
}

export function comparisonContentMatches(hit, expected) {
    return Array.isArray(hit?.candidates) && Array.isArray(expected?.candidates)
        && hit.candidates.length === expected.candidates.length
        && hit.candidates.every((candidate, index) => candidateContentMatches(candidate, expected.candidates[index]));
}

export function restoreComparisonAnnotations(expected, saved, scores) {
    const result = JSON.parse(JSON.stringify(expected));
    for (const field of ['bookmark', 'comment']) {
        if (Object.hasOwn(saved, field)) result[field] = saved[field];
    }
    for (let i = 0; i < result.candidates.length; i++) {
        const candidate = result.candidates[i], imported = saved.candidates[i];
        for (const score of scores) candidate[scoreField(score)] = imported[scoreField(score)];
        for (let r = 0; r < (candidate.translation_regions || []).length; r++) {
            candidate.translation_regions[r].quality_score = imported.translation_regions[r].quality_score;
            candidate.translation_regions[r].presentation_score = imported.translation_regions[r].presentation_score;
            candidate.translation_regions[r].edits = JSON.parse(JSON.stringify(imported.translation_regions[r].edits || []));
        }
    }
    normalizeComparison(result, scores);
    return result;
}
