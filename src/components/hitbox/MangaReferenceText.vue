<script>
export default { props: ['references', 'japanese'] }
</script>
<template>
    <section class="human-references" aria-label="Human reference text">
        <h3>Human reference text</h3>
        <ol v-if="references?.length" class="reference-pairs">
            <li v-for="(text, index) in references" :key="index">
                <span class="reference-number">{{ index + 1 }}</span>
                <div class="reference-pair-text">
                    <span class="reference-language">Japanese</span>
                    <p lang="ja">{{ japanese?.[index] || 'Japanese text unavailable' }}</p>
                    <span class="reference-language">English reference</span>
                    <p lang="en">{{ text }}</p>
                </div>
            </li>
        </ol>
        <p v-else>No reference text for this page.</p>
    </section>
</template>
<style scoped>
h3 { margin: 0 0 .5rem; font-size: 1rem; }
.reference-pairs { list-style: none; margin: 0; padding: 0; }
li { display: flex; align-items: flex-start; gap: .7rem; padding: 1rem 0; border-bottom: 1px solid #e0e6ee; }
li:last-child { border-bottom: 0; }
.reference-number { flex: 0 0 1.6rem; text-align: center; border-radius: 50%; padding: .2rem 0; background: #e7edf5; color: #45617e; font-size: .8rem; }
.reference-pair-text { min-width: 0; }
.reference-language { color: #64758a; font-size: .75rem; font-weight: 600; }
p { margin: .3rem 0 .75rem; line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }
p:last-child { margin-bottom: 0; }
</style>
