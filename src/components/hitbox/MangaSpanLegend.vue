<script>
export default { props: ['modelValue'], emits: ['update:modelValue'] }
</script>
<template>
    <div class="span-legend" role="group" aria-label="Span label">
        <span>Highlight as:</span>
        <button v-for="category in ['strength', 'okay', 'error']" :key="category" type="button"
            :class="`span-choice-${category}`" :aria-pressed="modelValue === category" @click="$emit('update:modelValue', category)">
            {{ category === 'okay' ? 'Okay' : category === 'strength' ? 'Strength' : 'Error' }}
        </button>
    </div>
</template>
<style scoped>
.span-legend { position: sticky; top: 0; z-index: 1; background: #fafafa; padding: .4rem 0; display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; font-size: .85rem; margin: .6rem 0; }
button { padding: .3rem .5rem; border: 1px solid #aaa; border-radius: 4px; cursor: pointer; background: #fff; }
button[aria-pressed=true] { outline: 2px solid #555; outline-offset: 1px; font-weight: 600; }
.span-choice-strength { background: #d9f2df; }
.span-choice-okay { background: #fff1bd; }
.span-choice-error { background: #ffe0df; }
</style>
