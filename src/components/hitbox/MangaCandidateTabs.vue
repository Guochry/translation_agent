<script setup>
import { isRegionRated } from '../../assets/js/manga-util.js';
</script>
<script>
export default {
    props: ['candidates', 'active', 'uid'], emits: ['select'],
    methods: {
        select_key(index, offset, event) {
            const next = (index + offset + this.candidates.length) % this.candidates.length
            this.$emit('select', next)
            event.currentTarget.parentElement.children[next].focus()
        },
        status(candidate) {
            if (candidate.available === false) return 'Unavailable'
            if (candidate.translation_regions === null) return 'Text unavailable'
            const regions = candidate.translation_regions || []
            return `${regions.filter(isRegionRated).length}/${regions.length} regions rated`
        }
    }
}
</script>
<template>
    <div class="candidate-tabs" role="tablist" aria-label="Translation candidates">
        <button v-for="(candidate, index) in candidates" :key="candidate.id" type="button" role="tab"
            :id="`pair-tab-${uid}-${index}`" :aria-selected="active === index" :aria-controls="`pair-text-${uid}`"
            :tabindex="active === index ? 0 : -1" @click="$emit('select', index)"
            @keydown.right.prevent="select_key(index, 1, $event)" @keydown.left.prevent="select_key(index, -1, $event)">
            <span>Translation {{ String.fromCharCode(65 + index) }}</span><small>{{ status(candidate) }}</small>
        </button>
    </div>
</template>
<style scoped>
.candidate-tabs { display: flex; flex-wrap: wrap; gap: .5rem; margin: 0 0 1rem; }
button { flex: 1 1 100px; display: flex; flex-direction: column; gap: .25rem; align-items: center; cursor: pointer; padding: .65rem; border: 1px solid #aaa; border-radius: 4px; background: white; }
button[aria-selected=true] { background: #e8f0fb; border-color: #245ba0; font-weight: 600; }
small { color: #555; font-weight: normal; }
</style>
