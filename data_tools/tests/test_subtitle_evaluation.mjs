import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { cloneSubtitleData as clone, validateSubtitleDataset, restoreSubtitleAnnotations, resetSubtitleClip,
    subtitleClipRated, subtitleCandidateRated, subtitleMediaUrl } from '../../src/assets/js/subtitle-util.js';
import { labelRegionSpan } from '../../src/assets/js/manga-span-util.js';
const data = JSON.parse(fs.readFileSync(new URL('../../public/data/demo/subtitle_multilingual.json', import.meta.url)));
const languages = ['en', 'vi', 'ka', 'ar', 'hi', 'ru'];

test('all 177 clips have consistent anonymous candidate order across six languages', () => {
    validateSubtitleDataset(data, languages);
    assert.equal(data.length, 177 * 6);
    assert.equal(data.flatMap(h => h.candidates).filter(c => c.available).length, 5660);
    for (const language of languages) {
        const hits = data.filter(h => h.language === language);
        assert.equal(hits.length, 177);
        for (let i = 0; i < 177; i++) {
            assert.equal(hits[i].clip_id, data[i].clip_id);
            assert.deepEqual(hits[i].candidates.filter(c => c.id !== 'human_reference').map(c => c.id), data[i].candidates.filter(c => c.id !== 'human_reference').map(c => c.id));
            assert.equal(hits[i].candidates.length, ['en', 'vi'].includes(language) ? 6 : 5);
            assert.equal(hits[i].source_language, 'zh');
        }
    }
});

test('zero counts; only the subtitle score pair is required; missing candidates excluded', () => {
    const hit = clone(data[0]);
    assert.equal(subtitleClipRated(hit), false);
    for (const c of hit.candidates) {
        for (const r of c.translation_regions) { r.quality_score = 60; r.presentation_score = 0; }
    }
    assert.equal(subtitleClipRated(hit), true);
    hit.candidates[0].translation_regions[0].presentation_score = 61;
    assert.equal(subtitleCandidateRated(hit.candidates[0]), false);
    hit.candidates[0].available = false;
    assert.equal(subtitleClipRated(hit), true);
    for (const c of hit.candidates) c.available = false;
    assert.equal(subtitleClipRated(hit), false);
});

test('upload restores scores, notes, bookmark and Unicode spans without crossing language/candidate', () => {
    const saved = clone(data.find(h => h.language === 'ar'));
    saved.bookmark = true;
    saved.candidates[0].comment = 'font too small';
    const region = saved.candidates[0].translation_regions[0];
    saved.candidates[0].translation_regions[0] = labelRegionSpan({ ...region, quality_score: 0, presentation_score: 60 }, 0, 3, 'strength');
    const [restored] = restoreSubtitleAnnotations(data, [saved]);
    assert.equal(restored.bookmark, true);
    assert.equal(restored.candidates[0].translation_regions[0].quality_score, 0);
    assert.equal(restored.candidates[0].comment, 'font too small');
    assert.equal(restored.candidates[0].translation_regions[0].edits[0].category, 'strength');
    assert.equal(restored.candidates[1].translation_regions[0].quality_score, null);
    assert.equal(data.find(h => h.id === saved.id).candidates[0].translation_regions[0].quality_score, null);
    const reset = resetSubtitleClip(restored);
    assert.equal(reset.candidates[0].translation_regions[0].edits.length, 0);
    assert.equal(reset.candidates[0].translation_regions[0].presentation_score, null);
    assert.equal(reset.bookmark, true);
});

test('uploads reject changed media, cue timing, language, model order, invalid scores/spans and duplicates', () => {
    for (const mutate of [
        h => { h.original_video += '-changed'; },
        h => { h.candidates[0].translated_video += '-changed'; },
        h => { h.candidates[0].metadata.render_identity += '-old-render'; },
        h => { h.candidates[0].metadata.video_bytes += 1; },
        h => { h.candidates[0].translation_regions[0].end_seconds += 1; },
        h => { h.candidates[0].translation_regions[0].source += 'x'; },
        h => { h.language = 'ar'; },
        h => { h.candidates.reverse(); },
        h => { h.candidates[0].translation_regions[0].quality_score = 62; },
        h => { h.candidates[0].translation_regions[0].edits = [{ category:'error', id:1, output_idx:[[0,99999]] }]; },
        h => { h.candidates[0].translation_regions[0].edits = [{ category:'error', id:1, output_idx:[[0,3]] }, { category:'strength', id:2, output_idx:[[1,4]] }]; },
    ]) {
        const hit = clone(data[0]); mutate(hit);
        assert.throws(() => restoreSubtitleAnnotations(data, [hit]));
    }
    assert.throws(() => restoreSubtitleAnnotations(data, [data[0], data[0]]));
});

test('video URLs use local media in dev and an external base in production', () => {
    const path = data[0].original_video;
    assert.equal(subtitleMediaUrl(path, { dev: true }), '/' + path);
    assert.equal(subtitleMediaUrl(path), '');
    assert.equal(subtitleMediaUrl(path, { mediaBase: 'https://example.org/media' }), 'https://example.org/media/original/430711.mp4');
    assert.equal(subtitleMediaUrl('https://example.org/video.mp4'), 'https://example.org/video.mp4');
});

test('English reference context is complete and older annotation exports retain their ratings', () => {
    const english = new Map(data.filter(h => h.language === 'en').map(h => [h.clip_id, h]));
    for (const hit of data) {
        for (const field of ['context_before_en', 'context_after_en']) {
            assert.deepEqual(hit[field], english.get(hit.clip_id)[field]);
            assert.equal(hit[field].length, hit[field.replace('_en', '')].length);
        }
    }
    const saved = clone(data[0]);
    delete saved.context_before_en;
    delete saved.context_after_en;
    saved.candidates[0].translation_regions[0].quality_score = 75;
    const [restored] = restoreSubtitleAnnotations(data, [saved]);
    assert.equal(restored.candidates[0].translation_regions[0].quality_score, 75);
    assert.deepEqual(restored.context_before_en, data[0].context_before_en);
    assert.deepEqual(restored.context_after_en, data[0].context_after_en);
    saved.context_before_en = ['Changed text in upload'];
    assert.deepEqual(restoreSubtitleAnnotations(data, [saved])[0].context_before_en, data[0].context_before_en);
    const incomplete = clone(data);
    incomplete[0].context_before_en.pop();
    assert.throws(() => validateSubtitleDataset(incomplete, languages), /English dialogue context/);
});

test('legacy clip scores are discarded without replacing the subtitle score pair', () => {
    const saved = clone(data[0]);
    saved.candidates[0].fidelity_score = 100;
    saved.candidates[0].presentation_score = 100;
    saved.candidates[0].translation_regions[0].quality_score = 65;
    saved.candidates[0].translation_regions[0].presentation_score = 0;
    const [result] = restoreSubtitleAnnotations(data, [saved]);
    assert.equal(Object.hasOwn(result.candidates[0], 'fidelity_score'), false);
    assert.equal(Object.hasOwn(result.candidates[0], 'presentation_score'), false);
    assert.equal(result.candidates[0].translation_regions[0].quality_score, 65);
    assert.equal(result.candidates[0].translation_regions[0].presentation_score, 0);
    assert.equal(subtitleCandidateRated(result.candidates[0]), true);
    assert.equal(subtitleClipRated(result), false);
    assert.equal(Object.hasOwn(resetSubtitleClip(saved).candidates[0], 'fidelity_score'), false);
});

test('human-reference candidates match the original references only in English and Vietnamese', () => {
    let count = 0;
    for (const hit of data) {
        const reference = hit.candidates.find(c => c.id === 'human_reference');
        if (!['en', 'vi'].includes(hit.language)) { assert.equal(reference, undefined); continue; }
        count++;
        assert.equal(reference.available, true);
        assert.equal(reference.metadata.translation_type, 'human_reference');
        assert.equal(reference.metadata.reference_field, hit.language);
        assert.equal(reference.metadata.model, null);
        const expected = hit.references.find(r => r.language === hit.language).text;
        assert.equal(reference.translation, expected);
        assert.equal(reference.translation_regions[0].target.replace(/\s+/g, ' ').trim(), expected.replace(/\s+/g, ' ').trim());
        assert.equal(reference.translation_regions[0].source, hit.source);
        const counterpart = data.find(h => h.clip_id === hit.clip_id && h.language === (hit.language === 'en' ? 'vi' : 'en'));
        assert.deepEqual(hit.candidates.map(c => c.id), counterpart.candidates.map(c => c.id));
    }
    assert.equal(count, 354);
    const positions = new Set(data.filter(h => h.language === 'en').map(h => h.candidates.findIndex(c => c.id === 'human_reference')));
    assert.equal(positions.size, 6);
});
