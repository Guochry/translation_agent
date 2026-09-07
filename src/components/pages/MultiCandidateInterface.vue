<script setup>
import Interface from "./Interface.vue";
</script>

<script>
export default {
    props: [
        'input_data',
        'consumed_config'
    ],
    data() {
        return {
            grouped_data: [],
            candidate_datasets: [],
            candidate_results: [],
            current_hit: 1,
            data_version: 0,
            data_error: null,
            timer_last: null,
            timer_interval: null,
            timer_mounted: false,
            timer_visible: true,
            timer_paused: false,
        }
    },
    computed: {
        task_config() {
            return this.consumed_config?.consumed_config
                || this.consumed_config?.config
                || this.consumed_config
                || {}
        },
        current_example() {
            return this.grouped_data[this.current_hit - 1]
        },
        total_time_ms() {
            return this.grouped_data.reduce((sum, example) => sum + this.elapsed_ms(example), 0)
        }
    },
    watch: {
        input_data() {
            this.consume_data()
        }
    },
    methods: {
        elapsed_ms(example) {
            const value = example?.annotation_time_ms
            return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0
        },
        format_time(ms) {
            const seconds = Math.floor(ms / 1000)
            const hours = Math.floor(seconds / 3600)
            return `${hours ? `${hours}:` : ''}${String(Math.floor(seconds / 60) % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
        },
        tick_timer() {
            const now = performance.now()
            const example = this.grouped_data[this.current_hit - 1]
            if (this.timer_last !== null && example) {
                example.annotation_time_ms = this.elapsed_ms(example) + Math.max(0, Math.round(now - this.timer_last))
            }
            this.timer_last = this.timer_mounted && this.timer_visible && !this.timer_paused && example ? now : null
        },
        handle_visibility() {
            this.tick_timer()
            this.timer_visible = !document.hidden
            this.tick_timer()
        },
        toggle_timer() {
            this.tick_timer()
            this.timer_paused = !this.timer_paused
            this.tick_timer()
        },
        clone_data(data) {
            return JSON.parse(JSON.stringify(data))
        },
        consume_data(data_override=null) {
            const input = data_override || (this.input_data && this.input_data.data)
            if (!Array.isArray(input)) { return }

            this.tick_timer()
            this.timer_last = null
            const data = this.clone_data(input)
            if (!data.length || data.some(example => !Array.isArray(example.candidates) || !example.candidates.length)) {
                this.data_error = 'Multi-candidate data must provide a non-empty candidates array for every example.'
                this.grouped_data = []
                this.candidate_datasets = []
                this.candidate_results = []
                return
            }

            const candidate_count = Math.max(...data.map(example => example.candidates.length))

            this.data_error = null
            this.grouped_data = data
            this.candidate_datasets = Array.from({ length: candidate_count }, (_, candidate_idx) => ({
                data: data.map((example, example_idx) => {
                    const candidate = example.candidates[candidate_idx]
                    return candidate
                        ? this.clone_data(candidate)
                        : {
                            id: `__missing_candidate_${example_idx + 1}_${candidate_idx + 1}`,
                            source: '',
                            target: '',
                            edits: []
                        }
                })
            }))
            this.candidate_results = this.candidate_datasets.map(dataset => this.clone_data(dataset.data))
            this.current_hit = 1
            this.data_version += 1
            this.tick_timer()
        },
        set_synchronized_hit(hit_num) {
            const bounded_hit = Math.min(Math.max(hit_num, 1), this.grouped_data.length)
            this.tick_timer()
            this.current_hit = bounded_hit
            this.timer_last = null
            this.tick_timer()
        },
        update_candidate_data(candidate_idx, hits_data) {
            this.candidate_results[candidate_idx] = this.clone_data(hits_data)
        },
        candidate_label(candidate_idx) {
            return `Candidate ${candidate_idx + 1}`
        },
        candidate_exists(candidate_idx) {
            const example = this.grouped_data[this.current_hit - 1]
            return Boolean(example && example.candidates[candidate_idx])
        },
        get_export_data() {
            this.tick_timer()
            return this.grouped_data.map((example, example_idx) => {
                const exported_example = this.clone_data(example)
                exported_example.annotation_time_ms = this.elapsed_ms(example)
                exported_example.candidates = example.candidates.map((candidate, candidate_idx) => {
                    const result = this.candidate_results[candidate_idx]
                        && this.candidate_results[candidate_idx][example_idx]
                    const exported_candidate = this.clone_data(result || candidate)
                    delete exported_candidate._thresh_id
                    exported_candidate.edits = exported_candidate.edits || []
                    return exported_candidate
                })
                return exported_example
            })
        },
        handle_uploaded_data(data) {
            this.consume_data(data)
        }
    },
    created() {
        this.consume_data()
    },
    mounted() {
        this.timer_mounted = true
        this.timer_visible = !document.hidden
        this.tick_timer()
        this.timer_interval = window.setInterval(this.tick_timer, 1000)
        document.addEventListener('visibilitychange', this.handle_visibility)
    },
    beforeUnmount() {
        this.tick_timer()
        window.clearInterval(this.timer_interval)
        document.removeEventListener('visibilitychange', this.handle_visibility)
        this.timer_mounted = false
        this.timer_last = null
    }
}
</script>

<template>
    <div v-if="data_error" class="multi-candidate-error ba b--red dark-red pa3 br2">
        {{ data_error }}
    </div>
    <div v-else class="multi-candidate-container">
        <div v-if="current_example" class="annotation-timer card-body w-65" aria-label="Annotation time">
            <span>This example: <strong>{{ format_time(elapsed_ms(current_example)) }}</strong></span>
            <span>Total: <strong>{{ format_time(total_time_ms) }}</strong></span>
            <span v-if="timer_paused || !timer_visible">Paused</span>
            <button type="button" @click="toggle_timer" :aria-pressed="timer_paused">{{ timer_paused ? 'Resume timer' : 'Pause timer' }}</button>
        </div>
        <Interface
            v-for="(candidate_dataset, candidate_idx) in candidate_datasets"
            v-show="candidate_exists(candidate_idx)"
            :key="`${data_version}-${candidate_idx}`"
            class="multi-candidate-interface"
            :input_data="candidate_dataset"
            :consumed_config="consumed_config"
            :candidate_label="candidate_label(candidate_idx)"
            :show_instructions="candidate_idx === 0"
            :show_hit_header="candidate_idx === 0"
            :synchronized_hit="current_hit"
            :set_synchronized_hit="set_synchronized_hit"
            :on_hits_data_change="hits_data => update_candidate_data(candidate_idx, hits_data)"
            :get_export_data="get_export_data"
            :handle_uploaded_data="handle_uploaded_data"
        />
        <section
            v-if="task_config.enable_translation_synthesis && current_example"
            class="translation-synthesis container card-body w-65"
        >
            <label class="translation-synthesis-label">
                <span class="candidate-heading">Combine strengths into a better translation <span class="translation-synthesis-optional">(optional)</span></span>
                <span class="translation-synthesis-help">Start from the best provided translation and incorporate complementary strength spans you annotated in other candidates. Write a revision only if it improves that translation while preserving the source meaning; otherwise, leave this blank.</span>
                <textarea
                    :key="`${data_version}-${current_hit}`"
                    v-model="current_example.improved_translation"
                    class="translation-synthesis-input"
                    rows="3"
                    placeholder="Write your improved translation here…"
                ></textarea>
            </label>
        </section>
    </div>
</template>
