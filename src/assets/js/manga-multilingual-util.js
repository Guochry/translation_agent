import { comparisonRated, normalizeComparison, comparisonContentMatches } from './manga-comparison-util.js';
import { isValidScore, scoreConfigs, scoreField } from './score-util.js';
import { isValidTranslationQuality, isRegionRated } from './manga-util.js';

export function multilingualPageRated(hit, config) {
    const scores = scoreConfigs(config);
    if (Array.isArray(hit.candidates)) return comparisonRated(hit, scores);
    return scores.length > 0 && scores.every(score => isValidScore(hit[scoreField(score)], score))
        && Array.isArray(hit.translation_regions)
        && hit.translation_regions.every(region => isRegionRated(region));
}

export function normalizeMultilingualScores(hit, config) {
    if (Array.isArray(hit.candidates)) { normalizeComparison(hit, scoreConfigs(config)); return hit; }
    for (const score of scoreConfigs(config)) {
        const field = scoreField(score);
        if (!isValidScore(hit[field], score)) hit[field] = null;
    }
    for (const region of hit.translation_regions || []) {
        if (!isValidTranslationQuality(region.quality_score)) region.quality_score = null;
        if (!isValidTranslationQuality(region.presentation_score)) region.presentation_score = null;
        region.edits = region.edits || [];
    }
    return hit;
}

export function validateMultilingualData(data, canonical, languages) {
    if (!Array.isArray(data) || !data.length) throw new Error('Upload a JSON export from this multilingual task.');
    const known = new Map(canonical.map(hit => [hit.id, hit]));
    const seen = new Set();
    for (const hit of data) {
        const original = known.get(hit?.id);
        if (!original || seen.has(hit.id) || !languages.includes(hit.language)
            || hit.language !== original.language || hit.page_key !== original.page_key
            || hit.original_image !== original.original_image || hit.translated_image !== original.translated_image
            || hit.metadata?.original_sha256 !== original.metadata?.original_sha256
            || hit.metadata?.translated_sha256 !== original.metadata?.translated_sha256) {
            throw new Error('This file contains duplicate pages or pages from another task or language.');
        }
        seen.add(hit.id);
        if (Array.isArray(original.candidates)) {
            if (!comparisonContentMatches(hit, original)) throw new Error('This file contains different translation candidates or text.');
            continue;
        }
        if (Array.isArray(hit.candidates)) throw new Error('This file belongs to a comparison task.');
        if (original.translation_regions === null) {
            if (hit.translation_regions !== null) throw new Error('This file changes unavailable translation text.');
        } else if (!Array.isArray(hit.translation_regions)
            || hit.translation_regions.length !== original.translation_regions.length
            || hit.translation_regions.some((region, index) => region.id !== original.translation_regions[index].id
                || region.target !== original.translation_regions[index].target)) {
            throw new Error('This file contains translation text that differs from this task.');
        }
    }
    return true;
}

export function mangaImageUrl(path, { baseUrl = '/', externalPrefix, externalBase, useExternal = false } = {}) {
    if (typeof path !== 'string' || !path.trim()) return null;
    if (/^(https?:)?\/\//i.test(path)) return path;
    if (/^[a-z][a-z\d+.-]*:/i.test(path)) return null;
    const relative = path.replace(/^\/+/, '');
    if (useExternal && externalPrefix && externalBase && relative.startsWith(externalPrefix)) {
        return `${externalBase.replace(/\/$/, '')}/${relative.slice(externalPrefix.length)}`;
    }
    return `${baseUrl}${relative}`;
}
