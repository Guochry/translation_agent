import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { restoreBookAnnotations, validateBookDataset } from '../../src/assets/js/book-util.js';
import { cloneSubtitleData as clone, resetSubtitleClip, startSubtitlePostEdit, subtitleClipRated } from '../../src/assets/js/subtitle-util.js';

const data = JSON.parse(fs.readFileSync(new URL('../../public/data/demo/book_multilingual.json', import.meta.url)));
const languages = ['ar', 'hi', 'ka', 'ru', 'vi', 'zh-CN'];

test('published fables align by source and candidate order across languages', () => {
    validateBookDataset(data, languages);
    const originals = data.filter(hit => hit.language === 'ar');
    assert.equal(originals.length, 197);
    for (const language of languages) {
        const rows = data.filter(hit => hit.language === language);
        assert.equal(rows.length, originals.length);
        for (const [i, hit] of rows.entries()) {
            assert.equal(hit.source_index, i);
            assert.equal(hit.source, originals[i].source);
            assert.deepEqual(hit.candidates.map(c => c.id), originals[i].candidates.map(c => c.id));
        }
    }
    assert(data.some(hit => hit.language === 'ka' && hit.candidates.some(c => !c.available)));
});

test('book import restores scores, optional flags and draft origin on canonical content', () => {
    const original = data.find(hit => hit.language === 'ka' && hit.candidates.some(c => !c.available));
    const saved = clone(original);
    for (const c of saved.candidates.filter(c => c.available)) {
        c.translation_regions[0].quality_score = 0;
        c.translation_regions[0].presentation_score = 80;
    }
    const selected = saved.candidates.find(c => c.available);
    selected.annotation_issue = { category: 'omission', note: 'Missing the moral.' };
    const edited = startSubtitlePostEdit(saved, selected.id);
    const [restored] = restoreBookAnnotations(data, [edited]);
    assert.equal(subtitleClipRated(restored), true);
    assert.deepEqual(restored.post_edit_origin, edited.post_edit_origin);
    assert.deepEqual(restored.candidates.find(c => c.id === selected.id).annotation_issue, selected.annotation_issue);
    const reset = resetSubtitleClip(restored);
    assert.equal(subtitleClipRated(reset), false);
    assert.equal(reset.post_edit, '');
    selected.translation_regions[0].target += ' changed';
    assert.throws(() => restoreBookAnnotations(data, [saved]), /different book content/);
    const changed = clone(original);
    changed.source += ' changed';
    assert.throws(() => restoreBookAnnotations(data, [changed]), /different book content/);
});
