<script setup>
import MangaReferenceText from './MangaReferenceText.vue';
import MangaCandidateTabs from './MangaCandidateTabs.vue';
import { mangaImageUrl } from '../../assets/js/manga-multilingual-util.js';
import MangaSpanLegend from './MangaSpanLegend.vue';
import OverallScore from '../common/OverallScore.vue';
import MangaTextRegion from './MangaTextRegion.vue';
</script>
<script>
export default {
    props: ['hit', 'scores', 'update_candidate', 'config'],
    data() {
        return { reference_percent: 30, reference_resize_start: null, span_category: 'error', active: 0, image_errors: {}, uid: this.$.uid }
    },
    computed: {
        candidates() { return this.hit.candidates || [] },
        many_candidates() { return this.candidates.length > 2 },
        panels() {
            const visible = this.candidates.map((candidate, index) => ({ label: this.label(index), image: candidate.translated_image, candidate, index }))
                .filter(panel => !this.many_candidates || panel.index === this.active)
            return [{ label: 'Original Japanese', image: this.hit.original_image },
                ...visible]
        },
        active_candidate() { return this.candidates[this.active] }
    },
    watch: { active() { this.image_errors = {} } },
    methods: {
        set_reference_size(value) { this.reference_percent = Math.min(50, Math.max(20, Math.round(value))) },
        start_reference_resize(event) {
            if (event.button !== 0) return
            event.preventDefault()
            this.reference_resize_start = { y: event.clientY, value: this.reference_percent }
            event.currentTarget.setPointerCapture(event.pointerId)
        },
        resize_reference(event) {
            if (!this.reference_resize_start) return
            const height = this.$refs.text_panel?.clientHeight
            if (height) this.set_reference_size(this.reference_resize_start.value + (event.clientY - this.reference_resize_start.y) / height * 100)
        },
        stop_reference_resize() { this.reference_resize_start = null },
        label(index) { return `Translation ${String.fromCharCode(65 + index)}` },
        image_url(path) {
            return mangaImageUrl(path, { baseUrl: import.meta.env.BASE_URL,
                externalPrefix: this.config?.external_asset_prefix, externalBase: this.config?.external_asset_base,
                useExternal: import.meta.env.PROD })
        },
        update_score(index, data) { this.update_candidate(index, data[0]) },
        update_region(index, region) {
            const candidate = JSON.parse(JSON.stringify(this.active_candidate))
            if (candidate.translation_regions[index]?.id !== region.id) return
            candidate.translation_regions[index] = region
            this.update_candidate(this.active, candidate)
        }
    }
}
</script>
<template>
    <section class="manga-pair" aria-label="Manga translation comparison">
        <header class="pair-heading">
            <h2>{{ hit.metadata?.book_title || 'Manga comparison' }}</h2>
            <span>Page {{ hit.metadata?.page_index }}</span>
        </header>
        <MangaCandidateTabs v-if="many_candidates" :candidates="candidates" :active="active" :uid="uid" @select="active = $event" />
        <div class="pair-workspace" :class="{ 'many-candidates': many_candidates }">
            <details v-if="!many_candidates" class="pair-references" :open="!config?.manga_multilingual">
                <summary>Human reference text</summary>
                <ol v-if="hit.reference_texts?.length">
                    <li v-for="(text, index) in hit.reference_texts" :key="index">
                        <p lang="ja">{{ hit.reference_texts_ja?.[index] || 'Japanese text unavailable' }}</p>
                        <p lang="en">{{ text }}</p>
                    </li>
                </ol>
                <p v-else>No reference text for this page.</p>
            </details>
        <div class="pair-images">
            <figure v-for="panel in panels" :key="panel.candidate?.id || 'original'">
                <figcaption><h3>{{ panel.label }}</h3>
                    <a v-if="image_url(panel.image)" :href="image_url(panel.image)" target="_blank" rel="noopener noreferrer">Open full-size image</a>
                </figcaption>
                <a v-if="image_url(panel.image) && !image_errors[panel.image]" :href="image_url(panel.image)" target="_blank" rel="noopener noreferrer">
                    <img :src="image_url(panel.image)" :alt="`${panel.label}, page ${hit.metadata?.page_index}`" @error="image_errors[panel.image] = true" />
                </a>
                <p v-else-if="panel.candidate?.available === false" role="status">This translation is unavailable for this page.</p>
                <p v-else role="status">Image unavailable. Try opening the full-size image.</p>
                <div v-if="panel.candidate && panel.candidate.available !== false" class="pair-scores" :aria-label="`${panel.label} page ratings`">
                    <OverallScore v-for="score in scores" :key="score.name" :hits_data="[panel.candidate]" :current_hit="1"
                        :set_hits_data="data => update_score(panel.index, data)" :config="{}" :score_definition="score" :caption="score.label" />
                </div>
            </figure>
        </div>

            <aside ref="text_panel" class="pair-text" :class="{ 'parallel-text': many_candidates }" aria-label="Reference text and translation assessment">
                <div v-if="many_candidates" class="reference-pane" :style="{ height: `${reference_percent}%` }">
                    <MangaReferenceText :references="hit.reference_texts" :japanese="hit.reference_texts_ja" />
                </div>
                <div v-if="many_candidates" class="reference-resizer" role="separator" aria-orientation="horizontal"
                    tabindex="0" aria-label="Resize reference section" aria-valuemin="20" aria-valuemax="50" :aria-valuenow="reference_percent"
                    :aria-valuetext="`${reference_percent}% reference area`" title="Drag or use the up/down arrow keys to resize references"
                    @pointerdown="start_reference_resize" @pointermove="resize_reference" @pointerup="stop_reference_resize"
                    @pointercancel="stop_reference_resize" @lostpointercapture="stop_reference_resize"
                    @keydown.up.prevent="set_reference_size(reference_percent - 5)" @keydown.down.prevent="set_reference_size(reference_percent + 5)"
                    @keydown.home.prevent="set_reference_size(20)" @keydown.end.prevent="set_reference_size(50)"></div>
                <div class="assessment-pane">
                <MangaCandidateTabs v-if="!many_candidates" :candidates="candidates" :active="active" :uid="uid" @select="active = $event" />
                <div v-if="active_candidate" :key="active_candidate.id" role="tabpanel" :id="`pair-text-${uid}`" :aria-labelledby="`pair-tab-${uid}-${active}`">
                    <h3>{{ label(active) }} — region assessment</h3>
                    <p>Rate translation fidelity and visual presentation: <strong>0–100, steps of 5</strong>.</p>
                    <p v-if="active_candidate.available === false" role="status">This translation is unavailable for this page.</p>
                    <p v-else-if="active_candidate.translation_regions === null" role="status">Translation text is unavailable for this page.</p>
                    <template v-else>
                    <MangaSpanLegend v-model="span_category" />
                    <p v-if="!active_candidate.translation_regions?.length">No translation text for this page.</p>
                    <MangaTextRegion v-for="(region, index) in active_candidate.translation_regions || []" :key="region.id"
                        :region="region" :region_index="index" :span_category="span_category" :language="hit.language" :update_region="update_region" />
                    </template>
                </div>
                </div>
            </aside>
        </div>
    </section>
</template>
<style scoped>
.pair-heading { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 1rem; }
.pair-heading h2 { margin: 0; font-size: 1.3rem; }
.pair-workspace { display: grid; grid-template-columns: minmax(240px, 1fr) minmax(0, 2fr); gap: 1rem; align-items: start; }
.pair-images { grid-column: 1 / -1; grid-row: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; align-items: start; }
figure { margin: 0; min-width: 0; }
figcaption { margin-bottom: .75rem; }
h3 { font-size: 1.1rem; margin: 0 0 .5rem; }
a { color: #245ba0; }
img { box-sizing: border-box; display: block; width: 100%; height: auto; border: 1px solid #ddd; }
.pair-scores { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem; margin: .75rem 0; }
.pair-scores :deep(.candidate-score-box) { width: auto; min-width: 0; margin: 0; }
.pair-scores :deep(.score-question) { font-size: .8rem; }
.pair-references { grid-column: 1; grid-row: 2; }
.pair-text { grid-column: 2; grid-row: 2; }
.pair-references, .pair-text { min-width: 0; box-sizing: border-box; border: 1px solid #ddd; padding: 1rem; border-radius: 4px; max-height: 80vh; overflow: auto; background: #fafafa; }
.parallel-text { display: flex; flex-direction: column; height: 80vh; min-height: 480px; max-height: 900px; padding: 0; overflow: hidden; }
.reference-pane { flex: 0 0 auto; min-height: 0; overflow-y: auto; box-sizing: border-box; padding: 1rem; }
.parallel-text .assessment-pane { flex: 1 1 0; min-height: 0; overflow-y: auto; padding: 1rem; }
.reference-resizer { flex: 0 0 12px; display: flex; justify-content: center; align-items: center; cursor: row-resize; touch-action: none; background: #edf1f6; border-top: 1px solid #d6dfe9; border-bottom: 1px solid #d6dfe9; }
.reference-resizer::before { content: ''; width: 40px; height: 3px; border-radius: 4px; background: #8297af; }
.reference-resizer:hover, .reference-resizer:focus-visible { background: #dce8f7; outline: 2px solid #245ba0; outline-offset: -2px; }
summary { cursor: pointer; font-weight: 600; }
li { border-bottom: 1px solid #ddd; padding: .5rem 0; }
li p { white-space: pre-wrap; overflow-wrap: anywhere; margin: .4rem 0; }
.pair-workspace.many-candidates { grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr); }
.many-candidates .pair-images { grid-column: 1; grid-row: 1; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.many-candidates .pair-text { grid-column: 2; grid-row: 1; }
@media (max-width: 1100px) {
    .pair-workspace.many-candidates { grid-template-columns: minmax(0, 1fr); }
    .many-candidates .pair-references, .many-candidates .pair-images, .many-candidates .pair-text { grid-column: 1; grid-row: auto; }
}
@media (max-width: 900px) {
    .pair-workspace { grid-template-columns: minmax(0, 1fr); }
    .pair-references, .pair-images, .pair-text { grid-column: 1; grid-row: auto; }
    .pair-scores { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 650px) { .pair-images, .many-candidates .pair-images { grid-template-columns: minmax(0, 1fr); } }
</style>
