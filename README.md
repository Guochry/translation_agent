<div align="center">
    <img src="./public/img/logo.png" width="400" />
    <!-- <h3 style="margin: 0">thresh.tools: Fine-grained evaluation for text generation</h3> -->

[**Build an Interface**](https://thresh.tools) | [**Video Tutorial**](#quick_start) | [**Paper**](https://arxiv.org/abs/2308.06953)

<!-- | [**Paper**](https://arxiv.org/) -->
</div>
<br />
<div align="center">
    <img src="./public/img/github-banner.jpg" width="100%" style="max-width: 1000px" />
</div>

<!-- TODO ADD GIF DEMO HERE -->

------------------------------------------------

**thresh.tools** is a platform which makes it easy to create and share fine-grained annotation. It was written specifically for complex annotation of text generation (such as [**Scarecrow**](https://thresh.tools/scarecrow) or [**SALSA**](https://thresh.tools/salsa)) and built to be universal across annotation tasks, quickly customizable and easily deployable.

<a id="quick_start"></a>

## Quick Start
Visit [**thresh.tools/demo**](https://thresh.tools/?t=demo_start) for an explanation of how our interface creation works!

https://github.com/davidheineman/thresh/assets/9833172/6138408a-1650-42ec-8588-0affb5c98eb5

## Manga Translation Evaluation

The [manga template](./public/templates/demo/manga_translation.yml) shows one matched original Japanese manga page and translated image per task. A text sidebar beside the image pair contains human Japanese/English references from OpenMantra and separate cards for the agent's generated translation regions. Each page has two independent overall integer scores from **1 to 100**:

- **Fidelity:** Preservation of dialogue meaning and tone, story, characters, and original artwork. Intended replacement of Japanese lettering is allowed; unintended visual changes reduce fidelity.
- **Presentation:** Readability and visual polish, including typography, text placement, speech-balloon fit, and rendering artifacts.

Each generated-region card shows detected Japanese and the generated translation. Annotators can highlight errors in the generated translation, without severity labels, and assign that region a **text-quality score from 0 to 100 in steps of 5**. A score of **0** means meaning is lost or the translation is in the wrong language; **100** means fully accurate and natural English. Human references and generated regions are separate lists because region counts and boundaries can differ.

Scores start blank. Navigation retains ratings and highlights during the session. A page counts as fully rated once both overall scores and every generated-region quality score are filled; **0** is a valid text score and error highlights are optional. Pages with no generated regions need only the two overall scores. Download JSON at any point to save partial work and upload that file to resume. Reset clears both overall ratings, every region's quality score, and all error highlights for the current page.

After deploying this checkout with the existing GitHub Pages workflow, open:

[Manga Translation Evaluation](https://guochry.github.io/translation_agent/?i=templates/demo/manga_translation.yml&d=data/demo/manga_translation.json)

For local use, run `npm run dev` and open [the local task](http://localhost:5173/?i=templates/demo/manga_translation.yml&d=data/demo/manga_translation.json). The template is also available in the interface builder as **Manga Translation**.

### Prepare or refresh the manga data

From this repository, run the converter with its defaults:

```bash
python data_tools/prepare_manga_evaluation.py
```

The equivalent explicit command is:

```bash
python data_tools/prepare_manga_evaluation.py \
  --dataset-root ../data/manga/open-mantra-dataset \
  --rendered-results-root ../agent/manga_tryout/manga_agent/runs/fst_try/rendered_results \
  --results-root ../agent/manga_tryout/manga_agent/runs/fst_try \
  --run-id fst_try \
  --output-json public/data/demo/manga_translation.json \
  --assets-dir public/data/manga/fst_try
```

The converter matches pages by book and image filename stem using `annotation.json`; source filenames are zero-based while annotation page numbers are one-based. It preserves book order, ascending page numbers, and the exact Japanese and English reference text paired in annotation order. Empty Japanese annotations are preserved and shown as unavailable in the interface.

Generated text comes from the matched agent `result.json` files under `--results-root`, which defaults to the parent of `--rendered-results-root` when omitted. The converter validates matching page identities and rendered-image hashes before packaging the generated text. It uses valid agent reading-order information when present, otherwise the stored region order. Human references retain annotation order; neither list establishes independently verified manga reading order.

The current `fst_try` run produces **203 tasks across five manga**, with **1,501 human reference pairs** and **2,361 generated translation regions**. Eleven source pages have no rendered translation and are omitted. Five matched pages have no human reference text; four have no generated regions. Each list has its own empty state. The conversion report is saved beside the task JSON as `manga_translation.report.json`.

Matched originals and translated images are copied unchanged into `public/data/manga/fst_try/original/` and `translated/`, preserving their original image quality for evaluation. These public assets add approximately **204 MiB** and are bundled into the GitHub Pages build. Exported ratings retain page identity, image URLs, reference text, and metadata.

Run the converter checks with `python -m unittest discover -s data_tools/tests -v`.

The template enables `manga_evaluation: true` and `manga_text_evaluation: true`. Its root `scores` list defines only the two overall page scores. Task records contain `id`, `original_image`, `translated_image`, `reference_texts` (English), `reference_texts_ja` (Japanese, aligned by index), `metadata`, `fidelity_score`, `presentation_score`, and `translation_regions`.

Each `translation_regions` entry contains `id`, `source` (detected Japanese), `target` (generated translation), `bbox`, `kind`, nullable `quality_score`, and `edits`. Error edits use the existing shape: `category: "error"`, a numeric `id`, `annotation: null`, and `output_idx` character ranges local to that region's `target`, measured in JavaScript UTF-16 offsets. The root `edits` list stays empty; text cards manage their own error lists.

Uploaded older exports recover missing Japanese references and generated-region arrays from the currently loaded dataset while preserving saved page scores and bookmarks. Template and dataset loads revalidate the browser cache so new deployments can supply updated task settings and data. Existing text annotation templates retain their current format and `overall_score` setting.

Original images and reference annotations come from [OpenMantra](https://github.com/mantra-inc/open-mantra-dataset), described in *Towards Fully Automated Manga Translation* by Ryota Hinami, Shonosuke Ishiwatari, Kazuhiko Yasuda, and Yusuke Matsui (AAAI 2021). The upstream **Creative Commons Attribution-NonCommercial 4.0 International** license is included with the copied assets as [LICENSE.md](./public/data/manga/fst_try/LICENSE.md). Translated pages are generated outputs from the `fst_try` manga-agent run.

## Getting Started with `thresh.tools`

### Overview
`thresh.tools` can be used to [***customize***](#customize) a fine-grained typology, [***deploy***](#deploy) an interface with co-authors, annotators or the research community and [***manage***](#manage) fine-grained annotations using Python. We support each step of the fine-grained annotation lifecycle:
<div align="center">
    <img src="./public/img/lifecycle.png" width="100%" style="max-width: 1000px" />
</div>

### Interface Customization Tutorials
These tutorials show how to customize an interface for annotation on `thresh.tools`. 

| feature | tutorial | documentation |
|:--- | :--: |  :-- | 
| Edit Types | [🔗](https://thresh.tools/?t=demo_edit_types) | [**Adding Edits**](#demo_edit_types)
| Recursive Question Trees | [🔗](https://thresh.tools/?t=demo_question_trees) | [**Annotating with Recursive Structure**](#demo_question_trees)
| Custom Instructions | [🔗](https://thresh.tools/?t=demo_instructions) | [**Add Instructions**](#demo_instructions)
| Paragraph-level Annotation | [🔗](https://thresh.tools/?t=demo_paragraph) | [**Paragraph-level Annotation**](#demo_paragraph)
| Adjudication | [🔗](https://thresh.tools/?t=demo_adjudication) | [**Multi-interface Adjudication**](#demo_adjudication)
| Disable Features | [🔗](https://thresh.tools/?t=demo_disable) | --
| Sub-word Selection | [🔗](https://thresh.tools/?t=demo_tokenization) | [**Sub-word Selection**](#demo_tokenization)
| Multi-lingual Annotation | [🔗](https://thresh.tools/?t=demo_multilingual) | [**Multi-lingual Annotation**](#demo_multilingual)
| Crowdsource Deployment | [🔗](https://thresh.tools/?t=demo_crowdsource) | [**Deploy to Crowdsource Platforms**](#demo_crowdsource)

### Deploy & Manage Annotation Tutorials
These notebook tutorials show broader usage of `thresh` for deploying to annoation platforms and managing annotations in Python:

| description | tutorial |
|:--- | :--: |
| Load data using the `thresh` library | [**load_data.ipynb**](./notebook_tutorials/load_data.ipynb) |
| Deploy an interface to the Prolific platform | [**deploy_to_prolific.ipynb**](./notebook_tutorials/deploy_to_prolific.ipynb) |
| Use `tokenizers` to pre-process your dataset | [**subword_annotation.ipynb**](./notebook_tutorials/subword_annotation.ipynb) |

<a id="customize"></a>

## Customize an Interface

All interfaces consists of two elements the *typology* and the *data*. The typology defines your interface and data defines the examples to be annotated.

`<typology>.yml`:

```yaml
template_name: my_template
template_label: My First thresh.tools Template!
edits:
    ...
```

`<data>.json`:
```json
{
    "source": "...",
    "target": "..."
}
```

<a id="demo_edit_types"></a>

### Adding Edits [↗️](https://thresh.tools/?t=demo_edit_types)

The `edits` command defines a list of edits. Each edit can be one of these types:

| ![](./public/img/docs/edit_input_output.png) | ![](./public/img/docs/edit_multispan.png) | ![](./public/img/docs/edit_composite.png) |
| :--: | :--: | :--: | 
| `type: single_span` | `type: multi_span` | `type: composite` |

Additionally, the `enable_input` and `enable_output` commands are used to enable selecting the span on the source or target sentences respectively.

| ![](./public/img/docs/edit_input.png) | ![](./public/img/docs/edit_output.png) | ![](./public/img/docs/edit_input_output.png) |
|:--: | :--: | :--: |
| `enable_input: true` | `enable_output: true` | `enable_input: true` & `enable_output: true` |

To style your edits, the `icon` is any [**Font Awesome icon**](http://fontawesome.com/search?o=r&m=free) and `color` is the associated edit color. 

```yaml
edits:
  - name: edit_with_annotation
    label: "Custom Annotation"
    icon: fa-<icon>
    color: <red|orange|yellow|green|teal|blue>
    type: <single_span|multi_span|composite>
    enable_input: <true|false>
    enable_output: <true|false>
    annotation: ...
```

<a id="demo_question_trees"></a>

### Annotating with Recursive Structure [↗️](https://thresh.tools/?t=demo_question_trees)

Within each edit, the `annotation` command is used to specify the annotation questions for each edit. Using the `options` command, you can specify the question type:

| ![](./public/img/docs/question_binary.png) | ![](./public/img/docs/question_likert.png) | ![](./public/img/docs/question_text.png) |
| :--: | :--: | :--: | 
| `options: binary` | `options: likert-3` | `options: textbox` & `options: textarea` |

Qustions are structured as a tree, so if you list sub-questions under the `options` field, they will appear after the user has selected a certain annotation.

| ![](./public/img/docs/question_custom.png) | ![](./public/img/docs/question_multi.png) | ![](./public/img/docs/question_children.png) |
|:--: | :--: | :--: |
| List of children in `options` | Multiple questions in `options` | Nested sub-children in `options` |

```yaml
edits:
  - name: edit_with_annotation
    ...
    annotation:
    - name: simple_question
      question: "Can you answer this question?"
      options: <likert-3|binary|textbox|textarea>
    - name: grandparent_question
      question: "Which subtype question is important"
      options:
      - name: parent_question_1
        label: "Custom Parent Question"
        question: "Which subchild would you like to select"
        options:
      - name: child_1
        label: "Custom Child Option 1"
      - name: child_2
        label: "Custom Child Option 2"
        ...
      - name: parent_question_2
        label: "Pre-defined Parent Question"
        question: "Can you rate the span on a scale of 1-3?"
        options: <likert-3|binary|textbox|textarea>
      ...
  ...
```

<a id="demo_instructions"></a>

### Add Instructions [↗️](https://thresh.tools/?t=demo_instructions)

Using the `instructions` flag, you can add an instructions modal, or prepend the text above the interface using the `prepend_instructions` flag. Instructions are fomatted with [**Markdown**](https://www.markdownguide.org/cheat-sheet/).

<div align="center">
    <img src="./public/img/docs/instructions.png" width="400" />
</div>

```yaml
prepend_instructions: <true|false>
instructions: |
  Your instruction text in markdown format.
```

<a id="demo_paragraph"></a>

### Paragraph-level Annotation [↗️](https://thresh.tools/?t=demo_paragraph)

To add text before or after the annotation, add the `context` and `_context_before` entries to your data JSON. The context field is formatted in [**Markdown**](https://www.markdownguide.org/cheat-sheet/), allowing for titles, subsections or code in your annotation context.

<div align="center">
    <img src="./public/img/docs/paragraph.png" width="400" />
</div>

```json
[
  {
    "context": "<context written in markdown>",
    "source_context_before": "...",
    "source": "<selectable text with context>",
    "source_context_after": "...",
    "target_context_before": "...",
    "target": "<selectable text with context>",
    "target_context_after": "...",
  }
]
```

Additionally, we have utilities under the `display` command to help with side-by-side or long-context annotations:
```yaml
display:
 - side-by-side         # shows text and editor next to each other
 - text-side-by-side    # shows source and target next to each other
 - disable-lines        # disables lines between annotations which can be distracting
 - hide-context         # hides the context by default, adding a "show context" button
```

<div align="center">
    <img src="./public/img/docs/paragraph_horizontal.png" width="600" />
</div>

<a id="demo_adjudication"></a>

### Multi-interface Adjudication [↗️](https://thresh.tools/?t=demo_adjudication)

To display multiple interfaces simultaneously, use the `adjudication` flag with the number of interfaces you want to show, and use `highlight_first_interface` to add a "Your Annotations" label on the first interface. 

<div align="center">
    <img src="./public/img/docs/adjudication.png" width="600" />
</div>

```yaml
adjudication: 2
highlight_first_interface: <true|false>
```

Unlike the traditional data loader (which uses the `d` parameter), you can specify multiple datasources with the `dX` parameter as such:

```
thresh.tools/?d1=<DATASET_1>&d2=<DATASET_2>
```

<a id="demo_tokenization"></a>

### Sub-word Selection [↗️](https://thresh.tools/?t=demo_tokenization)

To allow a smoother annotation experience, the span selection will "snap" to the closest word boundary. This boundary is `word` by default, but can also be defined as such:

<!-- TODO: ADD SCREENSHOT -->

For a guide on pre-processing your dataset, please see [**notebook_tutorials/subword_annotation.ipynb**](./notebook_tutorials/subword_annotation.ipynb).

```yaml
tokenization: <word|char|tokenized>
```

<a id="demo_multilingual"></a>

### Multi-lingual Annotation [↗️](https://thresh.tools/?t=demo_multilingual)

Any text in our interface can be overriden by specifying its source using the `interface_text` flag. We create templates for different languages which can be used the `language` flag.

For a full list of interface text overrides, please reference a [**langauage template**](./public/lang/en.yml).

```yaml
language: <zh|en|es|hi|pt|bn|ru|ja|vi|tr|ko|fr|ur>
interface_text:
  typology:
    source_label: "莎士比亚"
    target_label: "现代英语"
  ...
```

Looking to expand our language support? See our section on [**contributing**](#language_contribute).

<a id="deploy"></a>

## Deploy an Interface

Please reference the "Deploy" modal within [**the interface builder**](https://thresh.tools/) for more detail!

<div align="center">
    <img src="./public/img/docs/deploy.png" width="400" />
</div>

<a id="demo_database"></a>

### Deploy with a Database [↗️](https://thresh.tools/?t=demo_crowdsource)

Use the `database` command to specify a public database to save annotations after users click a "Submit" button. We currently support [**Firebase**](https://firebase.google.com/) for any deployment method (in-house or crowdsourcing). Please see [**notebook_tutorials/deploy_database_with_firebase.md**](./notebook_tutorials/deploy_database_with_firebase.md) for a full tutorial on connecting a Firebase database to Thresh.

```yml
crowdsource: "custom"
database: 
    type: firebase
    project_id: [your-project-id]
    url: https://[your-project-id].firebaseio.com/
    # collection: thresh     # (default: thresh) The database to use
    # document: annotation   # (default: annotation) The document to use
    field: annotation_set_1  # The document field to store annotations
```

<a id="demo_crowdsource"></a>

### Deploy to Crowdsource Platforms [↗️](https://thresh.tools/?t=demo_crowdsource)

Use the `crowdsource` command to specify a "Submit" button at the end of annotation. Please see [**notebook_tutorials/deploy_to_prolific.ipynb**](./notebook_tutorials/deploy_to_prolific.ipynb) for a full guide on deploying an interface programatically.

```yaml
crowdsource: <prolific>
prolific_completion_code: "XXXXXXX"
```

<a id="manage"></a>

## Manage Data with the `thresh` Library
```sh
pip install thresh
```

### Loading Annotations
To load annotations, simply load your JSON data and call `load_annotations`:

```python
from thresh import load_interface

# Serialize your typology into a class
YourInterface = load_interface(
    "<path_to_typology>.yml"
)

# Load & serialize data from <file_name>.json
thresh_data = YourInterface.load_annotations(
    "<file_name>.json"
)
```

For example, using the SALSA demo data:
```python
from thresh import load_interface

# Load SALSA data using the SALSA typology
Salsa = load_interface("salsa.yml")
salsa_data = Salsa.load_annotations("salsa.json")

print(salsa_data[0])
>> SalsaEntry(
>>   annotator: annotator_1, 
>>   system: new-wiki-1/Human-2-written, 
>>   source: "Further important aspects of Fungi ...", 
>>   target: "An important aspect of Fungi in Art is ...", 
>>   edits: [
>>     DeletionEdit(
>>       input_idx: [[259, 397]], 
>>       annotation: DeletionAnnotation(
>>         deletion_type: GoodDeletion(
>>           val: 3
>>         ), 
>>         coreference: False, 
>>         grammar_error: False
>>       ),
>>     ), 
>>     ...
>>   ]
>> )
```

To prepare a dataset for annotation, simply export your `List[Annotation]` object and call `export_data`:
```python
# Export data to <file_name>.json for annotation
YourInterface.export_data(
    data=thresh_data,
    output_filename="<file_name>.json"
)
```

For a full tutorial with examples and advanced usage, please see [**/notebook_tutorials/load_data.ipynb**](./notebook_tutorials/load_data.ipynb).

### Internal Data Classes
Our data loading code is backed by custom internal classes which are created based on your typology. You can access these classes directly:
```python
from thresh import get_entry_class

# Get the custom data class for the SALSA typology
Salsa = load_interface("salsa.yml")
SalsaEntry = Salsa.get_entry_class()

# Create a new entry
custom_entry = SalsaEntry(
    annotator = annotator_1, 
    system = new-wiki-1/GPT-3-zero-shot, 
    target = The film has made more than $552 million at the box office and is currently the eighth most successful movie of 2022., 
    source = The film has grossed over $552 million worldwide, becoming the eighth highest-grossing film of 2022.
)

print(custom_entry.system)
>> new-wiki-1/GPT-3-zero-shot
```

## Data Conversion
Our `thresh` data format is meant to be universal across fine-grained annotation tasks. To show this, we have created conversion scripts from exisitng fine-grained typologies. Use the `thresh` library to convert from existing data formats:

```sh
pip install thresh
```

To convert to our standardized data format, our library includes bi-directional conversion from existing fine-grained annotation typologies:

```python
from thresh import convert_dataset

# To convert to the thresh.tools standardized format:
thresh_data = convert_dataset(
    data_path="<path_to_original_data>", 
    output_path="<path_to_output_data>.json", # (Optional) Will save data locally
    dataset_name="<dataset_name>"
)

# To convert back to the original format:
original_data = convert_dataset(
    data_path="<path_to_original_data>.json", 
    output_path="<path_to_output_data>",
    dataset_name="<dataset_name>", 
    reverse=True
)
```

We support conversion for the following datasets:
```
frank, scarecrow, mqm, snac, fg-rlhf, propaganda, arxivedits
```

### Demo Data Sources

In the table below you can find all the original data for each interface. For our demo data, we randomly selected 50 annotations from each dataset. We include the file names of the specific datsets we use below, selecting from the test set when applicable:

| interface | data | implementation | file name |
|:--- | :--: | :--- | :---: |
| FRANK | [🔗](https://github.com/artidoro/frank) | [**thresh.tools/frank**](https://thresh.tools/frank) | `human_annotations.json` |
| Scarecrow | [🔗](https://yao-dou.github.io/scarecrow) | [**thresh.tools/scarecrow**](https://thresh.tools/scarecrow) | `grouped_data.csv` |
| MQM | [🔗](https://github.com/google/wmt-mqm-human-evaluation) | [**thresh.tools/mqm**](https://thresh.tools/mqm) | `mqm_newstest2020_ende.tsv` |
| SALSA | [🔗](https://github.com/davidheineman/salsa) | [**thresh.tools/salsa**](https://thresh.tools/salsa) | `salsa_test.json` |
| SNaC | [🔗](https://github.com/tagoyal/snac) | [**thresh.tools/snac**](https://thresh.tools/snac) | `SNaC_data.json` |
| arXivEdits | [🔗](https://github.com/chaojiang06/arXivEdits) | [**thresh.tools/arxivedits**](https://thresh.tools/arxivedits) | `test.json` |
| Wu et al., 2023 | [🔗](https://github.com/allenai/FineGrainedRLHF) | [**thresh.tools/fg-rlhf**](https://thresh.tools/fg-rlhf) | `dev_feedback.json` |
| Da San Martino et al., 2019 | [🔗](https://propaganda.qcri.org/) | [**thresh.tools/propaganda**](https://thresh.tools/propaganda) | `test/article<X>.labels.tsv` |

We do not create dataloaders for the following interfaces:

| interface | reason |
|:---: | :-- |
| MultiPIT | This is an inspection interface, examples are taken from Table 7 of the [**MultiPIT paper**](https://aclanthology.org/2022.emnlp-main.631). |
| CWZCC | The example is taken from App. B of the [**CWZCC paper**](https://aclanthology.org/2020.lrec-1.327). Full dataset is not publically available due to copyright and privacy concerns. |
| ERRANT | Our example data is taken from the annotations from the [**W&I+LOCNESS corpus**]() collected by [**Bryant et al., 2019**](https://aclanthology.org/W19-4406/) from original exerpts from [**Yannakoudakis et al., 2018**](https://www.tandfonline.com/doi/abs/10.1080/08957347.2018.1464447) and [**Granger, 1998**](https://www.learnercorpusassociation.org/resources/tools/locness-corpus/). The dataset was released as part of the [**Building Educational Applications 2019 Shared Task**](https://www.cl.cam.ac.uk/research/nl/bea2019st/#data). |

## Contributing

<a id="local"></a>

### Set Up `thresh.tools` Locally
Clone this repo: 
```sh
git clone https://github.com/davidheineman/thresh.git
```

Set up Vue: 
```sh
npm install
npm run dev     # To run a dev environment
npm run build   # To build a prod environment in ./build
npm run deploy  # Push to gh-pages
```

Deployment will create a `gh-pages` branch. You will need to go into GitHub Pages settings and set the source branch to `gh-pages`.

### Submit a New Typology
You do *not* need to do this if you want to use your interface (please see [**Deploy an Interface**](#deploy)). This will add your interface to the `thresh.tools` homepage!

<div align="left">
    <img src="./public/img/hosted-interface.png" width="300px" />
</div>

To make your interface available in the `thresh.tools` builder, please clone this repo and submit a pull request with the following:

1. Add your typology YML file to [**public/templates/**](./public/templates/).
2. Add your demo data JSON file to [**public/data/**](./public/data/). We encourage authors to submit a sample of 50 examples for their full dataset, but this is not required.
3. Modify [**src/main.js**](./src/main.js) to link to your dataset, by adding a line to `templates`:

    ```js
    const templates = [
        { name: "SALSA", path: "salsa", task: "Simplification", hosted: true },
        { name: "Scarecrow", path: "scarecrow", task: "Open-ended Generation", hosted: true },
        ...
        { name: "<display_name>", path: "<your_interface>", task: "<your_task>", hosted: true }
    ]
    ```
    In this case `<your_task>` will correspond to the task you are grouped with. *Note: You can preview your changes by setting up [**thresh.tools locally**](#local)!*
4. Submit a [**pull request**](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) with your changes! Then we will merge with the `thresh.tools` main branch. Please reach out if you have any questions.

<a id="language_contribute"></a>

### Add Language Support
Multi-lingual deployment is core to `thresh.tools`, and we are actively working to add support for more languages. If you would like to add support for a new language (or revise our existing support), our language templates are located in [**public/lang/**](./public/lang/).
- To add support for a new language, simply create a new `.yml` using the structure of an [**existing language template**](./public/lang/en.yml).
- To revise an existing template, simply make changes within the template.

When you are finished, please submit a [**pull request**](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) with your changes.

### Set Up the `thresh` Python Library
Clone this repo: 
```sh
git clone https://github.com/davidheineman/thresh.git
cd data_tools
```

Make any changes to the library and push to PyPi:
```sh
rm -r dist 
python -m build
python -m twine upload --repository pypi dist/*
```

## Cite `thresh.tools`
If you find our library helpful, please consider citing [**our work**](https://arxiv.org/abs/2308.06953):
```
@article{heineman2023thresh,
  title={Thresh: A Unified, Customizable and Deployable Platform for Fine-Grained Text Evaluation},
  author={Heineman, David and Dou, Yao and and Xu, Wei},
  journal={arXiv preprint arXiv:2308.06953},
  year={2023}
}
```
