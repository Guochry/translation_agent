<script>
export default {
    props: [
        'hits_data',
        'current_hit',
        'set_hits_data',
        'config'
    ],
    computed: {
        score_config() {
            return typeof this.config.overall_score === 'object'
                ? this.config.overall_score
                : {}
        },
        field_name() {
            return this.score_config.name || this.score_config.field || 'overall_score'
        },
        minimum() {
            return this.score_config.min ?? 0
        },
        maximum() {
            return this.score_config.max ?? 100
        },
        step() {
            return this.score_config.step ?? 1
        },
        current_score() {
            const hit = this.hits_data && this.hits_data[this.current_hit - 1]
            const value = hit && hit[this.field_name]
            return value == null ? null : Number(value)
        },
        score_background() {
            if (this.current_score == null) return '#f2f2f2'
            const range = Number(this.maximum) - Number(this.minimum)
            const fraction = range > 0
                ? Math.min(1, Math.max(0, (this.current_score - Number(this.minimum)) / range))
                : 0
            return `hsl(${fraction * 120}, 75%, 85%)`
        }
    },
    methods: {
        update_score(event) {
            const input = event.target
            // Allow unfinished numeric input while typing; normalize on commit.
            if (event.type === 'input' && !input.validity.valid) return
            const value = input.value === '' ? null : Number(input.value)
            const score = value == null || !Number.isFinite(value)
                ? null
                : Math.min(Number(this.maximum), Math.max(Number(this.minimum),
                    Number(this.minimum) + Math.round((value - Number(this.minimum)) / Number(this.step)) * Number(this.step)))
            input.value = score == null ? '' : String(score)
            const new_hits_data = JSON.parse(JSON.stringify(this.hits_data))
            new_hits_data[this.current_hit - 1][this.field_name] = score
            this.set_hits_data(new_hits_data)
        }
    }
}
</script>

<template>
    <label class="candidate-score-box">
                <span class="candidate-score-caption">Score</span>
                <input
                    :key="current_hit"
                    class="candidate-score-input"
                    :style="{ backgroundColor: score_background }"
                    type="number"
                    :min="minimum"
                    :max="maximum"
                    :step="step"
                    :value="current_score ?? ''"
                    placeholder="—"
                    :aria-label="`${score_config.label || 'Overall Translation Score'} (${minimum}–${maximum})`"
                    :title="`Type a score from ${minimum} to ${maximum}; leave blank for not rated`"
                    @input="update_score"
                    @change="update_score"
                />
    </label>
</template>
