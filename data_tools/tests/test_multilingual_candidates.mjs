import test from 'node:test';
import assert from 'node:assert/strict';
import {comparisonRated,comparisonContentMatches,restoreComparisonAnnotations,resetComparison} from '../../src/assets/js/manga-comparison-util.js';
import {multilingualPageRated,normalizeMultilingualScores,validateMultilingualData} from '../../src/assets/js/manga-multilingual-util.js';
const config={scores:['fidelity_score','presentation_score'].map(name=>({name,min:0,max:100,step:5}))};
const makeHit=()=>({id:'comparison:en:page',language:'en',page_key:'book/ja/004.jpg',original_image:'original.jpg',metadata:{original_sha256:'original'},
    candidates:['baseline','qwen','gemma','cohere','gpt','translation'].map(id=>({id,available:true,translated_image:`${id}.webp`,fidelity_score:0,presentation_score:100,metadata:{translated_sha256:id},
        translation_regions:[{id:'r1',source:'日本語',target:`${id} text`,quality_score:0,presentation_score:100,edits:[]}]}))});

test('six candidates require independent scores, unavailable outputs are skipped rather than scored zero',()=>{
    const hit=makeHit();assert.equal(multilingualPageRated(hit,config),true);
    hit.candidates[5].translation_regions[0].presentation_score=null;
    assert.equal(comparisonRated(hit,config.scores),false);
    hit.candidates[5].available=false;assert.equal(comparisonRated(hit,config.scores),true);
    hit.candidates.forEach(c=>c.available=false);assert.equal(comparisonRated(hit,config.scores),false);
    assert.equal(comparisonRated({candidates:{}},config.scores),false);
});
test('comparison imports reject reordered, substituted, or modified candidate content',()=>{
    const original=makeHit();assert.equal(validateMultilingualData([makeHit()],[original],['en']),true);
    for(const mutate of [h=>h.candidates.reverse(),h=>h.candidates.pop(),h=>h.candidates[0].metadata.translated_sha256='changed',
        h=>h.candidates[0].translation_regions[0].target='changed',h=>h.candidates[0].available=false]){
        const hit=makeHit();mutate(hit);assert.equal(comparisonContentMatches(hit,original),false);
        assert.throws(()=>validateMultilingualData([hit],[original],['en']));
    }
});
test('import copies annotations onto canonical Japanese sources and preserves missing text',()=>{
    const original=makeHit(),saved=makeHit();saved.candidates[0].translation_regions[0].source='tampered';
    saved.candidates[0].translation_regions[0].edits=[{category:'strength',id:1,output_idx:[[0,4]]}];
    delete saved.candidates[1].translation_regions[0].presentation_score;
    const restored=restoreComparisonAnnotations(original,saved,config.scores);
    assert.equal(restored.candidates[0].translation_regions[0].source,'日本語');
    assert.equal(restored.candidates[0].translation_regions[0].edits[0].category,'strength');
    assert.equal(restored.candidates[1].translation_regions[0].quality_score,0);
    assert.equal(restored.candidates[1].translation_regions[0].presentation_score,null);
    const missing=makeHit();missing.candidates[0].translation_regions=null;
    normalizeMultilingualScores(missing,config);assert.equal(multilingualPageRated(missing,config),false);
    resetComparison(restored,config.scores);assert.ok(restored.candidates.every(c=>c.fidelity_score===null&&c.translation_regions.every(r=>r.quality_score===null&&r.presentation_score===null&&r.edits.length===0)));
});
