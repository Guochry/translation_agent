export const TRANSLATION_QUALITY_SCORE = Object.freeze({
    name: 'quality_score',
    label: 'Region fidelity',
    question: 'How well does the translation preserve meaning, accuracy, style, and tone?',
    min: 0,
    max: 100,
    step: 5
})

export function isValidTranslationQuality(value) {
    return Number.isInteger(value) && value >= 0 && value <= 100 && value % 5 === 0
}

export const REGION_PRESENTATION_SCORE = Object.freeze({
    name: 'presentation_score', label: 'Region presentation',
    question: 'How readable and well fitted is this region in the rendered image?',
    min: 0, max: 100, step: 5
})

export function isRegionRated(region) {
    return isValidTranslationQuality(region.quality_score) && isValidTranslationQuality(region.presentation_score)
}
