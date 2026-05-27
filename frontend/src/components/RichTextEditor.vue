<template>
  <div class="rte" :class="{ 'rte--focused': editor?.isFocused }">
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
        •≡
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
        🔗
      </button>
    </div>
    <editor-content :editor="editor" class="rte-content" />
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount, nextTick } from "vue";
import { useEditor, EditorContent } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";

const props = defineProps({
  modelValue: { type: String, default: "" },
});
const emit = defineEmits(["update:modelValue"]);

const initialValue = ref(props.modelValue);
const linkUrl = ref("");

const editor = useEditor({
  content: initialValue.value,
  extensions: [
    StarterKit.configure({
      heading: false,
      codeBlock: false,
      blockquote: false,
      horizontalRule: false,
    }),
    Link.configure({ openOnClick: false, HTMLAttributes: { rel: "noopener" } }),
  ],
  editorProps: {
    attributes: { class: "rte-content" },
  },
  onUpdate: ({ editor }) => {
    emit("update:modelValue", editor.getHTML());
  },
});

// Sync external modelValue changes back into the editor (e.g. template switching)
watch(
  () => props.modelValue,
  (val) => {
    if (editor.value && val !== editor.value.getHTML()) {
      editor.value.commands.setContent(val || "");
    }
  }
);

// Basic link toggle: prompt-based for simplicity
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
  min-height: 120px;
  font-size: 14px;
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
</style>
