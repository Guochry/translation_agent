<script setup>
import MangaSpanLegend from './MangaSpanLegend.vue';
import OverallScore from '../common/OverallScore.vue';
import { isRegionRated } from '../../assets/js/manga-util.js';
import MangaTextRegion from './MangaTextRegion.vue';
</script>
<script>
export default {
    props: ['hit', 'scores', 'update_candidate'],
    data() {
        return { span_category: 'error', active: 0, image_errors: {}, uid: this.$.uid }
    },
    computed: {
        candidates() { return this.hit.candidates || [] },
        panels() {
            return [{ label: 'Original Japanese', image: this.hit.original_image },
                ...this.candidates.map((candidate, index) => ({ label: this.label(index), image: candidate.translated_image, candidate, index }))]
        },
        active_candidate() { return this.candidates[this.active] }
    },
    methods: {
        label(index) { return `Translation ${String.fromCharCode(65 + index)}` },
        image_url(path) {
            if (typeof path !== 'string' || !path.trim()) return null
            if (/^(https?:)?\/\//i.test(path)) return path
            if (/^[a-z][a-z\d+.-]*:/i.test(path)) return null
            return `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`
        },
        update_score(index, data) { this.update_candidate(index, data[0]) },
        update_region(index, region) {
            const candidate = JSON.parse(JSON.stringify(this.active_candidate))
            if (candidate.translation_regions[index]?.id !== region.id) return
            candidate.translation_regions[index] = region
            this.update_candidate(this.active, candidate)
        },
        rated_count(candidate) {
            return (candidate.translation_regions || []).filter(region => isRegionRated(region)).length
        }
    }
}
</script>
<template>
    <section class="manga-pair" aria-label="Two-translation manga comparison">
        <header class="pair-heading">
            <h2>{{ hit.metadata?.book_title || 'Manga comparison' }}</h2>
            <span>Page {{ hit.metadata?.page_index }}</span>
        </header>
        <div class="pair-images">
            <figure v-for="(panel, index) in panels" :key="index">
                <figcaption><h3>{{ panel.label }}</h3>
                    <a v-if="image_url(panel.image)" :href="image_url(panel.image)" target="_blank" rel="noopener noreferrer">Open full-size image</a>
                </figcaption>
                <a v-if="image_url(panel.image) && !image_errors[index]" :href="image_url(panel.image)" target="_blank" rel="noopener noreferrer">
                    <img :src="image_url(panel.image)" :alt="`${panel.label}, page ${hit.metadata?.page_index}`" @error="image_errors[index] = true" />
                </a>
                <p v-else role="status">Image unavailable. Try opening the full-size image.</p>
                <div v-if="panel.candidate" class="pair-scores" :aria-label="`${panel.label} page ratings`">
                    <OverallScore v-for="score in scores" :key="score.name" :hits_data="[panel.candidate]" :current_hit="1"
                        :set_hits_data="data => update_score(panel.index, data)" :config="{}" :score_definition="score" :caption="score.label" />
                </div>
            </figure>
        </div>
        <div class="pair-text-layout">
            <details class="pair-references" open>
                <summary>Human reference text</summary>
                <ol v-if="hit.reference_texts?.length">
                    <li v-for="(text, index) in hit.reference_texts" :key="index">
                        <p lang="ja">{{ hit.reference_texts_ja?.[index] || 'Japanese text unavailable' }}</p>
                        <p lang="en">{{ text }}</p>
                    </li>
                </ol>
                <p v-else>No reference text for this page.</p>
            </details>
            <aside class="pair-text" aria-label="Translation text assessment">
                <div class="pair-tabs" role="tablist" aria-label="Translation text">
                    <button v-for="(candidate, index) in candidates" :key="candidate.id" type="button" role="tab"
                        :id="`pair-tab-${uid}-${index}`" :aria-selected="active === index" :aria-controls="`pair-text-${uid}`"
                        @click="active = index" @keydown.right.prevent="active = (active + 1) % candidates.length; $event.currentTarget.parentElement.children[active].focus()"
                        @keydown.left.prevent="active = (active + candidates.length - 1) % candidates.length; $event.currentTarget.parentElement.children[active].focus()">
                        {{ label(index) }} · {{ rated_count(candidate) }}/{{ candidate.translation_regions?.length || 0 }} rated
                    </button>
                </div>
                <div v-if="active_candidate" :key="active_candidate.id" role="tabpanel" :id="`pair-text-${uid}`" :aria-labelledby="`pair-tab-${uid}-${active}`">
                    <h3>{{ label(active) }} — region assessment</h3>
                    <p>Rate translation fidelity and visual presentation: <strong>0–100, steps of 5</strong>.</p>
                    <MangaSpanLegend v-model="span_category" />
                    <p v-if="!active_candidate.translation_regions?.length">No translation text for this page.</p>
                    <MangaTextRegion v-for="(region, index) in active_candidate.translation_regions || []" :key="region.id"
                        :region="region" :region_index="index" :span_category="span_category" :update_region="update_region" />
                </div>
            </aside>
        </div>
    </section>
</template>
<style scoped>
.pair-heading { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 1rem; }
.pair-heading h2 { margin: 0; font-size: 1.3rem; }
.pair-images { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; align-items: start; }
figure { margin: 0; min-width: 0; }
figcaption { margin-bottom: .75rem; }
h3 { font-size: 1.1rem; margin: 0 0 .5rem; }
a { color: #245ba0; }
img { box-sizing: border-box; display: block; width: 100%; height: auto; border: 1px solid #ddd; }
.pair-scores { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem; margin: .75rem 0; }
.pair-scores :deep(.candidate-score-box) { width: auto; min-width: 0; margin: 0; }
.pair-scores :deep(.score-question) { font-size: .8rem; }
.pair-text-layout { display: grid; grid-template-columns: minmax(240px, 1fr) minmax(0, 2fr); gap: 1rem; margin-top: 1.5rem; align-items: start; }
.pair-references, .pair-text { border: 1px solid #ddd; padding: 1rem; border-radius: 4px; max-height: 80vh; overflow: auto; background: #fafafa; }
summary { cursor: pointer; font-weight: 600; }
li { border-bottom: 1px solid #ddd; padding: .5rem 0; }
li p { white-space: pre-wrap; overflow-wrap: anywhere; margin: .4rem 0; }
.pair-tabs { display: flex; gap: .5rem; margin-bottom: 1rem; }
.pair-tabs button { flex: 1; cursor: pointer; padding: .65rem; border: 1px solid #aaa; border-radius: 4px; background: white; }
.pair-tabs [aria-selected=true] { background: #e8f0fb; border-color: #245ba0; font-weight: 600; }
@media (max-width: 900px) { .pair-text-layout { grid-template-columns: minmax(0, 1fr); } .pair-scores { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 650px) { .pair-images { grid-template-columns: minmax(0, 1fr); } }
</style>
