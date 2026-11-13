<script setup>
import { mangaImageUrl } from '../../assets/js/manga-multilingual-util.js';
import MangaTextRegion from './MangaTextRegion.vue';
</script>

<script>
export default {
    props: ['hit', 'text_evaluation', 'update_region', 'config'],
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
                { name: 'translated', label: this.hit.language_label ? `${this.hit.language_label} translation` : 'Translated manga', url: this.translated_url }
            ]
        },
        reference_texts() {
            return Array.isArray(this.hit.reference_texts) ? this.hit.reference_texts : []
        },
        reference_texts_ja() {
            return Array.isArray(this.hit.reference_texts_ja) ? this.hit.reference_texts_ja : null
        },
        translation_regions() {
            return Array.isArray(this.hit.translation_regions) ? this.hit.translation_regions : null
        }
    },
    watch: {
        original_url() { this.image_errors.original = false },
        translated_url() { this.image_errors.translated = false }
    },
    methods: {
        image_url(path) {
            return mangaImageUrl(path, {
                baseUrl: import.meta.env.BASE_URL,
                externalPrefix: this.config?.external_asset_prefix,
                externalBase: this.config?.external_asset_base,
                useExternal: import.meta.env.PROD
            })
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
        <div class="manga-layout" :class="{ 'has-text-evaluation': text_evaluation }">
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
        <aside class="manga-text-panel" :aria-label="text_evaluation ? 'Text translation evaluation' : 'Reference text'">
        <component :is="text_evaluation ? 'details' : 'div'" class="manga-reference-disclosure" :open="text_evaluation ? !config?.manga_multilingual : undefined">
        <summary v-if="text_evaluation">Human reference text</summary>
        <section class="manga-references" :aria-labelledby="reference_heading_id">
            <h3 :id="reference_heading_id">{{ reference_texts_ja ? 'Japanese source and English reference' : 'English reference translation' }}</h3>
            <ol v-if="reference_texts.length">
                <li v-for="(text, index) in reference_texts" :key="index">
                    <div class="manga-reference-pair" :class="{ 'has-source': reference_texts_ja !== null }">
                        <div v-if="reference_texts_ja !== null" class="manga-reference-source">
                            <span class="manga-reference-label">Japanese source</span>
                            <p v-if="typeof reference_texts_ja[index] === 'string' && reference_texts_ja[index].trim()" class="manga-reference-text" lang="ja">{{ reference_texts_ja[index] }}</p>
                            <p v-else class="manga-reference-unavailable" aria-label="Japanese source text unavailable">Japanese source text unavailable</p>
                        </div>
                        <div class="manga-reference-english">
                            <span class="manga-reference-label">English reference</span>
                            <p class="manga-reference-text" lang="en">{{ text }}</p>
                        </div>
                    </div>
                </li>
            </ol>
            <p v-else class="manga-empty-reference">No reference text for this page</p>
        </section>
        </component>
        <section v-if="text_evaluation" class="manga-generated-regions" aria-label="Generated translations">
            <h3>Generated translations</h3>
            <p class="manga-region-guide">Score accuracy and natural wording: <strong>0–100, steps of 5</strong>. Highlight errors to mark them.</p>
            <p v-if="translation_regions === null" class="manga-empty-reference">Generated text is unavailable for this page.</p>
            <p v-else-if="!translation_regions.length" class="manga-empty-reference">No generated text for this page.</p>
            <MangaTextRegion
                v-for="(region, index) in translation_regions || []"
                :key="`${index}-${region.id}`"
                :region="region"
                :region_index="index"
                :update_region="update_region"
                :language="hit.language"
            />
        </section>
        </aside>
        </div>
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
.manga-layout.has-text-evaluation { display: grid; grid-template-columns: minmax(0, 2fr) minmax(340px, 1fr); gap: 1rem; align-items: start; }
.has-text-evaluation .manga-text-panel { min-width: 0; max-height: 80vh; overflow: auto; padding: 1rem; border: 1px solid #ddd; border-radius: 4px; background: #fafafa; }
.has-text-evaluation .manga-references { margin-top: 0; padding-top: 0; border-top: 0; }
.has-text-evaluation .manga-reference-pair.has-source { grid-template-columns: minmax(0, 1fr); }
.manga-region-guide { font-size: .85rem; line-height: 1.4; color: #555; }
.manga-generated-regions { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #ddd; }
.manga-generated-regions h3 { margin: 0 0 0.75rem; font-size: 1.1rem; }
.manga-reference-disclosure summary { cursor: pointer; font-size: 0.9rem; font-weight: 600; margin-bottom: 0.85rem; }
.manga-image-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.manga-image-panel { margin: 0; min-width: 0; }
.manga-image-panel figcaption { margin-bottom: 0.75rem; }
.manga-image-panel h3 { font-size: 1.1rem; margin: 0 0 0.35rem; }
.manga-image-panel a { color: #245ba0; }
.manga-image-panel img { box-sizing: border-box; display: block; width: 100%; height: auto; border: 1px solid #ddd; }
.manga-image-error { padding: 1.5rem; border: 1px solid #d5aaaa; background: #fff4f4; color: #782c2c; }
.manga-references { margin-top: 1.5rem; border-top: 1px solid #ddd; padding-top: 1rem; }
.manga-references h3 { margin: 0 0 0.75rem; font-size: 1.1rem; }
.manga-references ol { margin: 0; padding-left: 1.75rem; }
.manga-references li { overflow-wrap: anywhere; line-height: 1.5; margin-bottom: 0.8rem; padding-left: 0.25rem; }
.manga-reference-pair { display: grid; grid-template-columns: minmax(0, 1fr); gap: 0.75rem 1rem; padding-bottom: 0.8rem; border-bottom: 1px solid #eee; }
.manga-reference-pair.has-source { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.manga-reference-label { font-size: 0.8rem; font-weight: 600; color: #555; }
.manga-reference-text { white-space: pre-wrap; margin: 0.25rem 0 0; }
.manga-reference-unavailable { margin: 0.25rem 0 0; color: #666; font-style: italic; }
.manga-empty-reference { margin-bottom: 0; color: #555; }
@media (max-width: 1100px) {
    .manga-layout.has-text-evaluation { grid-template-columns: minmax(0, 1fr); }
    .has-text-evaluation .manga-text-panel { max-height: none; overflow: visible; }
}
@media (max-width: 700px) {
    .manga-image-grid { grid-template-columns: minmax(0, 1fr); gap: 1.5rem; }
    .manga-reference-pair.has-source { grid-template-columns: minmax(0, 1fr); }
}
</style>
