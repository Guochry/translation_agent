<script setup>
import { computed, ref, watch } from 'vue';
const props = defineProps({ language: String, languages: Array, source: String });
const expanded = ref(false);
const text = ref('');
const sourceLanguage = ref('zh-CN');
const targetLanguage = ref(props.language || 'en');
watch(() => props.language, code => { targetLanguage.value = code || 'en'; });
const options = computed(() => [...new Map([
    { code: 'zh-CN', label: 'Chinese' }, { code: 'en', label: 'English' }, ...(props.languages || [])
].map(language => [language.code, language])).values()]);
const translateUrl = computed(() => {
    const url = new URL('https://translate.google.com/');
    url.search = new URLSearchParams({ sl: sourceLanguage.value, tl: targetLanguage.value, text: text.value, op: 'translate' }).toString();
    return url.href;
});
</script>
<template>
    <aside class="google-translate-box" aria-label="Google Translate helper">
        <button class="translate-toggle" type="button" :aria-expanded="expanded" aria-controls="google-translate-content" @click="expanded = !expanded">
            <span>Google Translate</span><span aria-hidden="true">{{ expanded ? '−' : '+' }}</span>
        </button>
        <div v-if="expanded" id="google-translate-content" class="translate-content">
            <div class="translate-languages">
                <label>From<select v-model="sourceLanguage" aria-label="Google Translate source language">
                    <option value="auto">Detect language</option>
                    <option v-for="option in options" :key="option.code" :value="option.code">{{ option.label }}</option>
                </select></label>
                <label>To<select v-model="targetLanguage" aria-label="Google Translate target language">
                    <option v-for="option in options" :key="option.code" :value="option.code">{{ option.label }}</option>
                </select></label>
            </div>
            <label class="translate-text-label">Text to translate
                <textarea v-model="text" rows="3" dir="auto" :lang="sourceLanguage === 'zh-CN' ? 'zh' : sourceLanguage === 'auto' ? undefined : sourceLanguage" aria-label="Text for Google Translate" placeholder="Paste text here" />
            </label>
            <button type="button" class="use-source" :disabled="!source" @click="text = source; sourceLanguage = 'zh-CN'">Use Chinese source</button>
            <a class="translate-open" :href="text.trim() ? translateUrl : undefined" target="_blank" rel="noopener noreferrer"
                :aria-disabled="!text.trim()" :tabindex="text.trim() ? 0 : -1" @click="!text.trim() && $event.preventDefault()">Open Google Translate ↗</a>
            <small>Opens in a new tab.</small>
        </div>
    </aside>
</template>
<style scoped>
.google-translate-box { position: fixed; left: 1rem; bottom: 1rem; width: 290px; max-width: calc(100vw - 2rem); z-index: 20; background: white; border: 1px solid #b7bec9; border-radius: 8px; box-shadow: 0 3px 16px #0002; color: #202735; font-size: .85rem; }
.translate-toggle { width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: .7rem .85rem; background: #eaf1fc; border: 0; border-radius: 8px; font-weight: 600; color: inherit; cursor: pointer; }
.translate-content { padding: .8rem; max-height: calc(100dvh - 6rem); overflow: auto; }
.translate-languages { display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin-bottom: .65rem; }
label { display: flex; flex-direction: column; gap: .3rem; min-width: 0; }
select, textarea { box-sizing: border-box; width: 100%; min-width: 0; border: 1px solid #b7bec9; border-radius: 4px; padding: .4rem; background: white; color: inherit; font: inherit; }
textarea { resize: vertical; max-height: 160px; }
.use-source { margin: .5rem 0; border: 1px solid #b7bec9; border-radius: 4px; padding: .35rem .5rem; background: white; color: inherit; cursor: pointer; font: inherit; }
.translate-open { display: block; padding: .55rem; border-radius: 4px; background: #245ba0; color: white; text-align: center; text-decoration: none; }
.translate-open[aria-disabled=true] { opacity: .45; cursor: default; }
small { display: block; margin-top: .4rem; color: #626b78; }
:focus-visible { outline: 2px solid #245ba0; outline-offset: 2px; }
</style>
