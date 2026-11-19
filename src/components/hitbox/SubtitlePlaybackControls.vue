<script setup>
defineProps({ playing: Boolean, currentTime: Number, duration: Number, volume: Number, muted: Boolean, ready: Boolean, fullscreen: Boolean, canFullscreen: Boolean });
defineEmits(['toggle-play', 'restart', 'seek', 'volume', 'toggle-mute', 'fullscreen']);
function time(value) {
    const seconds = Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}
</script>
<template>
    <div class="subtitle-playback-controls" role="group" aria-label="Video playback controls">
        <input class="video-progress" type="range" min="0" :max="duration || 0" step="0.01" :value="currentTime || 0"
            :disabled="!ready" aria-label="Video progress" :aria-valuetext="`${time(currentTime)} of ${time(duration)}`"
            @input="$emit('seek', Number($event.target.value))" />
        <div class="playback-buttons">
            <button type="button" :disabled="!ready" :aria-label="playing ? 'Pause video' : 'Play video'" @click="$emit('toggle-play')">{{ playing ? 'Pause' : 'Play' }}</button>
            <button type="button" :disabled="!ready" aria-label="Restart video" @click="$emit('restart')">Replay</button>
            <span class="video-time" aria-label="Video time">{{ time(currentTime) }} / {{ time(duration) }}</span>
            <button type="button" :aria-label="muted || volume === 0 ? 'Unmute video' : 'Mute video'" @click="$emit('toggle-mute')">{{ muted || volume === 0 ? 'Unmute' : 'Mute' }}</button>
            <input class="video-volume" type="range" min="0" max="1" step="0.05" :value="muted ? 0 : volume" aria-label="Video volume" @input="$emit('volume', Number($event.target.value))" />
            <button v-if="canFullscreen" class="fullscreen-button" type="button" :aria-label="fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'" @click="$emit('fullscreen')">{{ fullscreen ? 'Exit fullscreen' : 'Fullscreen' }}</button>
        </div>
    </div>
</template>
<style scoped>
.subtitle-playback-controls { box-sizing: border-box; width: 100%; background: #f6f8fb; border: 1px solid #dbe0e8; border-radius: 0 0 5px 5px; padding: .6rem .7rem; color: #202735; }
.video-progress { display: block; width: 100%; margin: 0 0 .5rem; accent-color: #245ba0; cursor: pointer; }
.playback-buttons { display: flex; flex-wrap: wrap; align-items: center; gap: .45rem; }
button { padding: .35rem .55rem; border: 1px solid #b7bec9; border-radius: 4px; background: white; color: inherit; cursor: pointer; font: inherit; font-size: .8rem; }
button:disabled, input:disabled { cursor: default; opacity: .45; }
.video-time { font-size: .8rem; white-space: nowrap; font-variant-numeric: tabular-nums; }
.video-volume { width: 65px; max-width: 20%; accent-color: #245ba0; }
.fullscreen-button { margin-left: auto; }
:focus-visible { outline: 2px solid #245ba0; outline-offset: 2px; }
</style>
