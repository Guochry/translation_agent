<script>
export default {
    props: ['hit'],
    data() {
        return {
            image_errors: { original: false, translated: false },
            reference_heading_id: `manga-references-${this.$.uid}`
        }
    },
    computed: {
        metadata() {
            return this.hit.metadata || {}
        },
        original_url() {
            return this.image_url(this.hit.original_image)
        },
        translated_url() {
            return this.image_url(this.hit.translated_image)
        },
        image_panels() {
            return [
                { name: 'original', label: 'Original Japanese manga', url: this.original_url },
                { name: 'translated', label: 'Translated manga', url: this.translated_url }
            ]
        },
        reference_texts() {
            return Array.isArray(this.hit.reference_texts) ? this.hit.reference_texts : []
        }
    },
    watch: {
        original_url() { this.image_errors.original = false },
        translated_url() { this.image_errors.translated = false }
    },
    methods: {
        image_url(path) {
            if (typeof path !== 'string' || !path.trim()) return null
            if (/^(https?:)?\/\//i.test(path)) return path
            if (/^[a-z][a-z\d+.-]*:/i.test(path)) return null
            return `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`
        }
    }
}
</script>

<template>
    <section class="manga-comparison" aria-label="Manga translation comparison">
        <header class="manga-page-heading">
            <h2>{{ metadata.book_title || 'Manga translation' }}</h2>
            <span v-if="metadata.page_index != null">Page {{ metadata.page_index }}</span>
        </header>
        <div class="manga-image-grid">
            <figure v-for="panel in image_panels" :key="panel.name" class="manga-image-panel">
                <figcaption>
                    <h3>{{ panel.label }}</h3>
                    <a v-if="panel.url" :href="panel.url" target="_blank" rel="noopener noreferrer" :aria-label="`Open ${panel.name} image at full size`">Open full-size image</a>
                </figcaption>
                <a v-if="panel.url && !image_errors[panel.name]" :href="panel.url" target="_blank" rel="noopener noreferrer" :aria-label="`Enlarge ${panel.name} manga`">
                    <img
                        :key="panel.url"
                        :src="panel.url"
                        :alt="`${panel.label}${metadata.book_title ? `: ${metadata.book_title}` : ''}${metadata.page_index != null ? `, page ${metadata.page_index}` : ''}`"
                        @error="image_errors[panel.name] = true"
                    />
                </a>
                <p v-else class="manga-image-error" role="status">
                    {{ panel.url ? `Could not load the ${panel.name} image.` : `The ${panel.name} image is unavailable.` }}
                </p>
            </figure>
        </div>
        <section class="manga-references" :aria-labelledby="reference_heading_id">
            <h3 :id="reference_heading_id">English reference translation</h3>
            <ol v-if="reference_texts.length">
                <li v-for="(text, index) in reference_texts" :key="index">{{ text }}</li>
            </ol>
            <p v-else class="manga-empty-reference">No reference text for this page</p>
        </section>
    </section>
</template>

<style scoped>
.manga-page-heading {
    clear: both;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.5rem 1rem;
    margin-bottom: 1rem;
}
.manga-page-heading h2 { margin: 0; font-size: 1.3rem; }
.manga-page-heading span { color: #555; }
.manga-image-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.manga-image-panel { margin: 0; min-width: 0; }
.manga-image-panel figcaption { margin-bottom: 0.75rem; }
.manga-image-panel h3 { font-size: 1.1rem; margin: 0 0 0.35rem; }
.manga-image-panel a { color: #245ba0; }
.manga-image-panel img { display: block; width: 100%; height: auto; border: 1px solid #ddd; }
.manga-image-error { padding: 1.5rem; border: 1px solid #d5aaaa; background: #fff4f4; color: #782c2c; }
.manga-references { margin-top: 1.5rem; border-top: 1px solid #ddd; padding-top: 1rem; }
.manga-references h3 { margin: 0 0 0.75rem; font-size: 1.1rem; }
.manga-references ol { margin: 0; padding-left: 1.75rem; }
.manga-references li { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.5; margin-bottom: 0.6rem; padding-left: 0.25rem; }
.manga-empty-reference { margin-bottom: 0; color: #555; }
@media (max-width: 700px) {
    .manga-image-grid { grid-template-columns: minmax(0, 1fr); gap: 1.5rem; }
}
</style>
