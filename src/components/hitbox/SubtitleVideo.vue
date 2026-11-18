<script setup>
import { ref, watch } from 'vue';
const props = defineProps({ src: String, label: String });
defineEmits(['play']);
const video = ref(null);
const failed = ref(false);
watch(() => props.src, () => { failed.value = false; });
async function playCue(start, end) {
    const player = video.value;
    if (!player) return;
    if (player.readyState === 0) {
        player.load();
        await new Promise(resolve => {
            player.addEventListener('loadedmetadata', resolve, { once: true });
            player.addEventListener('error', resolve, { once: true });
        });
    }
    if (player.readyState === 0) return;
    player.currentTime = start;
    cueEnd = end;
    try { await player.play(); } catch { /* Native controls remain available. */ }
}
let cueEnd = null;
watch(() => props.src, () => { cueEnd = null; });
function stopCue() {
    if (cueEnd != null && video.value?.currentTime >= cueEnd) {
        video.value.pause();
        cueEnd = null;
    }
}
defineExpose({ playCue, pause: () => video.value?.pause() });
</script>
<template>
    <div class="subtitle-video">
        <video v-if="src" :key="src" ref="video" :src="src" controls playsinline preload="metadata" :aria-label="label"
            @error="failed = true" @play="$emit('play')" @timeupdate="stopCue" />
        <p v-else class="media-message">Video hosting has not been configured for this site.</p>
        <p v-if="failed" class="media-message" role="alert">Could not load this video. Check your connection or open it directly.</p>
        <a v-if="src" :href="src" target="_blank" rel="noopener">Open video</a>
    </div>
</template>
<style scoped>
video { display: block; width: 100%; background: #151515; aspect-ratio: 16 / 9; border-radius: 5px; }
a { display: inline-block; margin-top: .4rem; font-size: .8rem; }
.media-message { background: #fff3d5; padding: 1rem; line-height: 1.4; }
</style>
