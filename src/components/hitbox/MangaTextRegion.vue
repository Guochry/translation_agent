<script setup>
import OverallScore from '../common/OverallScore.vue';
import { get_selection_offsets } from '../../assets/js/selection-util.js';
import { TRANSLATION_QUALITY_SCORE } from '../../assets/js/manga-util.js';
</script>

<script>
export default {
    props: ['region', 'region_index', 'update_region', 'language'],
    computed: {
        target() {
            return typeof this.region.target === 'string' ? this.region.target : ''
        },
        edits() {
            return Array.isArray(this.region.edits) ? this.region.edits : []
        },
        error_spans() {
            return this.edits.filter(edit => edit.category === 'error').flatMap(edit =>
                (Array.isArray(edit.output_idx) ? edit.output_idx : [])
                    .filter(span => Array.isArray(span) && span.length === 2
                        && Number.isInteger(span[0]) && Number.isInteger(span[1])
                        && span[0] >= 0 && span[1] > span[0] && span[1] <= this.target.length)
                    .map(([start, end]) => ({ start, end, id: edit.id }))
            )
        },
        errors() {
            return this.edits.filter(edit => edit.category === 'error'
                && this.error_spans.some(span => span.id === edit.id))
        },
        segments() {
            const boundaries = [...new Set([0, this.target.length,
                ...this.error_spans.flatMap(span => [span.start, span.end])])].sort((a, b) => a - b)
            return boundaries.slice(0, -1).map((start, index) => {
                const end = boundaries[index + 1]
                return {
                    start,
                    text: this.target.slice(start, end),
                    marked: this.error_spans.some(span => span.start < end && span.end > start)
                }
            })
        }
    },
    methods: {
        commit(region) {
            if (typeof this.update_region === 'function') this.update_region(this.region_index, region)
        },
        update_score_data(data) {
            this.commit(data[0])
        },
        mark_selection(event) {
            if (event.button != null && event.button !== 0) return
            const selection = window.getSelection()
            if (!selection || selection.rangeCount !== 1) return
            const offsets = get_selection_offsets(event.currentTarget, selection.getRangeAt(0))
            if (!offsets) return
            const [start, end] = offsets
            if (start < 0 || end <= start || end > this.target.length || !this.target.slice(start, end).trim()) return
            if (this.error_spans.some(span => span.start === start && span.end === end)) {
                selection.removeAllRanges()
                return
            }
            const existing_ids = this.edits.filter(edit => edit.category === 'error')
                .map(edit => edit.id).filter(id => Number.isInteger(id) && id > 0)
            const id = Math.max(0, ...existing_ids) + 1
            this.commit({
                ...this.region,
                edits: [...this.edits, { category: 'error', id, annotation: null, output_idx: [[start, end]] }]
            })
            selection.removeAllRanges()
        },
        remove_error(error) {
            this.commit({
                ...this.region,
                edits: this.edits.filter(edit => !(edit.category === 'error' && edit.id === error.id))
            })
        },
        error_text(error) {
            return this.error_spans.filter(span => span.id === error.id)
                .map(span => this.target.slice(span.start, span.end)).join(' … ')
        }
    }
}
</script>

<template>
    <article class="manga-text-region" :aria-label="`Generated text region ${region_index + 1}`">
        <h4>Region {{ region_index + 1 }}</h4>
        <template v-if="typeof region.source === 'string' && region.source.trim()">
        <span class="region-text-label">Japanese source</span>
        <p class="region-source" lang="ja">{{ region.source }}</p>
        </template>
        <p v-if="target.length" class="region-target" :lang="language || 'en'" :dir="language === 'ar' ? 'rtl' : 'auto'" tabindex="0" aria-label="Generated translation text" @mouseup="mark_selection"><span v-for="segment in segments" :key="segment.start" :class="{ 'region-error-highlight': segment.marked }">{{ segment.text }}</span></p>
        <p v-else class="region-unavailable">No generated translation text for this region.</p>
        <OverallScore
            class="region-quality-score"
            :hits_data="[region]"
            :current_hit="1"
            :set_hits_data="update_score_data"
            :config="{}"
            :score_definition="TRANSLATION_QUALITY_SCORE"
            :compact="true"
            caption="Quality"
        />
        <div v-if="errors.length" class="region-errors" aria-label="Marked translation errors">
            <h5>Errors ({{ errors.length }})</h5>
            <ul>
                <li v-for="error in errors" :key="error.id">
                    <span class="region-error-text" :lang="language || 'en'" :dir="language === 'ar' ? 'rtl' : 'auto'">{{ error_text(error) }}</span>
                    <button type="button" @click="remove_error(error)" :aria-label="`Remove error ${error.id} from region ${region_index + 1}`">Remove</button>
                </li>
            </ul>
        </div>
    </article>
</template>

<style scoped>
.manga-text-region { min-width: 0; margin-top: 1rem; padding: 0.85rem; background: #fff; border: 1px solid #ccc; border-radius: 4px; }
.manga-text-region h4 { margin: 0 0 0.85rem; font-size: 1rem; }
.region-text-label { display: block; font-size: 0.8rem; font-weight: 600; color: #444; }
.region-source, .region-target { margin: 0.3rem 0 0.85rem; white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.5; }
.region-target { padding: 0.6rem; background: #f7f7f7; border: 1px solid #ddd; border-radius: 3px; cursor: text; }
.region-target:focus-visible { outline: 2px solid #245ba0; }
.region-error-highlight { background: #ffe0df; border-bottom: 2px solid #c33; }
.region-unavailable { color: #666; font-style: italic; line-height: 1.4; margin: 0.3rem 0 0.85rem; }
.region-quality-score { display: grid; grid-template-columns: minmax(0, 1fr) 4.5rem; gap: 0.35rem 0.75rem; margin: 0.75rem 0; text-align: left; }
.region-quality-score :deep(.candidate-score-caption) { grid-column: 1; font-size: 0.85rem; font-weight: 600; color: #333; }
.region-quality-score :deep(.candidate-score-input) { grid-column: 2; grid-row: 1; align-self: center; padding: 0.5rem 0.2rem; }
.region-errors h5 { margin: 0.75rem 0 0.4rem; font-size: 0.85rem; }
.region-errors ul { list-style: none; padding: 0; margin: 0; }
.region-errors li { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.5rem; }
.region-error-text { white-space: pre-wrap; overflow-wrap: anywhere; min-width: 0; font-size: 0.85rem; line-height: 1.4; }
.region-errors button { flex-shrink: 0; border: 1px solid #aaa; background: #fff; border-radius: 3px; padding: 0.2rem 0.4rem; font-size: 0.75rem; cursor: pointer; }
</style>
