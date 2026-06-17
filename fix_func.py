"""Replace extractRtfImages function body."""
lines = open('frontend/src/views/SettingsView.vue', 'r', encoding='utf-8').readlines()

# Find function boundaries
fn_start, fn_end = None, None
in_func = False
brace_depth = 0
for i, line in enumerate(lines):
    if 'async function extractRtfImages' in line:
        fn_start = i
        in_func = True
    if in_func:
        brace_depth += line.count('{') - line.count('}')
        if brace_depth == 0 and fn_start is not None and i > fn_start:
            fn_end = i
            break

print(f"Function: lines {fn_start+1}-{fn_end+1}")

# Keep the signature + opening brace + first lines (pict block extraction logic)
# Replace from after pictBlocks extraction to before return

# Find where "const pictBlocks = [];" ends and where "return result;" is
return_line = None
for i in range(fn_start, fn_end + 1):
    if 'return result;' in lines[i]:
        return_line = i
        break

# The body to replace: from "// 第2步" comment to just before "return result;"
# Let me find the line with "第2步" or we can just replace everything between the pictBlocks closing
# and the return

# Find "console.log("[sig] pictBlocks:" line"
pict_log_line = None
for i in range(fn_start, return_line):
    if 'pictBlocks' in lines[i] and 'console' in lines[i]:
        pict_log_line = i
        break

# Replace from pict_log_line+1 to return_line-1
new_body = [
    '\n',
    '  // 删除所有非 hex 字符，留下纯净的图片数据\n',
    '  for (const block of pictBlocks) {\n',
    '    const hexStr = block.replace(/[^0-9a-fA-F]/g, "");\n',
    '    if (hexStr.length < 200) continue;\n',
    '    const len = Math.floor(hexStr.length / 2);\n',
    '    const bytes = new Uint8Array(len);\n',
    '    for (let j = 0; j < len; j++) {\n',
    '      bytes[j] = parseInt(hexStr.substring(j * 2, j * 2 + 2), 16);\n',
    '    }\n',
    '    try {\n',
    '      const blob = new Blob([bytes]);\n',
    '      const bmp = await createImageBitmap(blob);\n',
    '      const canvas = document.createElement("canvas");\n',
    '      canvas.width = bmp.width; canvas.height = bmp.height;\n',
    '      canvas.getContext("2d").drawImage(bmp, 0, 0);\n',
    '      bmp.close();\n',
    '      result.push(canvas.toDataURL("image/png"));\n',
    '    } catch {\n',
    '      console.warn("[sig] decode failed, hexLen:", hexStr.length);\n',
    '    }\n',
    '  }\n',
    '\n',
]

out = lines[:pict_log_line + 1] + new_body + lines[return_line:]
with open('frontend/src/views/SettingsView.vue', 'w', encoding='utf-8') as f:
    f.writelines(out)
print(f"Replaced from line {pict_log_line+2} to {return_line}")
