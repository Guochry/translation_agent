import test from 'node:test';
import assert from 'node:assert/strict';
import { comparisonRated, normalizeComparison, resetComparison } from '../../src/assets/js/manga-comparison-util.js';

const scores = ['fidelity_score', 'presentation_score'].map(name => ({ name, min: 0, max: 100, step: 5 }));
const makeHit = () => ({ candidates: ['agent', 'baseline'].map(id => ({ id, fidelity_score: 0, presentation_score: 100,
    translation_regions: [{ id: `${id}:1`, target: 'Hello', quality_score: 0, presentation_score: 0, edits: [{ category: 'error', id: 1, output_idx: [[0, 2]] }] }] })) });

test('completion includes both candidates, accepts zero, rejects unfinished/off-step scores', () => {
    const hit = makeHit();
    assert.equal(comparisonRated(hit, scores), true);
    hit.candidates[1].translation_regions[0].quality_score = null;
    assert.equal(comparisonRated(hit, scores), false);
    hit.candidates[1].translation_regions[0].quality_score = 5;
    hit.candidates[1].fidelity_score = 12;
    assert.equal(comparisonRated(hit, scores), false);
    assert.equal(comparisonRated({ candidates: [hit.candidates[0]] }, scores), false);
});

test('normalization retains annotations and zero while clearing invalid imported scores', () => {
    const hit = makeHit();
    hit.candidates[1].fidelity_score = 101;
    hit.candidates[1].translation_regions[0].quality_score = 12;
    normalizeComparison(hit, scores);
    assert.equal(hit.candidates[0].fidelity_score, 0);
    assert.equal(hit.candidates[0].translation_regions[0].edits.length, 1);
    assert.equal(hit.candidates[1].fidelity_score, null);
    assert.equal(hit.candidates[1].translation_regions[0].quality_score, null);
});

test('reset clears ratings and errors for both systems while preserving content and identity', () => {
    const hit = makeHit();
    resetComparison(hit, scores);
    for (const candidate of hit.candidates) {
        assert.equal(candidate.fidelity_score, null);
        assert.equal(candidate.presentation_score, null);
        assert.equal(candidate.translation_regions[0].quality_score, null);
        assert.equal(candidate.translation_regions[0].presentation_score, null);
        assert.deepEqual(candidate.translation_regions[0].edits, []);
        assert.equal(candidate.translation_regions[0].target, 'Hello');
    }
    assert.deepEqual(hit.candidates.map(c => c.id), ['agent', 'baseline']);
    assert.equal(comparisonRated(hit, scores), false);
});


test('old quality ratings survive migration while missing presentation remains unfinished', () => {
    const hit = makeHit();
    delete hit.candidates[0].translation_regions[0].presentation_score;
    normalizeComparison(hit, scores);
    assert.equal(hit.candidates[0].translation_regions[0].quality_score, 0);
    assert.equal(hit.candidates[0].translation_regions[0].presentation_score, null);
    assert.equal(comparisonRated(hit, scores), false);
});
