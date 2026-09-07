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
        }
    },
    watch: {
        input_data() {
            this.consume_data()
        }
    },
    methods: {
        clone_data(data) {
            return JSON.parse(JSON.stringify(data))
        },
        consume_data(data_override=null) {
            const input = data_override || (this.input_data && this.input_data.data)
            if (!Array.isArray(input)) { return }

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
        },
        set_synchronized_hit(hit_num) {
            const bounded_hit = Math.min(Math.max(hit_num, 1), this.grouped_data.length)
            this.current_hit = bounded_hit
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
            return this.grouped_data.map((example, example_idx) => {
                const exported_example = this.clone_data(example)
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
    }
}
</script>

<template>
    <div v-if="data_error" class="multi-candidate-error ba b--red dark-red pa3 br2">
        {{ data_error }}
    </div>
    <div v-else class="multi-candidate-container">
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
