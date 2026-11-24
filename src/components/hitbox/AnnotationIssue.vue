<script setup>
import { ISSUE_TYPES } from '../../assets/js/annotation-issue-util.js';

const props = defineProps({ modelValue: Object, sourceLabel: { type: String, default: 'source text' } });
const emit = defineEmits(['update:modelValue']);

function setIssue(category, note = props.modelValue?.note || '') {
    emit('update:modelValue', category ? { category, note } : null);
}
</script>

<template>
    <details class="annotation-issue" :open="modelValue ? true : undefined">
        <summary>Flag a problem <span v-if="modelValue">· Flagged</span><span v-else> (optional)</span></summary>
        <p>Use this for problems a highlight can’t show, such as missing meaning or unclear {{ sourceLabel }}.</p>
        <label>
            Issue type
            <select :value="modelValue?.category || ''" @change="setIssue($event.target.value)">
                <option value="">None</option>
                <option v-for="(label, code) in ISSUE_TYPES" :key="code" :value="code">{{ label }}</option>
            </select>
        </label>
        <label v-if="modelValue">
            Short note (optional)
            <textarea rows="2" dir="auto" :value="modelValue.note"
                @input="setIssue(modelValue.category, $event.target.value)" />
        </label>
    </details>
</template>

<style scoped>
.annotation-issue summary { cursor: pointer; font-size: .9rem; }
.annotation-issue p { font-size: .85rem; margin: .5rem 0; }
.annotation-issue label { display: grid; gap: .25rem; margin-top: .5rem; font-size: .85rem; }
.annotation-issue textarea { resize: vertical; }
</style>
