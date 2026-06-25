---
name: english-gaokao-test-creator
description: >
  Create original English test papers aligned with China's New Gaokao I format by crawling foreign news articles,
  selecting base texts, and generating Word documents with answer keys and analysis.
  当用户需要制作英语原创题、原创试题、高考模拟题、新高考英语题、听力/阅读/语言运用/写作题型，
  或想把 NPR / The Guardian 等外文新闻改编成中国高考英语题时，立即使用本 skill。
  主题可更换，题型覆盖新高考 I 卷全部四个部分。即使没有出现 "skill" 或 "word" 关键词，只要任务涉及上述场景也要调用。
compatibility: Python 3.10+, requests, beautifulsoup4, lxml, python-docx
---

# 新高考 I 卷英语原创题生成器

## 触发场景

当用户提到以下任一需求时立即使用本 skill：

- 制作 / 生成 / 编写英语原创题、原创试题、高考模拟题、新高考英语题
- 需要根据外文新闻报道生成听力、阅读、语言运用、写作等题型
- 把国外主流新闻文章改编成中国高考英语题
- 需要输出 Word 试卷、答案、解析、基本信息表
- 爬取 NPR、The Guardian 等外文语料并生成试题
- 要求更换主题、覆盖全部新高考题型

即使没出现 "skill" 或 "word" 关键词，只要任务符合上述场景也要调用。

## 能力范围

- 默认生成一套完整的 **新高考全国 I 卷英语试卷**，包含：
  - 第一部分 听力（脚本 + 试题；不生成音频）
  - 第二部分 阅读（阅读理解 4 篇 + 七选五 1 篇）
  - 第三部分 语言运用（完形填空 + 语法填空）
  - 第四部分 写作（应用文 + 读后续写）
- 用户可指定只生成某一部分或某几部分。
- 主题由用户指定，默认 **人与社会**；可更换为 **人与自我**、**人与自然** 或跨主题组合。
- 语料来源默认 NPR Education、The Guardian Society/World；用户可指定其它 RSS/站点，若站点结构未知则先尝试通用 RSS 解析，失败时向用户报告。

## 依赖

运行脚本需要 Python 3.10+ 与以下包（无则指导用户 pip install --user 或创建 venv）：

- requests
- beautifulsoup4
- lxml
- python-docx

不要私自使用 sudo 安装。

## 工作流

1. **确认需求**
   - 解析：parts（默认全部四部分）、theme、output_dir、difficulty、source_sites、是否使用现有语料。
   - 若用户提供评选方案 PDF 或空表 docx，读取并遵循；否则使用内置默认参数。
   - output_dir 默认取用户当前工作目录下的 `英语原创题_<YYYYMMDD>`，或用户指定的目录。

2. **准备输出目录**
   - 创建 output_dir 及其子目录（如 `原始语料_<theme>/`）。

3. **采集语料**
   - 若用户未提供现有语料目录，运行：
     ```bash
     python scripts/crawl_corpus.py \
       --out-dir <output_dir> \
       --theme <theme> \
       --sources npr guardian \
       --max-per-source 10 \
       --briefing <output_dir>/语料采集简报.html
     ```
   - 保存为 `原始语料_<theme>/` 下的 markdown，带 YAML frontmatter（title, source, url, pub_date, word_count）。
   - 生成 `语料采集简报.html`，包含标题、来源、字数、摘要，正文可折叠。
   - 把简报路径和文章列表展示给用户，请用户挑选各题型所需文章；用户也可回复“自动选择”。

4. **改编语料**
   - 根据所选题型控制长度：
     - 听力长对话脚本：150-250 词
     - 阅读理解 A/B/C/D：200-400 词
     - 七选五：250-350 词
     - 完形填空：300-380 词
     - 语法填空：200-280 题
     - 读后续写：350-450 词
   - 同一篇文章不重复使用；如需缩短，保留核心情节 / 论点，删除次要细节。
   - 控制难度：整体约 0.60，具体按题型调整。

5. **命题（必须严格符合新高考 I 卷题量）**
   - 听力：第一节 5 段短对话，每段 1 题；第二节 4-5 段长对话 / 独白，共 15 题。
   - 阅读理解：A、B、C、D 四篇，每篇 5 题，共 15 题。
   - 七选五：1 篇，5 个空，7 个选项。
   - 完形填空：1 篇，15 个空，每空 4 个选项。
   - 语法填空：1 篇，10 个空。
   - 应用文：1 题。
   - 读后续写：1 题，续写两段。
   - 生成题目后必须自检题量，不足则补充，超出则删减。
   - 标注答案，并对每道题写解析（考点 + 思路）。

6. **生成 Word**
   - 创建 JSON 试卷规格文件 `test_spec.json`（格式见下文）。
   - 运行：
     ```bash
     python scripts/build_test_docx.py \
       --spec test_spec.json \
       --out <output_dir>/<试卷文件名>.docx
     ```
   - 若用户提供了空表模板，在 `test_spec.json` 中指定 `form_template_path` 和 `form_output_path`，脚本会自动按标签匹配填充；否则在 Word 末尾嵌入基本信息表。

7. **交付**
   - 列出所有输出文件路径，并提示用户检查。

## 输入与默认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| parts | 全部四部分 | 可指定任意组合，如 `part3` / `reading,writing` |
| theme | 人与社会 | 可更换为任意主题语境 |
| sources | npr, guardian | 用逗号分隔，如 `npr,guardian,bbc` |
| max-per-source | 10 | 每个源最多爬取文章数 |
| difficulty | 0.60 | 整体难度预估值 |
| output_dir | 当前工作目录 / 英语原创题_<日期> | 用户可指定 |
| existing_corpus | 无 | 若提供，跳过爬取直接使用 |
| criteria_pdf | 无 | 可选 |
| form_template | 无 | 可选 |

## 输出文件

默认输出：

- `<output_dir>/原始语料_<theme>/`：带 YAML frontmatter 的 markdown 语料文件
- `<output_dir>/语料采集简报.html`
- `<output_dir>/<title>.docx`：完整 Word 试卷（含试题、答案、解析、基本信息表）

若提供了空表模板，额外输出：

- `<output_dir>/原创试题基本信息表_已填写.docx`

## Word 格式规范

- 页面：A4，上下左右 2.54 cm
- 大标题：黑体 18 磅加粗居中
- 章节标题：黑体 12 磅加粗
- 英文正文：Times New Roman 12 磅（小四）
- 中文说明与解析：宋体 12 磅
- 行距：1.5 倍
- 选项行左侧缩进 0.5 cm
- 基本信息表：2 列，表头居中加粗，内容 1.5 倍行距

## 新高考 I 卷默认结构

| 部分 | 题型 | 题量 / 分值 | 说明 |
|------|------|-------------|------|
| 第一部分 听力 | 第一节 短对话 | 5 题 × 1.5 | 每段对话 1 题 |
| | 第二节 长对话 / 独白 | 15 题 × 1.5 | 共 4-5 段 |
| 第二部分 阅读 | 第一节 阅读理解 | 15 题 × 2.5 | A、B、C、D 四篇 |
| | 第二节 七选五 | 5 题 × 2.5 | 1 篇，7 选 5 |
| 第三部分 语言运用 | 第一节 完形填空 | 15 题 × 1 | 四选一 |
| | 第二节 语法填空 | 10 题 × 1.5 | 填 1 词或括号内正确形式 |
| 第四部分 写作 | 第一节 应用文 | 1 题 × 15 | 书信 / 通知 / 演讲稿等 |
| | 第二节 读后续写 | 1 题 × 25 | 根据短文续写两段 |

如果用户只要求某一部分，按该部分生成即可。

## JSON 试卷规格（test_spec.json）

`sections` 数组中的每个对象代表一个大题，支持以下字段：

- `heading`：大题标题
- `instructions`：答题说明
- `passage`：正文（可选），按空行分段
- `items`：小题列表，每个小题可包含 `num`、`question`、`options`（A/B/C/D）、`answer`
- `options`：完形填空选项列表（每个元素含 `num`、`A`、`B`、`C`、`D`）
- `answers`：语法填空答案列表（每个元素含 `num`、`answer`）
- `gap_options`：七选五的 7 个选项句子
- `writing_prompts`：写作题列表（每个元素含 `num`、`type`、`prompt`、`word_count`、`sample` 等）

```json
{
  "title": "2026 年常德市中学英语原创题评选",
  "sections": [
    {
      "heading": "第三部分  语言运用（共两节，满分 30 分）",
      "instructions": "",
      "subsections": [
        {
          "heading": "第一节  完形填空（共 15 小题；每小题 1 分，满分 15 分）",
          "instructions": "阅读下面短文，从短文后各题所给的 A、B、C、D 四个选项中，选出可以填入空白处的最佳选项。",
          "passage": "The Santa Fe Indian School ... 41_____ ...",
          "options": [
            {"num": "41", "A": "imagine", "B": "expect", "C": "remember", "D": "consider"}
          ]
        },
        {
          "heading": "第二节  语法填空（共 10 小题；每小题 1.5 分，满分 15 分）",
          "instructions": "阅读下面短文，在空白处填入 1 个适当的单词或括号内单词的正确形式。",
          "passage": "PHILADELPHIA ... 56_____ (gather) ...",
          "answers": [
            {"num": "56", "answer": "had gathered"}
          ]
        }
      ]
    }
  ],
  "answer_key": [
    {"section": "第三部分  语言运用", "lines": ["41-45  BACCA", "46-50  DDCCD", "51-55  DABAD", "56. had gathered", "57. a", "..."]}
  ],
  "analysis": {
    "第三部分  语言运用": [
      {"num": "41", "answer": "B", "explanation": "expect。根据上下文..."},
      {"num": "56", "answer": "had gathered", "explanation": "考查动词时态..."}
    ]
  },
  "basic_info_form": [
    {"label": "考查内容", "value": "..."},
    {"label": "试题来源", "value": "..."},
    {"label": "对应课程标准", "value": "..."},
    {"label": "命题意图", "value": "..."},
    {"label": "难度预估", "value": "..."}
  ],
  "form_template_path": null,
  "form_output_path": null
}
```

## 质量控制清单

生成完成后必须检查：

- 各题型题量与分值符合新高考 I 卷结构。
- 选项互斥，正确答案不重复出现在同一题的干扰项中。
- 语法填空括号内的提示词形式正确（动词用原形等）。
- 定语从句先行词与关系词一致（人/物/whose）。
- 同一篇文章不在多个题型中重复使用。
- 信息表中的来源 URL 与语料 frontmatter 一致。
- 课程标准版本号使用用户给定版本，否则使用《普通高中英语课程标准》（2017 年版 2025 年修订）。
- 文档无 emoji、无多余空行、字号统一。

## 脚本使用说明

### crawl_corpus.py

```bash
python scripts/crawl_corpus.py \
  --out-dir DIR \
  --theme THEME \
  --sources npr,guardian \
  --max-per-source 10 \
  --briefing DIR/语料采集简报.html
```

### build_test_docx.py

```bash
python scripts/build_test_docx.py \
  --spec test_spec.json \
  --out test.docx
```

## 示例用户 prompt

> 帮我做一套 2026 常德市中学英语原创题，主题人与社会，包含听力、阅读、语言运用和写作，输出到桌面/英语原创题。

> 只要第三部分，主题换成人与自然，语料用 NPR 的 Science 栏目。
