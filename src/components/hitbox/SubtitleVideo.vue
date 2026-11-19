<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import SubtitlePlaybackControls from './SubtitlePlaybackControls.vue';
const props = defineProps({ src: String, label: String, muted: { type: Boolean, default: false }, volume: { type: Number, default: 1 } });
const emit = defineEmits(['play', 'update:muted', 'update:volume']);
const video = ref(null);
const container = ref(null);
const failed = ref(false);
const playing = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const actualMuted = ref(props.muted);
const actualVolume = ref(props.volume);
const fullscreen = ref(false);
const canFullscreen = ref(false);
const status = ref('');
const ready = computed(() => !failed.value && duration.value > 0);
let cueEnd = null;
let autoplayAttempted = false;
let destroyed = false;
const currentPlayer = player => !destroyed && player === video.value;
watch(() => props.src, () => {
    failed.value = false; playing.value = false; currentTime.value = 0;
    duration.value = 0; cueEnd = null; autoplayAttempted = false; status.value = '';
});
watch(() => props.muted, value => { if (video.value) video.value.muted = value; });
watch(() => props.volume, value => { if (video.value) video.value.volume = value; });
function syncTime() {
    const player = video.value;
    if (!player) return;
    currentTime.value = player.currentTime;
    if (Number.isFinite(player.duration)) duration.value = player.duration;
    if (cueEnd != null && player.currentTime >= cueEnd) { player.pause(); cueEnd = null; }
}
function syncAudio() {
    if (!video.value) return;
    actualMuted.value = video.value.muted;
    actualVolume.value = video.value.volume;
    emit('update:muted', actualMuted.value);
    emit('update:volume', actualVolume.value);
}
async function autoplayOnce() {
    if (autoplayAttempted || !video.value) return;
    autoplayAttempted = true;
    const player = video.value;
    try { await player.play(); }
    catch (error) {
        if (!currentPlayer(player)) return;
        if (error.name === 'NotAllowedError' && !player.muted) {
            player.muted = true;
            syncAudio();
            try { await player.play(); status.value = 'Autoplay started muted. Use Unmute for sound.'; return; }
            catch { /* A Play button remains available if the browser blocks autoplay. */ }
        }
        if (currentPlayer(player)) status.value = 'Press Play to start the video.';
    }
}
function metadataLoaded() { syncTime(); syncAudio(); autoplayOnce(); }
async function play() {
    const player = video.value;
    if (!player) return;
    autoplayAttempted = true;
    status.value = '';
    try { await player.play(); }
    catch { if (currentPlayer(player)) status.value = 'Could not start playback. Try Play again.'; }
}
function togglePlay() {
    if (!video.value) return;
    cueEnd = null;
    if (video.value.paused) { if (video.value.ended) video.value.currentTime = 0; play(); }
    else video.value.pause();
}
function seek(value) {
    if (!video.value || !ready.value) return;
    cueEnd = null;
    currentTime.value = Math.max(0, Math.min(duration.value, value));
    video.value.currentTime = currentTime.value;
}
function restart() { seek(0); play(); }
function setVolume(value) {
    if (!video.value) return;
    video.value.volume = Math.max(0, Math.min(1, value));
    video.value.muted = value === 0;
    syncAudio();
    status.value = '';
}
function toggleMute() {
    if (!video.value) return;
    video.value.muted = !(video.value.muted || video.value.volume === 0);
    if (!video.value.muted && video.value.volume === 0) video.value.volume = 1;
    syncAudio(); status.value = '';
}
async function playCue(start, end) {
    const player = video.value;
    if (!player) return;
    autoplayAttempted = true;
    if (player.readyState === 0) {
        await new Promise(resolve => {
            const done = () => { player.removeEventListener('loadedmetadata', done); player.removeEventListener('error', done); resolve(); };
            player.addEventListener('loadedmetadata', done);
            player.addEventListener('error', done);
            player.load();
        });
    }
    if (!currentPlayer(player) || player.readyState === 0) return;
    player.currentTime = start;
    cueEnd = end;
    await play();
}
function fullscreenChanged() { fullscreen.value = document.fullscreenElement === container.value; }
async function toggleFullscreen() {
    try {
        if (fullscreen.value) await document.exitFullscreen();
        else await container.value?.requestFullscreen();
    } catch { status.value = 'Fullscreen is unavailable in this browser.'; }
}
onMounted(() => {
    canFullscreen.value = !!document.fullscreenEnabled && typeof container.value?.requestFullscreen === 'function';
    document.addEventListener('fullscreenchange', fullscreenChanged);
});
onBeforeUnmount(() => { destroyed = true; document.removeEventListener('fullscreenchange', fullscreenChanged); });
defineExpose({ playCue, pause: () => video.value?.pause() });
</script>
<template>
    <div class="subtitle-video">
        <div v-if="src" ref="container" class="subtitle-player">
            <div class="video-stage">
                <video :key="src" ref="video" :src="src" :muted="muted" :volume="volume" playsinline preload="metadata" :aria-label="label" tabindex="0"
                    @loadedmetadata="metadataLoaded" @durationchange="syncTime" @timeupdate="syncTime" @seeked="syncTime"
                    @error="failed = true; playing = false" @play="playing = true; $emit('play')" @pause="playing = false"
                    @ended="playing = false; cueEnd = null" @volumechange="syncAudio"
                    @click="togglePlay" @keydown.space.prevent="togglePlay" @keydown.enter.prevent="togglePlay" />
            </div>
            <SubtitlePlaybackControls :playing="playing" :current-time="currentTime" :duration="duration" :volume="actualVolume" :muted="actualMuted"
                :ready="ready" :fullscreen="fullscreen" :can-fullscreen="canFullscreen" @toggle-play="togglePlay" @restart="restart"
                @seek="seek" @volume="setVolume" @toggle-mute="toggleMute" @fullscreen="toggleFullscreen" />
            <p v-if="status" class="playback-status" role="status">{{ status }}</p>
        </div>
        <p v-else class="media-message">Video hosting has not been configured for this site.</p>
        <p v-if="failed" class="media-message" role="alert">Could not load this video. Check your connection or open it directly.</p>
        <a v-if="src" :href="src" target="_blank" rel="noopener">Open video</a>
    </div>
</template>
<style scoped>
.video-stage { min-width: 0; }
video { display: block; width: 100%; background: #151515; aspect-ratio: 16 / 9; object-fit: contain; border-radius: 5px 5px 0 0; }
a { display: inline-block; margin-top: .4rem; font-size: .8rem; }
.media-message { background: #fff3d5; padding: 1rem; line-height: 1.4; }
.playback-status { font-size: .8rem; margin: .4rem 0 0; color: #626b78; }
.subtitle-player:fullscreen { display: flex; flex-direction: column; width: 100%; height: 100%; box-sizing: border-box; padding: 1rem; background: #151515; }
.subtitle-player:fullscreen .video-stage { display: flex; flex: 1; min-height: 0; }
.subtitle-player:fullscreen video { height: 100%; aspect-ratio: auto; }
.subtitle-player:fullscreen .subtitle-playback-controls { flex-shrink: 0; }
.subtitle-player:fullscreen .playback-status { color: white; }
</style>
