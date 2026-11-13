import test from 'node:test';
import assert from 'node:assert/strict';
import {regionSpans,labelRegionSpan} from '../../src/assets/js/manga-span-util.js';
const makeRegion=()=>({target:'A good translation',quality_score:80,presentation_score:35,edits:[]});

test('all three span categories persist independently without changing region scores',()=>{
    let region=makeRegion();
    region=labelRegionSpan(region,0,1,'okay');
    region=labelRegionSpan(region,2,6,'strength');
    region=labelRegionSpan(region,7,18,'error');
    assert.deepEqual(regionSpans(region).map(s=>s.category),['okay','strength','error']);
    assert.deepEqual(region.edits.map(e=>e.id),[1,2,3]);
    assert.equal(region.quality_score,80);assert.equal(region.presentation_score,35);
});
test('exact spans can be relabeled; partial overlaps are rejected without losing annotations',()=>{
    let region=labelRegionSpan(makeRegion(),2,6,'error');
    region=labelRegionSpan(region,2,6,'strength');
    assert.equal(region.edits.length,1);assert.equal(region.edits[0].category,'strength');
    assert.throws(()=>labelRegionSpan(region,3,8,'okay'),/overlapping/);
    assert.equal(region.edits[0].category,'strength');
});
test('legacy error spans still load and invalid ranges do not annotate',()=>{
    const region={...makeRegion(),edits:[{category:'error',id:1,output_idx:[[2,6],[-1,3],[0,100]]}]};
    assert.equal(regionSpans(region).length,1);
    assert.equal(labelRegionSpan(region,0,1,'unknown'),region);
    assert.equal(labelRegionSpan(region,1,2,'okay'),region);
});
