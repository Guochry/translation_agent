import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { bookCandidateDisplayText, restoreBookAnnotations, validateBookDataset } from '../../src/assets/js/book-util.js';
import { cloneSubtitleData as clone, resetSubtitleClip, startSubtitlePostEdit, subtitleClipRated } from '../../src/assets/js/subtitle-util.js';

const data = JSON.parse(fs.readFileSync(new URL('../../public/data/demo/book_multilingual.json', import.meta.url)));
const languages = ['ar', 'hi', 'ka', 'ru', 'vi', 'zh-CN'];

test('Chinese reference reflows single and double body breaks without shifting spans', () => {
    const raw = '标题\n\n第一段换\n行，中间又换\n\n行继续。';
    const candidate = { id: 'human_reference', translation_regions: [{ target: raw }] };
    const displayed = bookCandidateDisplayText(candidate);
    assert.equal(displayed, '标题\n\n第一段换\u200b行，中间又换\u200b\u200b行继续。');
    assert.equal(displayed.length, raw.length);
    assert.equal(candidate.translation_regions[0].target, raw);
    assert.equal(bookCandidateDisplayText({ ...candidate, id: 'cohere' }), raw);
});

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
            const reference = hit.candidates.find(c => c.id === 'human_reference');
            assert.deepEqual(hit.candidates.filter(c => c !== reference).map(c => c.id), originals[i].candidates.map(c => c.id));
            if (language === 'zh-CN') {
                assert.equal(reference.available, true);
                assert.equal(reference.model, null);
                assert.equal(reference.metadata.translation_type, 'human_reference');
            } else {
                assert.equal(reference, undefined);
            }
        }
    }
    assert(data.some(hit => hit.language === 'ka' && hit.candidates.some(c => !c.available)));
});

test('old Chinese exports restore by candidate ID and update post-edit labels after adding the reference', () => {
    const canonical = data.find(hit => hit.language === 'zh-CN' && hit.candidates[0].id === 'human_reference');
    const saved = clone(canonical);
    saved.candidates.shift();
    const candidate = saved.candidates[0];
    candidate.translation_regions[0].quality_score = 75;
    const draft = startSubtitlePostEdit(saved, candidate.id);
    assert.equal(draft.post_edit_origin.candidate_label, 'Translation A');
    const [restored] = restoreBookAnnotations(data, [draft]);
    assert.equal(restored.candidates[0].id, 'human_reference');
    assert.equal(restored.candidates[0].translation_regions[0].quality_score, null);
    assert.equal(restored.candidates[1].translation_regions[0].quality_score, 75);
    assert.equal(restored.post_edit_origin.candidate_id, candidate.id);
    assert.equal(restored.post_edit_origin.candidate_label, 'Translation B');
    assert.deepEqual(restoreBookAnnotations(data, [restored]), [restored]);
    draft.candidates.reverse();
    assert.throws(() => restoreBookAnnotations(data, [draft]), /different book content/);
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

test('old book exports keep ratings and leave newly available outputs unrated', () => {
    const original = data.find(hit => hit.language === 'vi');
    const saved = clone(original);
    const missing = saved.candidates.find(c => c.id === 'cohere');
    missing.available = false;
    missing.translation_regions = [];
    const rated = saved.candidates.find(c => c.available);
    rated.translation_regions[0].quality_score = 85;
    const [restored] = restoreBookAnnotations(data, [saved]);
    const added = restored.candidates.find(c => c.id === 'cohere');
    assert.equal(added.available, true);
    assert.equal(added.translation_regions[0].quality_score, null);
    assert.equal(restored.candidates.find(c => c.id === rated.id).translation_regions[0].quality_score, 85);
    missing.translation_regions = [{ id: 'wrong', target: 'Unexpected output' }];
    assert.throws(() => restoreBookAnnotations(data, [saved]), /different book content/);
});
