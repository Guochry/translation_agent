export const TRANSLATION_QUALITY_SCORE = Object.freeze({
    name: 'quality_score',
    label: 'Translation quality',
    question: 'How accurate and natural is this generated translation?',
    min: 0,
    max: 100,
    step: 5
})

export function isValidTranslationQuality(value) {
    return Number.isInteger(value) && value >= 0 && value <= 100 && value % 5 === 0
}
