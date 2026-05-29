<template>
  <div class="rte" :class="{ 'rte--focused': editor?.isFocused }">
    <div v-if="variables && variables.length" class="rte-pills">
      <button
        v-for="v in variables"
        :key="v.marker"
        class="rte-pill"
        @click="insertVariable(v.marker)"
      >
        {{ v.label }}
      </button>
    </div>
    <div class="rte-toolbar">
      <button
        class="rte-btn"
        :class="{ 'rte-btn--active': editor?.isActive('bold') }"
        title="加粗"
        @click="editor?.chain().focus().toggleBold().run()"
      >
        <strong>B</strong>
      </button>
      <button
        class="rte-btn"
        :class="{ 'rte-btn--active': editor?.isActive('italic') }"
        title="斜体"
        @click="editor?.chain().focus().toggleItalic().run()"
      >
        <em>I</em>
      </button>
      <span class="rte-sep"></span>
      <button
        class="rte-btn"
        :class="{ 'rte-btn--active': editor?.isActive('bulletList') }"
        title="无序列表"
        @click="editor?.chain().focus().toggleBulletList().run()"
      >
        &bull;&equiv;
      </button>
      <button
        class="rte-btn"
        :class="{ 'rte-btn--active': editor?.isActive('orderedList') }"
        title="有序列表"
        @click="editor?.chain().focus().toggleOrderedList().run()"
      >
        1.
      </button>
      <span class="rte-sep"></span>
      <button
        class="rte-btn"
        :class="{ 'rte-btn--active': editor?.isActive('link') }"
        title="插入/编辑链接"
        @click="toggleLink"
      >
        &#128279;
      </button>
      <span class="rte-sep"></span>
      <button
        class="rte-btn"
        title="添加附件"
        @click="handleAttachClick"
      >
        &#128206;
      </button>
      <input
        ref="fileInput"
        type="file"
        multiple
        hidden
        @change="handleFileSelect"
      />
    </div>
    <editor-content :editor="editor" class="rte-content" />
    <div v-if="attachments.length" class="rte-attachments">
      <div
        v-for="(f, i) in attachments"
        :key="i"
        class="rte-attach-item"
      >
        <span class="rte-attach-name">{{ f.name }}</span>
        <span class="rte-attach-size">{{ formatSize(f.size) }}</span>
        <button class="rte-attach-remove" @click="removeAttachment(i)">&times;</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from "vue";
import { useEditor, EditorContent } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import { encodeImage } from "@/api";

const props = defineProps({
  modelValue: { type: String, default: "" },
  variables: {
    type: Array,
    default: () => [],
  },
});
const emit = defineEmits(["update:modelValue", "update:attachments"]);

const suppressEmit = ref(false);

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit.configure({
      heading: false,
      codeBlock: false,
      blockquote: false,
      horizontalRule: false,
    }),
    Link.configure({ openOnClick: false, HTMLAttributes: { rel: "noopener" } }),
    Image.configure({ inline: true }),
  ],
  editorProps: {
    attributes: { class: "rte-content" },
    handlePaste: (view, event) => {
      const items = event.clipboardData?.items;
      if (!items) return false;

      // Direct image paste (screenshot / image file in clipboard)
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
              editor.value?.chain().focus().setImage({ src: e.target.result }).run();
            };
            reader.readAsDataURL(file);
            return true;
          }
        }
      }

      // HTML paste containing <img> with local file:// paths
      const html = event.clipboardData?.getData("text/html");
      if (html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");
        const imgs = doc.querySelectorAll("img");
        const fileImgs = [];
        imgs.forEach((img) => {
          const src = img.getAttribute("src");
          if (src && (src.startsWith("file://") || /^[A-Z]:[/\\]/i.test(src))) {
            fileImgs.push({ img, src });
          }
        });

        if (fileImgs.length > 0) {
          Promise.all(
            fileImgs.map(({ img, src }) =>
              encodeImage(src)
                .then(({ data }) => img.setAttribute("src", data.data_uri))
                .catch(() => {})
            )
          ).then(() => {
            editor.value?.commands.insertContent(doc.body.innerHTML);
          });
          return true;
        }
      }

      return false;
    },
  },
  onUpdate: ({ editor }) => {
    if (suppressEmit.value) return;
    emit("update:modelValue", editor.getHTML());
  },
});

watch(
  () => props.modelValue,
  (val) => {
    if (editor.value && val !== editor.value.getHTML()) {
      suppressEmit.value = true;
      editor.value.commands.setContent(val || "");
      suppressEmit.value = false;
    }
  }
);

function insertVariable(marker) {
  editor.value?.chain().focus().insertContent(marker).run();
}

function toggleLink() {
  const ed = editor.value;
  if (!ed) return;

  if (ed.isActive("link")) {
    ed.chain().focus().unsetLink().run();
    return;
  }

  const url = window.prompt("请输入链接地址 (https://...)");
  if (url) {
    ed.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
  }
}

// ── Attachments ────────────────

const fileInput = ref(null);
const attachments = ref([]);

function handleAttachClick() {
  fileInput.value?.click();
}

function emitAttachments() {
  emit("update:attachments", attachments.value.map((a) => ({ name: a.name, size: a.size })));
}

function handleFileSelect(e) {
  const files = e.target.files;
  if (!files) return;
  for (const f of files) {
    attachments.value.push({ name: f.name, size: f.size, file: f });
  }
  emitAttachments();
  e.target.value = "";
}

function removeAttachment(index) {
  attachments.value.splice(index, 1);
  emitAttachments();
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function getAttachments() {
  return attachments.value.map((a) => a.file);
}

defineExpose({ getAttachments });

onBeforeUnmount(() => {
  editor.value?.destroy();
});
</script>

<style scoped>
.rte {
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.2s;
  background: #fff;
}

.rte--focused {
  border-color: #0071e3;
  box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.15);
}

.rte-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: #fafafa;
  border-bottom: 1px solid #e0e0e0;
}

.rte-pill {
  padding: 3px 10px;
  border: none;
  border-radius: 12px;
  background: #e8f2ff;
  color: #0071e3;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.rte-pill:hover {
  background: #0071e3;
  color: #fff;
}

.rte-toolbar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 8px 10px;
  background: #f5f5f7;
  border-bottom: 1px solid #e0e0e0;
}

.rte-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #424245;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.rte-btn:hover {
  background: #e8e8ed;
}

.rte-btn--active {
  background: #0071e3;
  color: #fff;
}

.rte-sep {
  width: 1px;
  height: 20px;
  background: #d0d0d0;
  margin: 0 4px;
}

.rte-content {
  padding: 12px 14px;
  min-height: 100px;
  font-size: 16px;
  line-height: 1.7;
  color: #1d1d1f;
  outline: none;
}

.rte-content :deep(p) {
  margin: 0 0 8px;
}

.rte-content :deep(a) {
  color: #0071e3;
}

.rte-content :deep(ul),
.rte-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.rte-content :deep(li) {
  margin-bottom: 4px;
}

.rte-content :deep(strong) {
  font-weight: 600;
}

.rte-content :deep(img) {
  max-width: 100%;
  height: auto;
}

.rte-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid #e0e0e0;
  background: #fafafa;
}

.rte-attach-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #f0f0f0;
  border-radius: 8px;
  font-size: 12px;
}

.rte-attach-name {
  color: #1d1d1f;
  font-weight: 500;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rte-attach-size {
  color: #86868b;
}

.rte-attach-remove {
  border: none;
  background: none;
  color: #86868b;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0 2px;
  border-radius: 4px;
}

.rte-attach-remove:hover {
  color: #d03050;
  background: rgba(0, 0, 0, 0.05);
}
</style>
