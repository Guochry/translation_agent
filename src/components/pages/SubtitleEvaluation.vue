<script setup>
import { computed, nextTick, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
import VueMarkdown from 'vue-markdown-render';
import MangaTextRegion from '../hitbox/MangaTextRegion.vue';
import MangaSpanLegend from '../hitbox/MangaSpanLegend.vue';
import SubtitleVideo from '../hitbox/SubtitleVideo.vue';
import GoogleTranslateBox from '../hitbox/GoogleTranslateBox.vue';
import AnnotationIssue from '../hitbox/AnnotationIssue.vue';
import SubtitlePostEdit from '../hitbox/SubtitlePostEdit.vue';
import { BOOK_FIDELITY, bookCandidateDisplayText, bookCandidateRated, bookDisplayTitle, bookFableRated, restoreBookAnnotations, validateBookDataset } from '../../assets/js/book-util.js';
import { cloneSubtitleData, validateSubtitleDataset, restoreSubtitleAnnotations, resetSubtitleClip,
    subtitleClipRated, subtitleCandidateRated, subtitleRegionRated, subtitleMediaUrl, updateSubtitlePostEdit, startSubtitlePostEdit,
    SUBTITLE_FIDELITY, SUBTITLE_PRESENTATION } from '../../assets/js/subtitle-util.js';

const props = defineProps({ input_data: Array, config: Object });
const isBook = Boolean(props.config.book_evaluation);
const itemLabel = isBook ? 'fable' : 'clip';
const navigationLabel = isBook ? 'Fable' : 'Clip';
const validateDataset = isBook ? validateBookDataset : validateSubtitleDataset;
const restoreAnnotations = isBook ? restoreBookAnnotations : restoreSubtitleAnnotations;
const itemRated = isBook ? bookFableRated : subtitleClipRated;
const canonical = cloneSubtitleData(props.input_data);
const rows = shallowRef(cloneSubtitleData(props.input_data));
const dataError = ref('');
try { validateDataset(canonical, props.config.languages.map(l => l.code)); }
catch (error) { dataError.value = error.message; }
const language = ref(props.config.default_language || props.config.languages[0].code);
const index = ref(0);
const activeCandidate = ref(0);
const spanCategory = ref('error');
const message = ref('');
const uploadError = ref('');
const dirty = ref(false);
const translatedPlayer = ref(null);
const videoMuted = ref(false);
const videoVolume = ref(1);
const uploadInput = ref(null);
const hits = computed(() => rows.value.filter(hit => hit.language === language.value));
const hit = computed(() => hits.value[index.value]);
const displayTitle = computed(() => isBook && hit.value ? bookDisplayTitle(hit.value.title) : hit.value?.title);
const sourceParagraphs = computed(() => hit.value?.source.split(/\n\s*\n/).map(paragraph => paragraph.replace(/\s+/g, ' ').trim()) || []);
const candidate = computed(() => hit.value?.candidates[activeCandidate.value]);
const candidateLabel = computed(() => `Translation ${String.fromCharCode(65 + activeCandidate.value)}`);
const orderedReferences = computed(() => (hit.value?.references || [])
    .filter(reference => reference.language === 'en' || (language.value === 'vi' && reference.language === 'vi'))
    .sort((a, b) => Number(b.language === language.value) - Number(a.language === language.value)));
const rated = code => rows.value.filter(row => row.language === code && itemRated(row)).length;
const total = code => rows.value.filter(row => row.language === code).length;
const languageName = code => props.config.languages.find(l => l.code === code)?.label || code;
const media = path => subtitleMediaUrl(path, { dev: import.meta.env.DEV, base: import.meta.env.BASE_URL,
    prefix: props.config.subtitle_media_prefix, mediaBase: props.config.subtitle_media_base });
const formatTime = value => `${Math.floor(value / 60)}:${(value % 60).toFixed(2).padStart(5, '0')}`;
function pausePlayers() { translatedPlayer.value?.pause(); }
watch([language, index, activeCandidate], pausePlayers, { flush: 'sync' });
function selectLanguage(code) {
    language.value = code;
    index.value = Math.min(index.value, hits.value.length - 1);
    activeCandidate.value = 0;
}
function navigate(value) {
    index.value = Math.max(0, Math.min(hits.value.length - 1, Number(value) || 0));
    activeCandidate.value = 0;
}
function replaceHit(next) {
    rows.value = rows.value.map(row => row.id === next.id ? next : row);
    dirty.value = true;
}
function replaceCandidate(next) {
    replaceHit({ ...hit.value, candidates: hit.value.candidates.map((c, i) => i === activeCandidate.value ? next : c) });
}
function updateRegion(regionIndex, region) {
    replaceCandidate({ ...candidate.value, translation_regions: candidate.value.translation_regions.map((r, i) => i === regionIndex ? region : r) });
}
function resetClip() {
    replaceHit(resetSubtitleClip(hit.value));
    message.value = `Scores, spans, issue flags, and post-edit reset for this ${itemLabel} in the selected language.`;
}
function candidateStatus(c) {
    if (!c.available) return 'Unavailable';
    if (isBook ? bookCandidateRated(c) : subtitleCandidateRated(c)) return 'Fully rated';
    if (c.translation_regions.length === 1) return 'Not rated';
    return `${c.translation_regions.filter(subtitleRegionRated).length}/${c.translation_regions.length} subtitles rated`;
}
function download() {
    const blob = new Blob([JSON.stringify(rows.value, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${isBook ? 'book' : 'subtitle'}-annotations${props.config.evaluation_batch ? '-' + props.config.evaluation_batch : ''}-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    dirty.value = false;
    message.value = 'Download includes annotations for all languages.';
}
async function upload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
        const imported = restoreAnnotations(canonical, JSON.parse(await file.text()));
        const byId = new Map(imported.map(row => [row.id, row]));
        rows.value = rows.value.map(row => byId.get(row.id) || row);
        if (!imported.some(row => row.language === language.value)) selectLanguage(imported[0].language);
        message.value = 'Annotations restored.';
        uploadError.value = '';
        dirty.value = true;
    } catch (error) { uploadError.value = error.message; }
    event.target.value = '';
}
function warnBeforeClosing(event) {
    if (dirty.value) { event.preventDefault(); event.returnValue = ''; }
}
window.addEventListener('beforeunload', warnBeforeClosing);
function handleNavigationShortcut(event) {
    if (event.defaultPrevented || event.isComposing || event.repeat || event.ctrlKey || event.metaKey || event.altKey || dataError.value) return;
    const target = event.target instanceof Element ? event.target : document.activeElement;
    if (target?.closest('input, textarea, select') || target?.isContentEditable) return;
    const key = event.key.toLowerCase();
    if (key === 'q' || key === 'e') {
        event.preventDefault();
        const next = Math.max(0, Math.min(hits.value.length - 1, index.value + (key === 'q' ? -1 : 1)));
        if (next !== index.value) {
            navigate(next);
            if (target?.closest('.subtitle-candidate-tabs')) nextTick(() => document.getElementById('subtitle-tab-0')?.focus());
        }
        return;
    }
    if (key !== 'a' && key !== 'd') return;
    const count = hit.value?.candidates.length || 0;
    if (count < 2) return;
    event.preventDefault();
    activeCandidate.value = (activeCandidate.value + (key === 'a' ? -1 : 1) + count) % count;
    if (target?.closest('.subtitle-candidate-tabs')) document.getElementById(`subtitle-tab-${activeCandidate.value}`)?.focus();
}
window.addEventListener('keydown', handleNavigationShortcut);
onBeforeUnmount(() => {
    window.removeEventListener('beforeunload', warnBeforeClosing);
    window.removeEventListener('keydown', handleNavigationShortcut);
});
</script>

<template>
    <div v-if="dataError" role="alert">{{ dataError }}</div>
    <div v-else class="subtitle-evaluation">
        <section aria-label="Choose your native language">
            <p>Choose your native language.</p>
            <div class="language-buttons">
                <button v-for="item in config.languages" :key="item.code" :aria-pressed="language === item.code" @click="selectLanguage(item.code)">
                    <span :lang="item.code">{{ item.native_label || item.label }}</span>
                    <small>{{ item.label }} · {{ rated(item.code) }}/{{ total(item.code) }} rated</small>
                </button>
            </div>
        </section>
        <h1>{{ config.evaluation_title || 'Multilingual Subtitle Evaluation' }}</h1>
        <VueMarkdown class="subtitle-instructions" :source="config.instructions || ''" />
        <p v-if="!isBook && !media(hit.original_video)" class="hosting-notice" role="status">Video hosting is pending. Use the local preview to watch and rate the videos.</p>
        <nav class="subtitle-navigation" :aria-label="`${navigationLabel} navigation`">
            <div>
                <button :disabled="index === 0" :aria-label="`Previous ${itemLabel}`" @click="navigate(index - 1)">←</button>
                <label>{{ navigationLabel }} <select :value="index" :aria-label="`Choose ${itemLabel}`" @change="navigate($event.target.value)">
                    <option v-for="(row, position) in hits" :key="row.id" :value="position">{{ position + 1 }}{{ itemRated(row) ? ' ✓' : '' }}{{ row.bookmark ? ' ★' : '' }}</option>
                </select> / {{ hits.length }}</label>
                <button :disabled="index === hits.length - 1" :aria-label="`Next ${itemLabel}`" @click="navigate(index + 1)">→</button>
                <span class="progress-count">{{ rated(language) }}/{{ hits.length }} {{ itemLabel }}s fully rated</span>
            </div>
            <div class="file-buttons">
                <button @click="download">Download annotations</button>
                <button @click="uploadInput.click()">Upload annotations</button>
                <input ref="uploadInput" type="file" accept=".json,application/json" hidden @change="upload" />
            </div>
        </nav>
        <p v-if="uploadError" role="alert" class="upload-error">{{ uploadError }}</p>
        <p v-if="message" role="status">{{ message }}</p>
        <div class="clip-heading">
            <h2>{{ displayTitle }} <small>· {{ navigationLabel }} {{ index + 1 }}</small></h2>
            <div>
                <button :aria-pressed="hit.bookmark" @click="replaceHit({ ...hit, bookmark: !hit.bookmark })">{{ hit.bookmark ? 'Bookmarked ★' : 'Bookmark ' + itemLabel }}</button>
                <button @click="resetClip">Reset {{ itemLabel }}</button>
            </div>
        </div>
        <p class="player-hint">Translations: <kbd>A</kbd> previous · <kbd>D</kbd> next. {{ isBook ? 'Fables' : 'Videos' }}: <kbd>Q</kbd> previous · <kbd>E</kbd> next.</p>
        <div class="subtitle-candidate-tabs" role="tablist" aria-label="Translation candidates">
            <button v-for="(item, position) in hit.candidates" :key="item.id" role="tab"
                :id="`subtitle-tab-${position}`" :aria-selected="activeCandidate === position" aria-controls="subtitle-candidate-panel"
                :tabindex="activeCandidate === position ? 0 : -1" @click="activeCandidate = position"
                @keydown.right.prevent="activeCandidate = (position + 1) % hit.candidates.length; $event.currentTarget.parentElement.children[activeCandidate].focus()"
                @keydown.left.prevent="activeCandidate = (position + hit.candidates.length - 1) % hit.candidates.length; $event.currentTarget.parentElement.children[activeCandidate].focus()">
                Translation {{ String.fromCharCode(65 + position) }}<small>{{ candidateStatus(item) }}</small>
            </button>
        </div>
        <GoogleTranslateBox v-if="!isBook" :language="language" :languages="config.languages" :source="hit.source" />
        <div v-if="isBook" class="book-workspace">
            <section class="book-source" aria-label="English source" lang="en">
                <h3>English source</h3>
                <h4 class="book-source-title">{{ displayTitle }}</h4>
                <p v-for="(paragraph, position) in sourceParagraphs" :key="position">{{ paragraph }}</p>
            </section>
            <section class="annotation-column book-translation" :key="`${hit.id}-${candidate.id}`"
                id="subtitle-candidate-panel" role="tabpanel" :aria-labelledby="`subtitle-tab-${activeCandidate}`">
                <h3>{{ candidateLabel }} · {{ languageName(language) }}</h3>
                <template v-if="candidate.available">
                    <MangaSpanLegend v-model="spanCategory" />
                    <MangaTextRegion :region="candidate.translation_regions[0]" :region_index="0" :update_region="updateRegion"
                        :language="language" :span_category="spanCategory" hide_heading
                        :display_target="bookCandidateDisplayText(candidate)"
                        :fidelity_definition="BOOK_FIDELITY" :hide_presentation="true" />
                    <AnnotationIssue :model-value="candidate.annotation_issue"
                        @update:model-value="issue => replaceCandidate({ ...candidate, annotation_issue: issue })" />
                </template>
                <p v-else class="unavailable">This system has no output for this fable in this language.</p>
            </section>
        </div>
        <div v-else class="subtitle-workspace">
            <aside class="reference-column">
                <section class="reference-card">
                    <h3>Human reference</h3>
                    <div v-for="reference in orderedReferences" :key="reference.language">
                        <h4>{{ languageName(reference.language) }}</h4>
                        <p :lang="reference.language" dir="auto">{{ reference.text }}</p>
                    </div>
                </section>
                <details class="reference-card">
                    <summary>Dialogue context</summary>
                    <h4>Before this clip</h4>
                    <p v-for="(line, position) in hit.context_before_en" :key="`before-${position}`" lang="en">{{ line }}</p>
                    <h4>After this clip</h4>
                    <p v-for="(line, position) in hit.context_after_en" :key="`after-${position}`" lang="en">{{ line }}</p>
                </details>
            </aside>
            <section class="translated-column" id="subtitle-candidate-panel" role="tabpanel" :aria-labelledby="`subtitle-tab-${activeCandidate}`">
                <h3>{{ candidateLabel }} · {{ languageName(language) }}</h3>
                <SubtitleVideo v-if="candidate.available" :key="`${hit.id}-${candidate.id}`" ref="translatedPlayer"
                    :src="media(candidate.translated_video)" :label="`${candidateLabel} rendered video`"
                    v-model:muted="videoMuted" v-model:volume="videoVolume" />
                <p v-else class="unavailable">This translation is unavailable for this clip. Continue with the other candidates.</p>
                <p class="player-hint" v-if="candidate.available">Plays once automatically. Playback controls stay below the video.</p>
            </section>
            <aside class="annotation-column" :key="`${hit.id}-${candidate.id}`" aria-label="Subtitle annotations">
                <template v-if="candidate.available">
                    <MangaSpanLegend v-model="spanCategory" />
                    <div v-for="(region, position) in candidate.translation_regions" :key="region.id" class="subtitle-cue">
                        <button class="replay-cue" @click="translatedPlayer?.playCue(region.start_seconds, region.end_seconds)">
                            ▶ Replay<span v-if="candidate.translation_regions.length > 1"> {{ formatTime(region.start_seconds) }}–{{ formatTime(region.end_seconds) }}</span>
                        </button>
                        <MangaTextRegion :region="region" :region_index="position" :update_region="updateRegion" :language="language"
                            :span_category="spanCategory" source_label="Chinese source" source_language="zh" region_label="Subtitle"
                            :hide_heading="candidate.translation_regions.length === 1" target_label="Translation"
                            :fidelity_definition="SUBTITLE_FIDELITY" :presentation_definition="SUBTITLE_PRESENTATION" />
                    </div>
                    <AnnotationIssue :model-value="candidate.annotation_issue" source-label="dialogue"
                        @update:model-value="issue => replaceCandidate({ ...candidate, annotation_issue: issue })" />
                </template>
            </aside>
        </div>
        <SubtitlePostEdit :key="hit.id" :model-value="hit.post_edit || ''" :origin="hit.post_edit_origin" :language="language" :language-label="languageName(language)"
            :candidates="hit.candidates" :text-type="isBook ? 'version of the fable' : 'subtitle'"
            :display-candidate-text="isBook ? bookCandidateDisplayText : undefined" @update:model-value="text => replaceHit(updateSubtitlePostEdit(hit, text))"
            @start-from="id => replaceHit(startSubtitlePostEdit(hit, id))" />
    </div>
</template>

<style scoped>
@font-face { font-family: SubtitleCJK; src: url('/fonts/manga/NotoSansCJKjp-Regular.otf') format('opentype'); font-display: swap; }
@font-face { font-family: SubtitleHindi; src: url('/fonts/manga/NotoSansDevanagari.ttf') format('truetype'); font-weight: 100 900; font-display: swap; }
.subtitle-evaluation { max-width: 1800px; margin: 1.5rem auto 5rem; color: #202735; }
.subtitle-evaluation :deep([lang="zh"]), .subtitle-evaluation :deep([lang="zh-CN"]) { font-family: SubtitleCJK, sans-serif; }
.subtitle-evaluation :deep([lang="hi"]) { font-family: SubtitleHindi, sans-serif; }
h1 { font-size: 1.6rem; margin: 1.8rem 0 .8rem; }
h2 { font-size: 1.15rem; margin: 0; }
h3 { font-size: 1rem; margin: 0 0 .8rem; }
h4 { font-size: .8rem; color: #555; margin: .8rem 0 .35rem; }
p { line-height: 1.5; }
button, select { border: 1px solid #b7bec9; border-radius: 5px; padding: .45rem .7rem; background: white; cursor: pointer; color: inherit; }
button:disabled { cursor: default; opacity: .45; }
button:focus-visible, select:focus-visible { outline: 2px solid #245ba0; outline-offset: 2px; }
button[aria-pressed=true], button[aria-selected=true] { background: #eaf1fc; border-color: #376dc1; font-weight: 600; }
.language-buttons, .subtitle-navigation, .subtitle-navigation > div, .clip-heading, .clip-heading > div { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.language-buttons button, .subtitle-candidate-tabs button { display: flex; flex-direction: column; align-items: center; gap: .25rem; }
small { color: #586270; font-weight: 400; font-size: .78rem; }
.subtitle-instructions { line-height: 1.5; font-size: .92rem; }
.subtitle-instructions :deep(ul) { padding-left: 1.3rem; }
.subtitle-instructions :deep(li) { margin: .25rem 0; }
.subtitle-instructions :deep(table) { display: block; overflow-x: auto; border-collapse: collapse; margin: .4rem 0; }
.subtitle-instructions :deep(th),
.subtitle-instructions :deep(td) { border-bottom: 1px solid #dbe0e8; padding: .15rem .5rem; text-align: left; vertical-align: top; }
.subtitle-instructions :deep(th) { white-space: nowrap; }
.subtitle-instructions :deep(td) { min-width: 7rem; }
.subtitle-navigation { justify-content: space-between; padding: 1rem 0; border-top: 1px solid #d8dde4; margin-top: 1.4rem; }
.progress-count { color: #586270; font-size: .8rem; margin-left: .5rem; }
.clip-heading { justify-content: space-between; margin: .8rem 0 1rem; }
.subtitle-candidate-tabs { display: flex; gap: .5rem; margin-bottom: 1rem; flex-wrap: wrap; }
.subtitle-candidate-tabs button { flex: 1 1 100px; }
.subtitle-workspace { display: grid; grid-template-columns: minmax(210px, .8fr) minmax(0, 2.3fr) minmax(290px, 1.1fr); gap: 1rem; align-items: start; }
.book-workspace { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; align-items: start; }
.book-source { position: sticky; top: 1rem; max-height: calc(100vh - 2rem); overflow: auto; border: 1px solid #dbe0e8; border-radius: 6px; padding: 1rem; }
.book-source-title { margin: 0 0 .6rem; font-size: 1.05rem; color: inherit; overflow-wrap: anywhere; }
.book-source p { margin: .6rem 0; overflow-wrap: anywhere; }
.book-translation :deep(.annotation-issue) { margin-top: .75rem; }
.reference-column, .translated-column, .annotation-column { min-width: 0; position: sticky; top: 1rem; }
.reference-column, .annotation-column { max-height: calc(100vh - 2rem); overflow: auto; scrollbar-gutter: stable; }
.reference-card { padding: .85rem; background: #f6f8fb; border: 1px solid #dbe0e8; border-radius: 6px; margin-bottom: .75rem; }
.reference-card p { white-space: pre-wrap; overflow-wrap: anywhere; font-size: .9rem; margin: .4rem 0; }
.reference-card summary { cursor: pointer; font-weight: 600; font-size: .85rem; }
.annotation-column { background: #f6f8fb; border: 1px solid #dbe0e8; border-radius: 6px; padding: .8rem; }
.annotation-column :deep(.candidate-score-box) { display: flex; flex-direction: column; gap: .3rem; margin: 0; min-width: 0; }
.annotation-column :deep(.candidate-score-input) { width: 100%; max-width: 130px; padding: .45rem; box-sizing: border-box; border: 1px solid #aaa; border-radius: 4px; font-size: 1rem; }
.subtitle-cue { margin: .8rem 0; }
.subtitle-cue :deep(.manga-text-region) { margin-top: .4rem; }
.replay-cue { font-size: .8rem; background: #fff; }
.player-hint { color: #626b78; font-size: .8rem; }
.hosting-notice, .unavailable { background: #fff3d5; padding: .8rem; border-radius: 4px; }
.upload-error { color: #a11b1b; }
@media (max-width: 1150px) { .subtitle-workspace { grid-template-columns: minmax(180px, .7fr) minmax(0, 1.5fr) minmax(265px, 1fr); gap: .7rem; } }
@media (max-width: 850px) {
    .subtitle-workspace { grid-template-columns: 1fr; }
    .book-workspace { grid-template-columns: minmax(0, 1fr); }
    .book-source { position: static; max-height: none; }
    .reference-column, .translated-column, .annotation-column { position: static; max-height: none; overflow: visible; }
    .translated-column { grid-row: 1; }
    .reference-column { grid-row: 2; }
    .subtitle-evaluation { margin-top: 1rem; }
}
</style>
