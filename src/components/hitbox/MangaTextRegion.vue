<script setup>
import OverallScore from '../common/OverallScore.vue';
import { get_selection_offsets } from '../../assets/js/selection-util.js';
import { regionSpans, labelRegionSpan } from '../../assets/js/manga-span-util.js';
import { TRANSLATION_QUALITY_SCORE, REGION_PRESENTATION_SCORE } from '../../assets/js/manga-util.js';
</script>

<script>
export default {
    props: ['region', 'region_index', 'update_region', 'language', 'span_category'],
    data() { return { selection_message: '' } },
    computed: {
        target() { return typeof this.region.target === 'string' ? this.region.target : '' },
        spans() { return regionSpans(this.region) },
        annotations() {
            return (this.region.edits || []).filter(edit => this.spans.some(span => span.id === edit.id && span.category === edit.category))
        },
        segments() {
            const boundaries = [...new Set([0, this.target.length, ...this.spans.flatMap(span => [span.start, span.end])])].sort((a, b) => a - b)
            return boundaries.slice(0, -1).map((start, index) => {
                const end = boundaries[index + 1]
                const span = this.spans.find(span => span.start < end && span.end > start)
                return { start, text: this.target.slice(start, end), category: span?.category }
            })
        }
    },
    methods: {
        commit(region) { if (typeof this.update_region === 'function') this.update_region(this.region_index, region) },
        update_score_data(data) { this.commit(data[0]) },
        mark_selection(event) {
            if (event.button != null && event.button !== 0) return
            const selection = window.getSelection()
            if (!selection || selection.rangeCount !== 1) return
            const offsets = get_selection_offsets(event.currentTarget, selection.getRangeAt(0))
            if (!offsets) return
            this.selection_message = ''
            try { this.commit(labelRegionSpan(this.region, offsets[0], offsets[1], this.span_category || 'error')) }
            catch (error) { this.selection_message = error.message }
            selection.removeAllRanges()
        },
        remove_annotation(annotation) {
            this.commit({ ...this.region, edits: this.region.edits.filter(edit => !(edit.id === annotation.id && edit.category === annotation.category)) })
        },
        annotation_text(annotation) {
            return this.spans.filter(span => span.id === annotation.id && span.category === annotation.category)
                .map(span => this.target.slice(span.start, span.end)).join(' … ')
        }
    }
}

</script>

<template>
    <article class="manga-text-region" :aria-label="`Generated text region ${region_index + 1}`">
        <h4>Region {{ region_index + 1 }}</h4>
        <p v-if="region.render_status === 'skipped'" class="region-unavailable">Not rendered in the image.</p>
        <template v-if="(typeof region.source === 'string' && region.source.trim()) || region.source_alignment">
        <span class="region-text-label">Japanese source<span v-if="region.source_alignment === 'uncertain'" class="region-match-warning"> · Check match</span></span>
        <p v-if="region.source" class="region-source" lang="ja">{{ region.source }}</p>
        <p v-else class="region-unavailable">Source not matched</p>
        </template>
        <p v-if="target.length" class="region-target" :lang="language || 'en'" :dir="language === 'ar' ? 'rtl' : 'auto'" tabindex="0" aria-label="Generated translation text" @mouseup="mark_selection"><span v-for="segment in segments" :key="segment.start" :class="segment.category ? `region-${segment.category}-highlight` : null">{{ segment.text }}</span></p>
        <p v-else class="region-unavailable">No generated translation text for this region.</p>
        <p v-if="selection_message" class="region-unavailable" role="status">{{ selection_message }}</p>
        <div class="region-score-row">
            <OverallScore class="region-quality-score" :hits_data="[region]" :current_hit="1" :set_hits_data="update_score_data"
                :config="{}" :score_definition="TRANSLATION_QUALITY_SCORE" :compact="true" caption="Fidelity" />
            <OverallScore class="region-quality-score" :hits_data="[region]" :current_hit="1" :set_hits_data="update_score_data"
                :config="{}" :score_definition="REGION_PRESENTATION_SCORE" :compact="true" caption="Presentation" />
        </div>
        <div v-if="annotations.length" class="region-errors" aria-label="Marked translation spans">
            <ul>
                <li v-for="annotation in annotations" :key="`${annotation.category}-${annotation.id}`">
                    <span class="region-span-category" :class="`region-${annotation.category}-highlight`">{{ annotation.category }}</span>
                    <span class="region-error-text" :lang="language || 'en'" :dir="language === 'ar' ? 'rtl' : 'auto'">{{ annotation_text(annotation) }}</span>
                    <button type="button" @click="remove_annotation(annotation)" :aria-label="`Remove ${annotation.category} span ${annotation.id} from region ${region_index + 1}`">Remove</button>
                </li>
            </ul>
        </div>
    </article>
</template>

<style scoped>
.manga-text-region { min-width: 0; margin-top: 1rem; padding: 0.85rem; background: #fff; border: 1px solid #ccc; border-radius: 4px; }
.manga-text-region h4 { margin: 0 0 0.85rem; font-size: 1rem; }
.region-match-warning { color: #865400; }
.region-text-label { display: block; font-size: 0.8rem; font-weight: 600; color: #444; }
.region-source, .region-target { margin: 0.3rem 0 0.85rem; white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.5; }
.region-target { padding: 0.6rem; background: #f7f7f7; border: 1px solid #ddd; border-radius: 3px; cursor: text; }
.region-target:focus-visible { outline: 2px solid #245ba0; }
.region-strength-highlight { background: #d9f2df; border-bottom: 2px solid #27823e; }
.region-okay-highlight { background: #fff1bd; border-bottom: 2px solid #b28a15; }
.region-span-category { font-size: .7rem; padding: .15rem .25rem; text-transform: capitalize; flex-shrink: 0; }
.region-error-highlight { background: #ffe0df; border-bottom: 2px solid #c33; }
.region-unavailable { color: #666; font-style: italic; line-height: 1.4; margin: 0.3rem 0 0.85rem; }
.region-score-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; margin: .5rem 0; }
.region-quality-score { min-width: 0; flex: none; margin: 0; text-align: left; }
.region-quality-score :deep(.candidate-score-caption) { font-size: .8rem; font-weight: 600; color: #333; }
.region-quality-score :deep(.candidate-score-input) { padding: .4rem; }
.region-errors h5 { margin: 0.75rem 0 0.4rem; font-size: 0.85rem; }
.region-errors ul { list-style: none; padding: 0; margin: 0; }
.region-errors li { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.5rem; }
.region-error-text { white-space: pre-wrap; overflow-wrap: anywhere; min-width: 0; font-size: 0.85rem; line-height: 1.4; }
.region-errors button { flex-shrink: 0; border: 1px solid #aaa; background: #fff; border-radius: 3px; padding: 0.2rem 0.4rem; font-size: 0.75rem; cursor: pointer; }
</style>
