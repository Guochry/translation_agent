import test from 'node:test';
import assert from 'node:assert/strict';
import { multilingualPageRated, normalizeMultilingualScores, validateMultilingualData, mangaImageUrl } from '../../src/assets/js/manga-multilingual-util.js';
const config = { scores: ['fidelity_score', 'presentation_score'].map(name => ({name, min: 0, max: 100, step: 5})) };
const makeHit = (language = 'en') => ({ id: `${language}:book:004`, page_key: 'book/ja/004.jpg', language,
    original_image: 'original.jpg', translated_image: `${language}.jpg`, fidelity_score: 0, presentation_score: 100,
    metadata: {original_sha256:'source-hash', translated_sha256:`${language}-hash`},
    translation_regions: [{id:`${language}:1`, target: language === 'ar' ? 'مرحبا' : 'Hello', quality_score: 0, presentation_score: 0, edits: []}] });

test('zero is complete, missing extraction is unfinished, invalid scores are cleared', () => {
    const hit = makeHit(); assert.equal(multilingualPageRated(hit, config), true);
    hit.translation_regions = null; assert.equal(multilingualPageRated(hit, config), false);
    hit.translation_regions = []; assert.equal(multilingualPageRated(hit, config), true);
    hit.fidelity_score = 12; normalizeMultilingualScores(hit, config);
    assert.equal(hit.fidelity_score, null); assert.equal(multilingualPageRated(hit, config), false);
});
test('imports retain language identity, reject mixed or modified content, support partial languages', () => {
    const canonical = [makeHit(), makeHit('ar')];
    assert.equal(validateMultilingualData([makeHit('ar')], canonical, ['en','ar']), true);
    assert.throws(() => validateMultilingualData([makeHit(),makeHit()], canonical, ['en','ar']));
    for (const mutate of [h => h.language='ar', h => h.page_key='other', h => h.translation_regions[0].target='changed',
        h => h.metadata.translated_sha256='changed', h => h.translation_regions=null]) {
        const hit = makeHit(); mutate(hit);
        assert.throws(() => validateMultilingualData([hit], canonical, ['en','ar']));
    }
});
test('asset resolver uses local bytes in dev and external image hosting in production', () => {
    const options = {baseUrl:'/translation_agent/', externalPrefix:'evaluation_assets/', externalBase:'https://raw.githubusercontent.com/owner/repo/main/evaluation_assets/'};
    assert.equal(mangaImageUrl('evaluation_assets/sample/en/a.jpg', options), '/translation_agent/evaluation_assets/sample/en/a.jpg');
    assert.equal(mangaImageUrl('evaluation_assets/sample/en/a.jpg', {...options,useExternal:true}), 'https://raw.githubusercontent.com/owner/repo/main/evaluation_assets/sample/en/a.jpg');
    assert.equal(mangaImageUrl('data/old.jpg', {...options,useExternal:true}), '/translation_agent/data/old.jpg');
    assert.equal(mangaImageUrl('javascript:alert(1)', options), null);
});


test('region presentation is required independently and migration preserves quality and spans', () => {
    const hit=makeHit();
    delete hit.translation_regions[0].presentation_score;
    hit.translation_regions[0].edits=[{category:'strength',id:1,output_idx:[[0,2]]}];
    normalizeMultilingualScores(hit,config);
    assert.equal(hit.translation_regions[0].quality_score,0);
    assert.equal(hit.translation_regions[0].presentation_score,null);
    assert.equal(multilingualPageRated(hit,config),false);
    assert.equal(hit.translation_regions[0].edits[0].category,'strength');
    hit.translation_regions[0].presentation_score=0;
    assert.equal(multilingualPageRated(hit,config),true);
});
