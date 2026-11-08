# -*- coding: utf-8 -*-
"""构建《AI 工程全景手册》DOCX。

正文用轻量标记写在 parts/*.md 里，这里只负责解析并套样式：
  # / ## / ### / ####   标题
  ```lang ... ```       代码块
  | a | b |             表格（连续行）
  - item                项目符号
  1. item               编号列表
  > quote               引用块
  ---                   分隔线（忽略）
  **bold** `code`       行内强调
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
PARTS = ROOT / "parts"
OUT = ROOT.parent / "AI工程全景手册.docx"

CN_FONT = "微软雅黑"
CN_BODY = "宋体"
CODE_FONT = "Consolas"
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
ACCENT2 = RGBColor(0x2E, 0x74, 0xB5)
GREY = RGBColor(0x59, 0x59, 0x59)
MUTED = RGBColor(0x8C, 0x8C, 0x8C)


# ---------------------------------------------------------------- 基础工具
def set_run_font(run, name=CN_BODY, size=None, bold=None, color=None, code=False):
    run.font.name = name if not code else CODE_FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(attr), name if not code else CODE_FONT)
    rfonts.set(qn("w:eastAsia"), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    return run


def shade(el, hex_fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    el.append(shd)


def para_shade(paragraph, hex_fill):
    shade(paragraph._p.get_or_add_pPr(), hex_fill)


def para_border(paragraph, color="D9D9D9", size=6, sides=("left",)):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        ppr.append(pbdr)
    for side in sides:
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "6")
        el.set(qn("w:color"), color)
        pbdr.append(el)


def add_field(paragraph, instr):
    r = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = "更新目录：Ctrl+A → F9"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r._r.append(fld_begin)
    r._r.append(instr_el)
    r._r.append(fld_sep)
    r._r.append(txt)
    r._r.append(fld_end)
    return r


# ---------------------------------------------------------------- 文档骨架
def new_document() -> Document:
    doc = Document()

    st = doc.styles["Normal"]
    st.font.name = CN_BODY
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), CN_BODY)
    st.paragraph_format.line_spacing = 1.45
    st.paragraph_format.space_after = Pt(6)

    sizes = {"Heading 1": 19, "Heading 2": 15, "Heading 3": 12.5, "Heading 4": 11}
    for name, size in sizes.items():
        s = doc.styles[name]
        s.font.name = CN_FONT
        s.font.size = Pt(size)
        s.font.bold = True
        s.font.color.rgb = ACCENT if name != "Heading 4" else ACCENT2
        s.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
        s.paragraph_format.space_before = Pt(18 if name == "Heading 1" else 12)
        s.paragraph_format.space_after = Pt(8)
        s.paragraph_format.keep_with_next = True

    for section in doc.sections:
        section.top_margin = Cm(2.3)
        section.bottom_margin = Cm(2.1)
        section.left_margin = Cm(2.6)
        section.right_margin = Cm(2.4)

    # 页脚：页码
    footer_p = doc.sections[0].footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(footer_p, "PAGE")
    for r in footer_p.runs:
        set_run_font(r, CN_FONT, 9, color=GREY)

    # 页眉：书名
    head_p = doc.sections[0].header.paragraphs[0]
    head_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = head_p.add_run("AI 工程全景手册")
    set_run_font(hr, CN_FONT, 8.5, color=GREY)

    return doc


# ---------------------------------------------------------------- 行内解析
INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")


def add_inline(paragraph, text, size=10.5, base_bold=False, color=None):
    for chunk in INLINE.split(text):
        if not chunk:
            continue
        if chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
            set_run_font(paragraph.add_run(chunk[2:-2]), CN_BODY, size, bold=True, color=color)
        elif chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:
            run = set_run_font(paragraph.add_run(chunk[1:-1]), CODE_FONT, size - 0.7,
                               color=RGBColor(0xC0, 0x39, 0x2B), code=True)
            runpr = run._element.get_or_add_rPr()
            shade(runpr, "F2F2F2")
        else:
            set_run_font(paragraph.add_run(chunk), CN_BODY, size, bold=base_bold, color=color)


# ---------------------------------------------------------------- 块级渲染
def render_code(doc, lines, lang=""):
    body = "\n".join(lines).rstrip()
    if not body:
        return
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(4)
    pf.space_after = Pt(10)
    pf.line_spacing = 1.08
    pf.left_indent = Cm(0.35)
    pf.right_indent = Cm(0.2)
    para_shade(p, "F7F7F5")
    para_border(p, "D0D0D0", 8, sides=("left",))
    if lang:
        tag = p.add_run(lang.upper() + "  ")
        set_run_font(tag, CN_FONT, 7.5, bold=True, color=RGBColor(0x8C, 0x8C, 0x8C))
    run = p.add_run(body)
    set_run_font(run, CODE_FONT, 8.4, code=True)


def render_table(doc, rows):
    header, body = rows[0], rows[1:]
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    def fill(cells, values, is_head=False):
        for i, val in enumerate(values):
            cell = cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_inline(p, val, size=9, base_bold=is_head)
            if is_head:
                shade(cell._tc.get_or_add_tcPr(), "E8EEF7")
                for r in p.runs:
                    r.bold = True

    fill(table.add_row().cells, header, is_head=True)
    for row in body:
        padded = list(row) + [""] * (cols - len(row))
        fill(table.add_row().cells, padded)

    # 按内容长度分配列宽：避免「路径 A」这种短列白占半屏
    weights = []
    for c in range(cols):
        longest = max((len(r[c]) for r in rows if c < len(r)), default=1)
        weights.append(min(max(longest, 4), 40) ** 0.75)
    total = sum(weights)
    usable = doc.sections[0].page_width - doc.sections[0].left_margin - doc.sections[0].right_margin
    for c, w in enumerate(weights):
        width = int(usable * w / total)
        for row in table.rows:
            row.cells[c].width = width

    # 表头跨页重复
    trpr = table.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trpr.append(th)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def render_quote(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(0.4)
    pf.space_before = Pt(2)
    pf.space_after = Pt(8)
    para_shade(p, "FFF8E7")
    para_border(p, "E0B84C", 12, sides=("left",))
    add_inline(p, text, size=9.5)


def render_markdown(doc, md: str):
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 代码块
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i].rstrip())
                i += 1
            i += 1
            render_code(doc, buf, lang)
            continue

        # 表格
        if stripped.startswith("|") and stripped.endswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                raw = lines[i].strip().strip("|")
                cells = [c.strip() for c in raw.split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                render_table(doc, rows)
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1:
                doc.add_page_break()
            h = doc.add_heading(level=min(level, 4))
            h.text = ""
            add_inline(h, text, size={1: 19, 2: 15, 3: 12.5, 4: 11}[level],
                       base_bold=True, color=ACCENT if level <= 3 else ACCENT2)
            for r in h.runs:
                r.font.color.rgb = ACCENT if level <= 3 else ACCENT2
            i += 1
            continue

        # 引用
        if stripped.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            render_quote(doc, " ".join(buf))
            continue

        # 分隔线
        if re.fullmatch(r"-{3,}", stripped):
            i += 1
            continue

        # 列表：悬挂缩进 + 灰点/灰号，视觉上轻，不抢正文
        if re.match(r"^[-*]\s+", stripped):
            text = re.sub(r"^[-*]\s+", "", stripped)
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.space_before = Pt(1)
            pf.space_after = Pt(3)
            pf.left_indent = Cm(0.9)
            pf.first_line_indent = Cm(-0.45)
            set_run_font(p.add_run("·  "), CN_BODY, 10, bold=True, color=MUTED)
            add_inline(p, text, size=10)
            i += 1
            continue

        if re.match(r"^\d+[.)]\s+", stripped):
            num = re.match(r"^(\d+)[.)]\s+", stripped).group(1)
            text = re.sub(r"^\d+[.)]\s+", "", stripped)
            # 用字面序号而不是 List Number 样式：避免全文编号跨章节连续
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.space_before = Pt(1)
            pf.space_after = Pt(3)
            pf.left_indent = Cm(1.0)
            pf.first_line_indent = Cm(-0.55)
            set_run_font(p.add_run(num + ".  "), CN_BODY, 10, bold=False, color=MUTED)
            add_inline(p, text, size=10)
            i += 1
            continue

        # 普通段落
        buf = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith(("```", "|", "#", ">", "- ", "* "))
                    or re.match(r"^\d+[.)]\s+", nxt) or re.fullmatch(r"-{3,}", nxt)):
                break
            buf.append(nxt)
            i += 1
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        add_inline(p, " ".join(buf))


# ---------------------------------------------------------------- 封面 & 目录
def build_cover(doc):
    for _ in range(5):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(p.add_run("AI 工程全景手册"), CN_FONT, 34, bold=True, color=ACCENT)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    set_run_font(p.add_run("从框架原理到落地变现的完整路线图"), CN_FONT, 15, color=ACCENT2)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(26)
    set_run_font(p.add_run("模型 · 推理引擎 · Agent 框架 · 协议 · 网关 · 安全 · 部署 · 变现"),
                 CN_FONT, 10.5, color=GREY)

    for _ in range(9):
        doc.add_paragraph()

    for text, size in [
        ("面向：不会写代码但要用 AI 做事的人 / 刚入行的工程师 / 团队技术负责人", 10),
        ("版本：v1.0    体例：原理 → 调用 → 选型 → 踩坑 → 行动", 10),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run_font(p.add_run(text), CN_BODY, size, color=GREY)

    doc.add_page_break()


def build_toc(doc):
    p = doc.add_paragraph()
    set_run_font(p.add_run("目  录"), CN_FONT, 20, bold=True, color=ACCENT)
    p.paragraph_format.space_after = Pt(14)

    note = doc.add_paragraph()
    add_inline(note, "本目录已生成页码；改动正文后在 Word 中全选（Ctrl+A）按 F9 可刷新。", size=9)
    for r in note.runs:
        r.font.color.rgb = GREY

    # 只收 1~2 级：3 级标题多为「优点/缺点/什么时候用」这类重复小节，进目录只是噪音
    add_field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
    doc.add_page_break()


# ---------------------------------------------------------------- 主流程
def main():
    doc = new_document()
    build_cover(doc)
    build_toc(doc)

    parts = sorted(PARTS.glob("*.md"))
    if not parts:
        sys.exit("parts/ 下没有内容")
    for part in parts:
        render_markdown(doc, part.read_text(encoding="utf-8"))

    # 结尾收束（parts/09.md 里已有「全书完」标题，这里只补一句落款）
    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(p.add_run("AI 工程全景手册 · v1.0"), CN_FONT, 10, color=GREY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(p.add_run("原理会过时，方法不会。愿你做出能用的东西。"), CN_BODY, 10.5, color=GREY)

    doc.core_properties.title = "AI 工程全景手册"
    doc.core_properties.subject = "模型框架 / Agent / MCP / 部署 / 安全 / 变现"
    doc.core_properties.author = "AI 工程全景手册"
    doc.save(OUT)
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
