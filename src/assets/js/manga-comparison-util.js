import { isValidScore, scoreField } from './score-util.js';
import { isValidTranslationQuality, isRegionRated } from './manga-util.js';

export function comparisonRated(hit, scores) {
    return Array.isArray(hit?.candidates) && hit.candidates.length === 2 && scores.length > 0
        && hit.candidates.every(candidate => scores.every(score => isValidScore(candidate[scoreField(score)], score))
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
