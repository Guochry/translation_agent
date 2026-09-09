# Continue round-0 strength annotations with Hy models

Dataset: `public/data/strength_geyang_round_0_with_hy.json`.

- Exactly the original 50 items in the original order (25 Havoc in Heaven,
  25 others).
- Candidates 1–6 are copied unchanged from Geyang's round-0 annotation export,
  including the human reference, scores, and strength annotations.
- Candidate 7: `hy-mt2-7b`; Candidate 8: `hy-mt2-30b-a3b`.
  Their scores are blank and their span lists are empty.
- Improved translations and accumulated annotation times are preserved.
  The timer continues from the saved time, not zero.
- This is a continuation dataset with Geyang's annotations visible, not a
  fresh, independent annotation assignment. Use the strength task, not ESA.
  Original data files and default datasets remain unchanged.

After committing/pushing to the GitHub Pages repository and successful deployment:

https://guochry.github.io/translation_agent/demo_translation_strength?d=data/strength_geyang_round_0_with_hy.json

Local Vite URL:

http://localhost:5173/demo_translation_strength?d=data/strength_geyang_round_0_with_hy.json

Download the JSON after annotating to retain old and new annotations together.
The hosted dataset is a starting snapshot; browser edits do not update it.
Reloading that URL starts from the hosted snapshot. Upload your latest downloaded
JSON to resume subsequent work.

Regenerate from the parent project containing `annotation_data` and `data/llm_infer/res`:

```bash
python thresh/data_tools/add_hy_candidates.py
```

Matching uses exact title + source language + source text. Duplicate identities,
missing translations, or mismatched human references stop generation. The script
verifies that every original candidate and every item-level field is unchanged.
No inference jobs or other aggregation/sampling scripts need to be rerun.
