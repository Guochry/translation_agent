export function scoreConfigs(config = {}) {
    if (Array.isArray(config.scores)) return config.scores
    if (!config.overall_score) return []
    return [typeof config.overall_score === 'object' ? config.overall_score : {}]
}

export function scoreField(config) {
    return config.name || config.field || 'overall_score'
}

export function isValidScore(value, config) {
    if (typeof value !== 'number' || !Number.isFinite(value)) return false
    const minimum = Number(config.min ?? 0)
    const maximum = Number(config.max ?? 100)
    const step = Number(config.step ?? 1)
    return value >= minimum && value <= maximum && step > 0
        && Math.abs((value - minimum) / step - Math.round((value - minimum) / step)) < 1e-8
}
