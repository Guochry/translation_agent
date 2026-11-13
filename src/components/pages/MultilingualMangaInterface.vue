<script setup>
import Interface from './Interface.vue';
import { multilingualPageRated, validateMultilingualData, normalizeMultilingualScores } from '../../assets/js/manga-multilingual-util.js';
</script>
<script>
export default {
    props: ['input_data', 'consumed_config'],
    data() {
        return { results: {}, canonical: [], active_language: null, active_input: null,
            current_hit: 1, version: 0, data_error: null, upload_error: null }
    },
    computed: {
        config() { return this.consumed_config?.consumed_config || this.consumed_config?.config || this.consumed_config || {} },
        languages() { return this.config.languages || [] }
    },
    watch: { input_data() { this.consume_data() } },
    methods: {
        clone(value) { return JSON.parse(JSON.stringify(value)) },
        consume_data() {
            try {
                const data = this.input_data?.data;
                validateMultilingualData(data, data || [], this.languages.map(language => language.code));
                this.canonical = this.clone(data);
                this.results = Object.fromEntries(this.languages.map(language => [language.code,
                    this.clone(data.filter(hit => hit.language === language.code)).map(hit => normalizeMultilingualScores(hit, this.config))]));
                if (this.languages.some(language => !this.results[language.code].length)) throw new Error('A configured language has no pages.');
                this.data_error = null;
                this.active_language = null;
                this.select_language(this.config.default_language || this.languages[0].code);
            } catch (error) { this.data_error = error.message }
        },
        select_language(code) {
            if (code === this.active_language || !this.results[code]) return;
            this.active_language = code;
            this.current_hit = Math.min(this.current_hit, this.results[code].length);
            this.active_input = { data: this.clone(this.results[code]) };
            this.version += 1;
        },
        update_results(data) { this.results[this.active_language] = this.clone(data) },
        set_hit(number) { this.current_hit = Math.max(1, Math.min(number, this.results[this.active_language].length)) },
        rated(code) { return (this.results[code] || []).filter(hit => multilingualPageRated(hit, this.config)).length },
        export_data() {
            return this.languages.flatMap(language => this.clone(this.results[language.code] || [])).map(hit => {
                delete hit._thresh_id;
                return hit;
            });
        },
        import_data(data) {
            try {
                validateMultilingualData(data, this.canonical, this.languages.map(language => language.code));
                // Import annotations onto canonical content; partial-language exports merge safely.
                const imported = new Map(data.map(hit => [hit.id, hit]));
                for (const language of this.languages) {
                    this.results[language.code] = this.results[language.code].map(current => {
                        const saved = imported.get(current.id);
                        if (!saved) return current;
                        const result = this.clone(this.canonical.find(hit => hit.id === saved.id));
                        for (const field of ['fidelity_score', 'presentation_score', 'bookmark', 'comment']) {
                            if (Object.hasOwn(saved, field)) result[field] = this.clone(saved[field]);
                        }
                        for (let i = 0; i < (result.translation_regions || []).length; i++) {
                            result.translation_regions[i].quality_score = saved.translation_regions[i].quality_score;
                            result.translation_regions[i].presentation_score = saved.translation_regions[i].presentation_score;
                            result.translation_regions[i].edits = this.clone(saved.translation_regions[i].edits || []);
                        }
                        return normalizeMultilingualScores(result, this.config);
                    });
                }
                const code = data.some(hit => hit.language === this.active_language) ? this.active_language : data[0].language;
                this.active_language = null;
                this.current_hit = 1;
                this.select_language(code);
                this.upload_error = null;
            } catch (error) { this.upload_error = error.message }
        }
    },
    created() { this.consume_data() }
}
</script>
<template>
    <div v-if="data_error" role="alert" class="multilingual-error">{{ data_error }}</div>
    <div v-else class="multilingual-manga">
        <section class="language-selector container card-body" aria-label="Translation language">
            <h2>Translation language</h2>
            <p>Choose your native language.</p>
            <div class="language-buttons">
                <button v-for="language in languages" :key="language.code" type="button" :aria-pressed="active_language === language.code"
                    @click="select_language(language.code)">
                    <span :lang="language.code" :dir="language.code === 'ar' ? 'rtl' : 'auto'">{{ language.native_label || language.label }}</span>
                    <span>{{ language.label }} · {{ rated(language.code) }}/{{ results[language.code]?.length || 0 }} rated</span>
                </button>
            </div>
            <p v-if="upload_error" role="alert">{{ upload_error }}</p>
        </section>
        <Interface v-if="active_input" :key="version" :input_data="active_input" :consumed_config="consumed_config"
            :synchronized_hit="current_hit" :set_synchronized_hit="set_hit" :on_hits_data_change="update_results"
            :get_export_data="export_data" :handle_uploaded_data="import_data" />
    </div>
</template>
<style scoped>
@font-face { font-family: EvaluationCJK; src: url('/fonts/manga/NotoSansCJKjp-Regular.otf') format('opentype'); font-display: swap; }
@font-face { font-family: EvaluationHindi; src: url('/fonts/manga/NotoSansDevanagari.ttf') format('truetype'); font-weight: 100 900; font-display: swap; }
.multilingual-manga :deep([lang="ja"]), .multilingual-manga :deep([lang="zh"]) { font-family: EvaluationCJK, sans-serif; }
.multilingual-manga :deep([lang="hi"]) { font-family: EvaluationHindi, sans-serif; }
.language-selector { width: 100%; max-width: 1600px; box-sizing: border-box; }
h2 { margin: 0 0 .5rem; font-size: 1.2rem; }
p { line-height: 1.4; }
.language-buttons { display: flex; flex-wrap: wrap; gap: .5rem; }
.language-buttons button { display: flex; flex-direction: column; gap: .25rem; background: white; border: 1px solid #aaa; border-radius: 4px; cursor: pointer; padding: .6rem .85rem; }
.language-buttons button span:last-child { font-size: .8rem; color: #444; }
.language-buttons [aria-pressed=true] { background: #e8f0fb; border-color: #245ba0; font-weight: 600; }
.multilingual-error { padding: 1rem; color: #8b1111; }
</style>
