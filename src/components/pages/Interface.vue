<script setup>
  import AnnotationEditor from "../editor/AnnotationEditor.vue";
  import AnnotationViewer from "../viewer/AnnotationViewer.vue";
  import CommentBox from "../common/CommentBox.vue";
  import Instructions from "../common/Instructions.vue";
  import OverallScore from "../common/OverallScore.vue";
  import HitBox from "../hitbox/HitBox.vue";

  import tinycolor from 'tinycolor2';
  import _ from 'lodash';
  import { COLORS } from '../../assets/js/constants.js';
</script>

<script>
  export default {
    data() {
      return {
        panelId: this.$.uid,

        total_hits: 0,
        current_hit: 1,
        hits_data: null,
        config: null,
        edits_dict: {},
        lines: {},
        selected_edits: {},

        editor_open: false,
        selected_edits_html: '',
        annotating_edit_span_category_id: null,

        hit_box_config: undefined,
        selected_state: undefined,
        annotating_edit_span: undefined,
        
        set_hit: this.set_hit,
        set_hits_data: this.set_hits_data,
        set_edits_dict: this.set_edits_dict,
        set_lines: this.set_lines,
        set_span_text: this.set_span_text,
        set_span_indices: this.set_span_indices,
        set_span_category: this.set_span_category,
        set_edit_html: this.set_edit_html,
        set_selected_edits: this.set_selected_edits,
        set_hit_box_config: this.set_hit_box_config,
        set_editor_state: this.set_editor_state,
        set_annotating_edit_span_category_id: this.set_annotating_edit_span_category_id,
        set_annotating_edit_span: this.set_annotating_edit_span,

        refresh_interface_edit: this.refresh_interface_edit,

        instructions_open: false,
        toggle_instructions: this.toggle_instructions,
      }
    },
    props: [
      'input_data',
      'consumed_config',
      'highlight',
      'candidate_label',
      'show_instructions',
      'show_hit_header',
      'synchronized_hit',
      'set_synchronized_hit',
      'on_hits_data_change',
      'get_export_data',
      'handle_uploaded_data'
    ],
    watch: {
      input_data() {
        this.consume_data()
      },
      consumed_config() {
        this.consume_config()
      },
      synchronized_hit(hit_num) {
        if (hit_num != null && hit_num !== this.current_hit) {
          this.current_hit = hit_num
        }
      }
    },
    methods: {
        consume_data() {
          if (!this.input_data || !this.input_data.data) { return }
          let data = _.cloneDeep(this.input_data.data);
          this.set_hits_data(data)
          this.set_hit(this.synchronized_hit || 1)
        },
        consume_config() {
          let new_config;
          if (this.consumed_config.hasOwnProperty('consumed_config')) {
            new_config = _.cloneDeep(this.consumed_config.consumed_config)
          } else if (this.consumed_config.hasOwnProperty('config')) { 
            new_config = _.cloneDeep(this.consumed_config.config)
          } else {
            new_config = _.cloneDeep(this.consumed_config)
          }
          this.config = new_config
          
          if (this.config.template_label) {
            $('title').text(this.config.template_label);
          }
        },
        set_hit(hit_num) {
          if (this.set_synchronized_hit) {
            this.set_synchronized_hit(hit_num)
          } else if (hit_num != this.current_hit && this.config.adjudication) {
            $(`.circle-${hit_num}`).click()
          }
          this.current_hit = hit_num;
        },
        set_hits_data(hit_data) {
            hit_data.forEach(o => o.edits = o.edits || []);
            hit_data.forEach((o, idx) => { o._thresh_id = idx + 1; });
            this.hits_data = hit_data;
            this.total_hits = hit_data.length;
            if (this.on_hits_data_change) {
              this.on_hits_data_change(hit_data)
            }
        },
        set_edits_dict(edits_dict) {
            this.edits_dict = edits_dict;
        },
        set_span_text(text, type) {
          if (type == "source") {
            this.selected_state.source_span = text;
          } else if (type == "target") {
            this.selected_state.target_span = text;
          }
          if (this.editor_open && this.annotating_edit_span_category_id != null) {
            this.set_annotating_edit_span(text, type)
          }
        },
        set_span_indices(indices, type) {
          if (type == "source") {
            this.selected_state.source_idx = indices;
          } else if (type == "target") {
            this.selected_state.target_idx = indices;
          }
        },
        set_span_category(category, type) {
          if (type == "source") {
            this.selected_state.source_category = category;
          } else if (type == "target") {
            this.selected_state.target_category = category;
          }
          if (this.config.auto_add_spans && !this.editor_open) {
            const hit = this.current_hit
            const indices = [...this.selected_state[`${type}_idx`]]
            this.$nextTick(() => {
              if (this.current_hit === hit && !this.editor_open) this.auto_add_span(indices, type)
            })
          }
        },
        auto_add_span(indices, type) {
          const category = this.config.edits[0]
          if (!this.config.auto_add_spans || !category || !['source', 'target'].includes(type)) return
          const [start, end] = indices
          const hit = this.hits_data[this.current_hit - 1]
          if (indices.length !== 2 || !Number.isInteger(start) || !Number.isInteger(end)
              || start < 0 || end <= start || end > (hit[type] || '').length) return
          if (this.config.confirm_span_before_save) {
            // Keep the selected text/offsets as a draft; selecting either side
            // again replaces that side until the annotator explicitly saves.
            this.set_editor_state(true)
            const panel = $(this.$el)
            panel.find('.quality-selection').hide()
            panel.find('#add_an_edit').show()
            panel.find(`input[name=edit_cotegory_${this.panelId}]`).prop('checked', false)
            panel.find(`input[name=edit_cotegory_${this.panelId}][value="${category.name}"]`).prop('checked', true)
            panel.find('.span-selection-div').hide()
            panel.find(`.span-selection-div[data-category="${category.name}"]`).show()
            window.getSelection()?.removeAllRanges()
            return
          }
          const field = type === 'source' ? 'input_idx' : 'output_idx'
          const edits = hit.edits || []
          if (edits.some(edit => edit.category === category.name && edit[field]?.some(span => span[0] === start && span[1] === end))) {
            this.refresh_interface_edit()
            return
          }
          const id = Math.max(0, ...edits.filter(edit => edit.category === category.name).map(edit => Number(edit.id))) + 1
          const data = _.cloneDeep(this.hits_data)
          data[this.current_hit - 1].edits.push({ category: category.name, id, annotation: null, [field]: [[start, end]] })
          this.set_hits_data(data)
          this.refresh_interface_edit()
          window.getSelection()?.removeAllRanges()
          if (category.annotation?.length) {
            this.$nextTick(() => {
              $(this.$el).find(`.annotation-icon[data-category="${category.name}"][data-id="${category.name}-${id}"]`).click()
            })
          }
        },
        set_edit_html(html) {
          this.selected_edits_html = html;
        },
        set_selected_edits(edits) {
          this.selected_edits = edits;
        },
        refresh_interface_edit() {
          const DEFAULT_HIT_BOX_CONFIG = {
            enable_select_source_sentence: Boolean(this.config?.auto_add_spans),
            enable_select_target_sentence: Boolean(this.config?.auto_add_spans),
            enable_multi_select_source_sentence: false,
            enable_multi_select_target_sentence: false,
          }
          const DEFAULT_SELECTED_STATE = {
            source_span: '',
            source_idx: [],
            source_category: '',
            target_span: '',
            target_idx: [],
            target_category: '',
            split: '',
            split_id: null
          }
          const DEFAULT_ANNOTATING_EDIT_SPAN = {
            source: '',
            target: '',
            composite: ''
          }

          this.selected_edits = []
          this.selected_edits_html = ""
          this.selected_state = DEFAULT_SELECTED_STATE
          this.hit_box_config = DEFAULT_HIT_BOX_CONFIG
          this.annotating_edit_span = DEFAULT_ANNOTATING_EDIT_SPAN
          this.annotating_edit_span_category_id = null
        },
        set_hit_box_config(config) {
          this.hit_box_config = config;
        },
        set_editor_state(state) {
          this.editor_open = state;
        },
        set_annotating_edit_span_category_id(id) {
          this.annotating_edit_span_category_id = id;
        },
        set_annotating_edit_span(data, sent_type=null) {
          if (sent_type == 'source') {
            this.annotating_edit_span.source = data;
          } else if (sent_type == 'target') {
            this.annotating_edit_span.target = data;
          } else if (sent_type == 'composite') {
            this.annotating_edit_span.composite = data;
          } else {
            console.warn(`Invalid sent_type : ${sent_type}`)
          }
        },
        set_lines(lines) {
          this.lines = lines;
        },
        toggle_instructions() {
          this.instructions_open = !this.instructions_open;
        },
        compile_style() {
          if (!this.config.hasOwnProperty('edits')) { return }

          // Compile color overrides

          let css = ``
          for (const edit of this.config.edits) {
            let color = edit.color
            if (COLORS.hasOwnProperty(color)) {
              color = COLORS[color]
            }

            let light_color = tinycolor(color).lighten(25).toHexString();
            
            css += `
              :root { --${edit.name}: ${color}; --${edit.name}-light: ${light_color}; }
              .border-${edit.name} { border-bottom: 3px solid ${color}; }
              .border-${edit.name}-all { border: 2px solid ${color}; }
              .bg-${edit.name} { background-color: ${color}; }
              .txt-${edit.name} { color: ${color}; }
              .bg-${edit.name}-light { background-color: ${light_color}; }
              .border-${edit.name}-light { border-bottom: 3px solid ${light_color}; }
              .border-${edit.name}-light-all { border: 2px solid ${light_color}; }
              .txt-${edit.name}-light { color: ${light_color}; }
              .checkbox-tools-yes-no:checked + label.question-${edit.name},
              .checkbox-tools:checked + label.question-${edit.name},
              .checkbox-tools:checked + label.txt-${edit.name}{
                border: 2px solid var(--${edit.name});
              }
              .select-color-${edit.name}::selection { background: ${light_color} !important; }
            `
          }

          // Compile font size overrides
          if (this.config.font_size) {
            if (this.config.font_size.source) {
              css += `#source-sentence { font-size: ${this.config.font_size.source}px; }`
            }
            if (this.config.font_size.target) {
              css += `#target-sentence { font-size: ${this.config.font_size.target}px; }`
            }
          }

          return css
        },
        isAdjacent() {
          return this.config.hasOwnProperty('display') && Object.values(this.config.display).includes('side-by-side')
        }
    },
    updated() {
      $(this.$el).find('.custom_style').html(`<style>${this.compile_style()}</style>`)
      $(this.$el).find(`.circle-${this.current_hit}`).addClass('circle-active');
    }, 
    mounted() {
      this.consume_data()
      this.consume_config()
    },
    created() {
      this.consume_config()
      this.refresh_interface_edit()
    }
  }
  
</script>

<template>
  <div v-if="config != null" class="container mb0 card-body" :data-panel="panelId" v-bind:class="{ 'w-100 w-adjacent': isAdjacent(), 'w-65': !isAdjacent() }">
    <div class='custom_style' id='custom_style'>Custom style has not loaded!</div>
    <div v-if="highlight" class="tc f3 b mb3 mt3 adjudication-highlight">
      {{ config.interface_text.adjudication.highlight_label }}
    </div>
    <main v-bind:class="{ 'adjacent': isAdjacent() }">
      <div v-bind:class="{ 'selection-adjacent': isAdjacent() }">
        <Instructions v-if="show_instructions !== false" v-bind="$data" :config="config" />
        <!-- <CommentBox v-bind="$data" :config="config" /> -->
        <HitBox
          v-bind="$data"
          :config="config"
          :candidate_label="candidate_label"
          :show_header="show_hit_header"
          :get_export_data="get_export_data"
          :handle_uploaded_data="handle_uploaded_data"
        >
          <template #score>
            <OverallScore v-if="config.overall_score" v-bind="$data" :config="config" />
          </template>
        </HitBox>
      </div>
      <div v-bind:class="{ 'annotation-adjacent': isAdjacent() }">
        <AnnotationEditor v-bind="$data" :config="config" />
        <AnnotationViewer v-bind="$data" :config="config" />
      </div>
    </main>
  </div>
</template>

<style>
  @import '../../assets/css/index.css';
  @import '../../assets/css/selection.css';
  @import '../../assets/css/button.css';
  @import '../../assets/css/select_box.css';
  @import '../../assets/css/download_upload.css';
  @import 'https://unpkg.com/tachyons@4.10.0/css/tachyons.min.css';
  @import 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css';
  @import 'https://cdnjs.cloudflare.com/ajax/libs/animate.css/3.7.2/animate.min.css';
</style>
