<script setup>
import { nextTick, ref } from 'vue';
const props = defineProps({ modelValue: { type: String, default: '' }, origin: Object, language: String, languageLabel: String, candidates: Array });
const emit = defineEmits(['update:modelValue', 'start-from']);
const editor = ref(null);
const candidateText = candidate => (candidate.translation_regions || []).map(region => region.target).join('\n');
function startFrom(candidate) {
    if (props.modelValue.trim() || candidate.available === false) return;
    emit('start-from', candidate.id);
    nextTick(() => { editor.value?.focus(); const end = editor.value?.value.length || 0; editor.value?.setSelectionRange(end, end); });
}
</script>
<template>
    <section class="subtitle-post-edit" aria-label="Post-edit translation">
        <h2>Post-edit <small>(optional)</small></h2>
        <p>Combine strengths and fix errors across the translations to write an improved {{ languageLabel }} subtitle.</p>
        <label class="post-edit-label">Your improved translation
            <textarea ref="editor" :value="modelValue" :lang="language" :dir="language === 'ar' ? 'rtl' : 'auto'" rows="4"
                aria-label="Post-edited translation" placeholder="Write your improved translation here…"
                @input="emit('update:modelValue', $event.target.value)" />
        </label>
        <p v-if="modelValue.trim()" class="post-edit-save-note" aria-label="Post-edit starting point">Starting point:
            {{ origin?.type === 'candidate' ? origin.candidate_label : origin?.type === 'manual' ? 'manual entry' : 'not recorded' }}.
        </p>
        <p class="post-edit-save-note">Included when you download annotations. Shared across this clip’s translation candidates.</p>
        <details class="post-edit-comparison">
            <summary>Compare all translations</summary>
            <div class="post-edit-candidates">
                <article v-for="(candidate, index) in candidates || []" :key="candidate.id">
                    <h3>Translation {{ String.fromCharCode(65 + index) }}</h3>
                    <p v-if="candidate.available !== false" :lang="language" :dir="language === 'ar' ? 'rtl' : 'auto'">{{ candidateText(candidate) }}</p>
                    <p v-else class="post-edit-unavailable">Unavailable</p>
                    <button v-if="candidate.available !== false" type="button" :disabled="!!modelValue.trim() || !candidateText(candidate)"
                        :aria-label="`Start draft from Translation ${String.fromCharCode(65 + index)}`"
                        :title="modelValue.trim() ? 'Edit or clear your draft before starting from another candidate.' : 'Copy this translation into the empty draft.'"
                        @click="startFrom(candidate)">Use as starting draft</button>
                </article>
            </div>
        </details>
    </section>
</template>
<style scoped>
.subtitle-post-edit { margin-top: 1.5rem; padding: 1rem; border: 1px solid #dbe0e8; border-radius: 6px; background: #f6f8fb; }
h2 { font-size: 1.15rem; margin: 0 0 .6rem; }
small { font-size: .85rem; font-weight: normal; color: #626b78; }
p { line-height: 1.5; margin: .5rem 0 .8rem; }
.post-edit-label { display: flex; flex-direction: column; gap: .4rem; font-size: .9rem; font-weight: 600; }
textarea { width: 100%; box-sizing: border-box; resize: vertical; min-height: 105px; padding: .75rem; border: 1px solid #b7bec9; border-radius: 4px; font: inherit; font-weight: normal; line-height: 1.5; color: inherit; background: white; }
.post-edit-save-note { font-size: .8rem; color: #626b78; }
summary { cursor: pointer; font-size: .9rem; font-weight: 600; padding: .25rem 0; }
.post-edit-candidates { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap: .75rem; max-height: 350px; overflow: auto; }
article { min-width: 0; padding: .8rem; border: 1px solid #dbe0e8; border-radius: 4px; background: white; }
h3 { margin: 0 0 .5rem; font-size: .9rem; }
article p { white-space: pre-wrap; overflow-wrap: anywhere; font-size: .9rem; }
button { padding: .4rem .6rem; border: 1px solid #b7bec9; border-radius: 4px; color: inherit; background: #f6f8fb; cursor: pointer; font: inherit; font-size: .8rem; }
button:disabled { opacity: .5; cursor: default; }
:focus-visible { outline: 2px solid #245ba0; outline-offset: 2px; }
.post-edit-unavailable { color: #626b78; }
</style>
