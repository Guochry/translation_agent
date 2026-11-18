<script setup>
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
import VueMarkdown from 'vue-markdown-render';
import OverallScore from '../common/OverallScore.vue';
import MangaTextRegion from '../hitbox/MangaTextRegion.vue';
import MangaSpanLegend from '../hitbox/MangaSpanLegend.vue';
import SubtitleVideo from '../hitbox/SubtitleVideo.vue';
import { cloneSubtitleData, validateSubtitleDataset, restoreSubtitleAnnotations, resetSubtitleClip,
    subtitleClipRated, subtitleCandidateRated, subtitleRegionRated, subtitleMediaUrl,
    SUBTITLE_FIDELITY, SUBTITLE_PRESENTATION, CLIP_FIDELITY, CLIP_PRESENTATION } from '../../assets/js/subtitle-util.js';

const props = defineProps({ input_data: Array, config: Object });
const canonical = cloneSubtitleData(props.input_data);
const rows = shallowRef(cloneSubtitleData(props.input_data));
const dataError = ref('');
try { validateSubtitleDataset(canonical, props.config.languages.map(l => l.code)); }
catch (error) { dataError.value = error.message; }
const language = ref(props.config.default_language || props.config.languages[0].code);
const index = ref(0);
const activeCandidate = ref(0);
const spanCategory = ref('error');
const message = ref('');
const uploadError = ref('');
const dirty = ref(false);
const originalPlayer = ref(null);
const translatedPlayer = ref(null);
const uploadInput = ref(null);
const hits = computed(() => rows.value.filter(hit => hit.language === language.value));
const hit = computed(() => hits.value[index.value]);
const candidate = computed(() => hit.value?.candidates[activeCandidate.value]);
const candidateLabel = computed(() => `Translation ${String.fromCharCode(65 + activeCandidate.value)}`);
const orderedReferences = computed(() => [...(hit.value?.references || [])].sort((a, b) => Number(b.language === language.value) - Number(a.language === language.value)));
const rated = code => rows.value.filter(row => row.language === code && subtitleClipRated(row)).length;
const total = code => rows.value.filter(row => row.language === code).length;
const languageName = code => props.config.languages.find(l => l.code === code)?.label || code;
const media = path => subtitleMediaUrl(path, { dev: import.meta.env.DEV, base: import.meta.env.BASE_URL,
    prefix: props.config.subtitle_media_prefix, mediaBase: props.config.subtitle_media_base });
const formatTime = value => `${Math.floor(value / 60)}:${(value % 60).toFixed(2).padStart(5, '0')}`;
function pausePlayers() { originalPlayer.value?.pause(); translatedPlayer.value?.pause(); }
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
function resetClip() { replaceHit(resetSubtitleClip(hit.value)); message.value = 'Scores and spans reset for this clip in the selected language.'; }
function candidateStatus(c) {
    if (!c.available) return 'Unavailable';
    if (subtitleCandidateRated(c)) return 'Fully rated';
    return `${c.translation_regions.filter(subtitleRegionRated).length}/${c.translation_regions.length} subtitles rated`;
}
function download() {
    const blob = new Blob([JSON.stringify(rows.value, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `subtitle-annotations-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    dirty.value = false;
    message.value = 'Download includes annotations for all languages.';
}
async function upload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
        const imported = restoreSubtitleAnnotations(canonical, JSON.parse(await file.text()));
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
onBeforeUnmount(() => window.removeEventListener('beforeunload', warnBeforeClosing));
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
        <h1>Multilingual Subtitle Evaluation</h1>
        <VueMarkdown class="subtitle-instructions" :source="config.instructions || ''" />
        <p v-if="!media(hit.original_video)" class="hosting-notice" role="status">Video hosting is pending. Use the local preview to watch and rate the videos.</p>
        <nav class="subtitle-navigation" aria-label="Clip navigation">
            <div>
                <button :disabled="index === 0" aria-label="Previous clip" @click="navigate(index - 1)">←</button>
                <label>Clip <select :value="index" aria-label="Choose clip" @change="navigate($event.target.value)">
                    <option v-for="(row, position) in hits" :key="row.id" :value="position">{{ position + 1 }}{{ subtitleClipRated(row) ? ' ✓' : '' }}{{ row.bookmark ? ' ★' : '' }}</option>
                </select> / {{ hits.length }}</label>
                <button :disabled="index === hits.length - 1" aria-label="Next clip" @click="navigate(index + 1)">→</button>
                <span class="progress-count">{{ rated(language) }}/{{ hits.length }} clips fully rated</span>
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
            <h2>{{ hit.title }} <small>· Clip {{ index + 1 }}</small></h2>
            <div>
                <button :aria-pressed="hit.bookmark" @click="replaceHit({ ...hit, bookmark: !hit.bookmark })">{{ hit.bookmark ? 'Bookmarked ★' : 'Bookmark clip' }}</button>
                <button @click="resetClip">Reset clip</button>
            </div>
        </div>
        <div class="subtitle-candidate-tabs" role="tablist" aria-label="Translation candidates">
            <button v-for="(item, position) in hit.candidates" :key="item.id" role="tab"
                :id="`subtitle-tab-${position}`" :aria-selected="activeCandidate === position" aria-controls="subtitle-candidate-panel"
                :tabindex="activeCandidate === position ? 0 : -1" @click="activeCandidate = position"
                @keydown.right.prevent="activeCandidate = (position + 1) % hit.candidates.length; $event.currentTarget.parentElement.children[activeCandidate].focus()"
                @keydown.left.prevent="activeCandidate = (position + hit.candidates.length - 1) % hit.candidates.length; $event.currentTarget.parentElement.children[activeCandidate].focus()">
                Translation {{ String.fromCharCode(65 + position) }}<small>{{ candidateStatus(item) }}</small>
            </button>
        </div>
        <div class="subtitle-workspace">
            <aside class="reference-column">
                <section class="reference-card">
                    <h3>Human reference</h3>
                    <div v-for="reference in orderedReferences" :key="reference.language">
                        <h4>{{ languageName(reference.language) }}</h4>
                        <p :lang="reference.language" dir="auto">{{ reference.text }}</p>
                    </div>
                </section>
                <section class="reference-card">
                    <h3>Original Chinese video</h3>
                    <SubtitleVideo ref="originalPlayer" :src="media(hit.original_video)" label="Original Chinese video" @play="translatedPlayer?.pause()" />
                    <p lang="zh">{{ hit.source }}</p>
                </section>
                <details class="reference-card">
                    <summary>Dialogue context</summary>
                    <h4>Before this clip</h4>
                    <p v-for="(line, position) in hit.context_before" :key="`before-${position}`" lang="zh">{{ line }}</p>
                    <h4>After this clip</h4>
                    <p v-for="(line, position) in hit.context_after" :key="`after-${position}`" lang="zh">{{ line }}</p>
                </details>
            </aside>
            <section class="translated-column" id="subtitle-candidate-panel" role="tabpanel" :aria-labelledby="`subtitle-tab-${activeCandidate}`">
                <h3>{{ candidateLabel }} · {{ languageName(language) }}</h3>
                <SubtitleVideo v-if="candidate.available" :key="`${hit.id}-${candidate.id}`" ref="translatedPlayer"
                    :src="media(candidate.translated_video)" :label="`${candidateLabel} rendered video`" @play="originalPlayer?.pause()" />
                <p v-else class="unavailable">This translation is unavailable for this clip. Continue with the other candidates.</p>
                <p class="player-hint" v-if="candidate.available">Use fullscreen to inspect the subtitles. Replay a subtitle from its card.</p>
            </section>
            <aside class="annotation-column" :key="`${hit.id}-${candidate.id}`" aria-label="Subtitle annotations">
                <template v-if="candidate.available">
                    <h3>Clip scores</h3>
                    <div class="clip-scores">
                        <OverallScore :hits_data="[candidate]" :current_hit="1" :set_hits_data="data => replaceCandidate(data[0])"
                            :config="{}" :score_definition="CLIP_FIDELITY" :compact="true" caption="Fidelity" />
                        <OverallScore :hits_data="[candidate]" :current_hit="1" :set_hits_data="data => replaceCandidate(data[0])"
                            :config="{}" :score_definition="CLIP_PRESENTATION" :compact="true" caption="Presentation" />
                    </div>
                    <MangaSpanLegend v-model="spanCategory" />
                    <div v-for="(region, position) in candidate.translation_regions" :key="region.id" class="subtitle-cue">
                        <button class="replay-cue" @click="originalPlayer?.pause(); translatedPlayer?.playCue(region.start_seconds, region.end_seconds)">
                            ▶ Replay {{ formatTime(region.start_seconds) }}–{{ formatTime(region.end_seconds) }}
                        </button>
                        <MangaTextRegion :region="region" :region_index="position" :update_region="updateRegion" :language="language"
                            :span_category="spanCategory" source_label="Chinese source" source_language="zh" region_label="Subtitle"
                            :fidelity_definition="SUBTITLE_FIDELITY" :presentation_definition="SUBTITLE_PRESENTATION" />
                    </div>
                    <label class="candidate-notes">Notes (optional)
                        <textarea :value="candidate.comment || ''" @input="replaceCandidate({ ...candidate, comment: $event.target.value })" rows="2" />
                    </label>
                </template>
            </aside>
        </div>
    </div>
</template>

<style scoped>
@font-face { font-family: SubtitleCJK; src: url('/fonts/manga/NotoSansCJKjp-Regular.otf') format('opentype'); font-display: swap; }
@font-face { font-family: SubtitleHindi; src: url('/fonts/manga/NotoSansDevanagari.ttf') format('truetype'); font-weight: 100 900; font-display: swap; }
.subtitle-evaluation { max-width: 1800px; margin: 1.5rem auto 3rem; color: #202735; }
.subtitle-evaluation :deep([lang="zh"]) { font-family: SubtitleCJK, sans-serif; }
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
.subtitle-navigation { justify-content: space-between; padding: 1rem 0; border-top: 1px solid #d8dde4; margin-top: 1.4rem; }
.progress-count { color: #586270; font-size: .8rem; margin-left: .5rem; }
.clip-heading { justify-content: space-between; margin: .8rem 0 1rem; }
.subtitle-candidate-tabs { display: flex; gap: .5rem; margin-bottom: 1rem; flex-wrap: wrap; }
.subtitle-candidate-tabs button { flex: 1 1 100px; }
.subtitle-workspace { display: grid; grid-template-columns: minmax(210px, .8fr) minmax(0, 2.3fr) minmax(290px, 1.1fr); gap: 1rem; align-items: start; }
.reference-column, .translated-column, .annotation-column { min-width: 0; position: sticky; top: 1rem; }
.reference-column, .annotation-column { max-height: calc(100vh - 2rem); overflow: auto; scrollbar-gutter: stable; }
.reference-card { padding: .85rem; background: #f6f8fb; border: 1px solid #dbe0e8; border-radius: 6px; margin-bottom: .75rem; }
.reference-card p { white-space: pre-wrap; overflow-wrap: anywhere; font-size: .9rem; margin: .4rem 0; }
.reference-card summary { cursor: pointer; font-weight: 600; font-size: .85rem; }
.annotation-column { background: #f6f8fb; border: 1px solid #dbe0e8; border-radius: 6px; padding: .8rem; }
.clip-scores { display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; }
.clip-scores :deep(.candidate-score-box), .annotation-column :deep(.candidate-score-box) { display: flex; flex-direction: column; gap: .3rem; margin: 0; min-width: 0; }
.clip-scores :deep(input), .annotation-column :deep(.candidate-score-input) { width: 100%; max-width: 130px; padding: .45rem; box-sizing: border-box; border: 1px solid #aaa; border-radius: 4px; font-size: 1rem; }
.clip-scores :deep(.candidate-score-caption) { font-size: .8rem; font-weight: 600; }
.subtitle-cue { margin: .8rem 0; }
.subtitle-cue :deep(.manga-text-region) { margin-top: .4rem; }
.replay-cue { font-size: .8rem; background: #fff; }
.player-hint { color: #626b78; font-size: .8rem; }
.candidate-notes { font-size: .8rem; display: flex; flex-direction: column; gap: .4rem; }
textarea { resize: vertical; border: 1px solid #b7bec9; border-radius: 4px; padding: .5rem; }
.hosting-notice, .unavailable { background: #fff3d5; padding: .8rem; border-radius: 4px; }
.upload-error { color: #a11b1b; }
@media (max-width: 1150px) { .subtitle-workspace { grid-template-columns: minmax(180px, .7fr) minmax(0, 1.5fr) minmax(265px, 1fr); gap: .7rem; } }
@media (max-width: 850px) {
    .subtitle-workspace { grid-template-columns: 1fr; }
    .reference-column, .translated-column, .annotation-column { position: static; max-height: none; overflow: visible; }
    .translated-column { grid-row: 1; }
    .reference-column { grid-row: 2; }
    .subtitle-evaluation { margin-top: 1rem; }
}
</style>
