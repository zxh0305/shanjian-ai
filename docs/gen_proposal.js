const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
        Header, Footer, AlignmentType, LevelFormat, ExternalHyperlink,
        HeadingLevel, BorderStyle, WidthType, ShadingType,
        VerticalAlign, PageNumber, PageBreak } = require('docx');
const sizeOf = require('image-size');

const cjkFont = 'PingFang SC';

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

const PAGE_CONTENT_WIDTH_PX = 624;
const MAX_IMAGE_WIDTH = Math.floor(PAGE_CONTENT_WIDTH_PX * 0.9);
const MAX_IMAGE_HEIGHT = Math.floor(PAGE_CONTENT_WIDTH_PX * 1.3 * 0.6);

function safeImageRun(imagePath) {
  const data = fs.readFileSync(imagePath);
  const dims = sizeOf(data);
  let width = dims.width;
  let height = dims.height;
  if (width > MAX_IMAGE_WIDTH) { const s = MAX_IMAGE_WIDTH / width; width = MAX_IMAGE_WIDTH; height = Math.round(height * s); }
  if (height > MAX_IMAGE_HEIGHT) { const s = MAX_IMAGE_HEIGHT / height; height = MAX_IMAGE_HEIGHT; width = Math.round(width * s); }
  return new ImageRun({ type: imagePath.endsWith('.png') ? 'png' : 'jpg', data,
    transformation: { width, height }, altText: { title: "Diagram", description: "Diagram", name: "diagram" } });
}

function p(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, ...opts })], spacing: { after: 120, line: 360 } });
}
function h1(text) { return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] }); }
function h2(text) { return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] }); }
function h3(text) { return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] }); }

function cell(text, w, opts = {}) {
  return new TableCell({ borders, width: { size: w, type: WidthType.DXA },
    shading: opts.shade ? { fill: opts.shade, type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [new TextRun({ text, bold: opts.bold, size: opts.size || 20 })] })] });
}

function bullet(text) {
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun(text)], spacing: { after: 60, line: 320 } });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: { ascii: "Arial", hAnsi: "Arial", eastAsia: cjkFont }, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: { ascii: "Arial", hAnsi: "Arial", eastAsia: cjkFont } },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0, keepNext: false, keepLines: false } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: { ascii: "Arial", hAnsi: "Arial", eastAsia: cjkFont } },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1, keepNext: false, keepLines: false } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: { ascii: "Arial", hAnsi: "Arial", eastAsia: cjkFont } },
        paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 2, keepNext: false, keepLines: false } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 2000, after: 200 },
        children: [new TextRun({ text: "闪剪AI 智能体改造方案", size: 44, bold: true, font: { ascii: "Arial", hAnsi: "Arial", eastAsia: cjkFont } })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
        children: [new TextRun({ text: "从传统前后端到 Agent 中间件架构", size: 28, color: "666666", font: { ascii: "Arial", hAnsi: "Arial", eastAsia: cjkFont } })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
        children: [new TextRun({ text: "框架选型 \u00B7 架构设计 \u00B7 实施路径 \u00B7 论文方向", size: 20, color: "999999", font: { ascii: "Arial", hAnsi: "Arial", eastAsia: cjkFont } })] }),
      new Paragraph({ children: [new PageBreak()] }),

      // 一、项目现状
      h1("一、项目现状与改造目标"),
      h2("1.1 当前架构"),
      p("闪剪AI 目前是传统前后端架构：FastAPI 提供 RESTful 接口，原生 HTML/JS 单页做前端，SQLite 存储数据，FFmpeg 处理视频。LLM（DeepSeek/智谱GLM）在两个固定节点被调用：视觉分析和剪辑方案生成。整体流程是代码硬编码的线性管道。"),
      p("「核心问题：LLM 是」被调用的函数「，不是」做决策的大脑「。流程写死后，LLM 无法根据中间结果调整后续行动，无法自主选择工具，无法在失败后重新规划。"),

      h2("1.2 改造目标"),
      bullet("「将 LLM 从」被调用函数「升级为」决策中枢「，使其能自主规划任务、选择工具、评估结果"),
      bullet("引入状态管理和错误恢复机制，工具执行失败时可自动重试或调整方案"),
      bullet("支持人在回路（Human-in-the-Loop），关键剪辑决策可由用户审核确认"),
      bullet("保持现有代码资产（FFmpeg渲染、VL分析、时间线编辑）封装为 Agent 工具复用"),
      bullet("研究重点放在 Agent 中间件层（调度/容错/可观测），而非上层剪辑业务"),

      new Paragraph({ children: [new PageBreak()] }),

      // 二、框架选型
      h1("二、框架选型对比"),
      p("对 2025-2026 年主流 Agent 框架进行了调研和对比："),

      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        columnWidths: [1600, 2200, 2500, 3060],
        rows: [
          new TableRow({ cantSplit: true, children: [
            cell("「框架」, 1600, { bold: true, shade: 「D5E8F0" }),
            cell("「定位」, 2200, { bold: true, shade: 「D5E8F0" }),
            cell("「国产模型兼容」, 2500, { bold: true, shade: 「D5E8F0" }),
            cell("「适用性评价」, 3060, { bold: true, shade: 「D5E8F0" }),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("LangGraph", 1600, { bold: true }),
            cell("有向状态图编排", 2200),
            cell("通过 OpenAI Compatible API 接入 DeepSeek/智谱", 2500),
            cell("最适合：状态管理+循环迭代+工具调用+HITL", 3060),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("AutoGen/MAF", 1600, { bold: true }),
            cell("对话式多Agent（微软）", 2200),
            cell("Azure生态适配，国产支持不明", 2500),
            cell("多Agent对话强，但流程可控性不如LangGraph", 3060),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("CrewAI", 1600, { bold: true }),
            cell("角色驱动多Agent", 2200),
            cell("社区活跃，国产支持未明确", 2500),
            cell("快速原型好，复杂流程稳定性不足", 3060),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("LlamaIndex", 1600, { bold: true }),
            cell("RAG优先，Agent为辅", 2200),
            cell("可接入OpenAI Compatible", 2500),
            cell("偏检索增强，不适合工具编排场景", 3060),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("Dify", 1600, { bold: true }),
            cell("低代码Agent平台", 2200),
            cell("支持私有化，可接国产模型", 2500),
            cell("适合可视化搭建，核心逻辑仍需代码", 3060),
          ]}),
        ]
      }),
      p(""),

      h2("2.1 选型结论：LangGraph"),
      p("LangGraph 是 LangChain 团队推出的有向状态图编排框架，GitHub 34.8K Stars，被 Klarna、Cisco 等企业生产使用。选择理由："),
      bullet("显式状态管理：每个节点有清晰的输入/输出状态，可断点续跑"),
      bullet("「循环迭代：支持条件跳转和回退，适合」理解\u2192决策\u2192执行\u2192评估\u2192重规划「的循环工作流"),
      bullet("工具调用：原生支持 LangChain Tools，可封装 FFmpeg/VL/文件操作为自定义工具"),
      bullet("人在回路（HITL）：内置 interrupt 机制，关键操作可暂停等待用户确认"),
      bullet("「LangSmith 可观测性：每步推理/工具调用的 trace 可追踪，满足论文的」可观测性「要求"),
      bullet("模型中立：通过 OpenAI Compatible API 接入 DeepSeek/智谱，不绑定特定厂商"),

      new Paragraph({ children: [new PageBreak()] }),

      // 三、架构设计
      h1("三、架构设计"),
      h2("3.1 整体架构"),
      p("改造后的系统分为四层：用户层、Agent中间件层（论文核心）、工具层（现有代码封装）、基础设施层。", { bold: true }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 100 }, children: [safeImageRun('/Users/meta/Documents/AI_project/shanjian-ai/docs/architecture.png')] }),
      new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "图1：闪剪AI Agent 架构总览", size: 18, color: "666666" })] }),

      h2("3.2 Agent 中间件层（论文核心）"),
      p("这是改造的关键，也是论文的研究对象。包含四个核心组件："),

      h3("任务规划器 TaskPlanner"),
      bullet("「接收用户自然语言指令（如」把这段视频剪成15秒卡点视频，保留坦克那段「）"),
      bullet("LLM 将指令分解为有序子任务：分析素材 \u2192 筛选含坦克片段 \u2192 生成EDL \u2192 渲染 \u2192 评估"),
      bullet("输出结构化任务计划（JSON），包含每步要调用的工具和参数"),

      h3("工具路由器 ToolRouter"),
      bullet("根据任务计划，将子任务分发到对应工具"),
      bullet("处理工具调用的参数组装、结果收集、异常捕获"),
      bullet("工具调用失败时触发状态管理器的恢复流程"),

      h3("状态管理器 StateManager"),
      bullet("维护整个执行过程的状态机：当前步骤、已完成步骤、中间结果、错误记录"),
      bullet("支持状态持久化（SQLite），任务可中断后恢复"),
      bullet("错误恢复策略：自动重试（如VL模型429限流）、方案降级（AI方案失败\u2192规则引擎）、回退到上一步重新规划"),

      h3("结果评估器 Evaluator"),
      bullet("每个关键步骤完成后评估质量：渲染是否成功、成片时长是否符合用户要求、画面是否冻结"),
      bullet("「评估不通过时，触发 TaskPlanner 重新规划（如」时长不对\u2192调整片段裁剪参数\u2192重新渲染「）"),
      bullet("支持人工审核中断：关键决策（如最终成片）暂停等待用户确认后继续"),

      new Paragraph({ children: [new PageBreak()] }),

      // 四、工作流
      h1("四、智能体工作流设计"),
      p("「工作流采用 LangGraph 的有向状态图建模，核心是」评估\u2192重规划「的循环："),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 100 }, children: [safeImageRun('/Users/meta/Documents/AI_project/shanjian-ai/docs/workflow.png')] }),
      new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "图2：Agent 循环工作流（状态图）", size: 18, color: "666666" })] }),
      p(""),
      p("与传统管道的关键区别："),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        columnWidths: [4680, 4680],
        rows: [
          new TableRow({ cantSplit: true, children: [
            cell("「传统管道（当前）」, 4680, { bold: true, shade: 「D5E8F0" }),
            cell("「Agent 工作流（改造后）」, 4680, { bold: true, shade: 「D5E8F0" }),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("流程写死，线性执行", 4680),
            cell("LLM自主规划，可循环迭代", 4680),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("工具失败\u2192降级或报错", 4680),
            cell("工具失败\u2192评估\u2192重新规划\u2192换策略重试", 4680),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("用户只在开始和结束参与", 4680),
            cell("用户可在关键节点审核（HITL）", 4680),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("中间结果不可追溯", 4680),
            cell("每步状态可持久化、可恢复", 4680),
          ]}),
        ]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 五、工具定义
      h1("五、工具定义（现有代码封装）"),
      p("现有代码的每个功能模块封装为 LangGraph Tool，Agent 可按需调用："),

      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        columnWidths: [1600, 2000, 2800, 2960],
        rows: [
          new TableRow({ cantSplit: true, children: [
            cell("「工具名」, 1600, { bold: true, shade: 「D5E8F0" }),
            cell("「来源」, 2000, { bold: true, shade: 「D5E8F0" }),
            cell("「功能」, 2800, { bold: true, shade: 「D5E8F0" }),
            cell("「Agent 调用场景」, 2960, { bold: true, shade: 「D5E8F0" }),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("VLAnalysis", 1600, { bold: true }),
            cell("qwen_vl.py", 2000),
            cell("抽帧+视觉模型分析画面内容", 2800),
            cell("理解素材内容，判断精彩时段", 2960),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("EDLGenerator", 1600, { bold: true }),
            cell("qwen_vl.py", 2000),
            cell("LLM生成剪辑决策方案", 2800),
            cell("根据内容和用户指令生成剪辑方案", 2960),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("FFmpegRender", 1600, { bold: true }),
            cell("renderer.py", 2000),
            cell("视频拼接+转场+混音渲染", 2800),
            cell("执行剪辑方案，输出成片", 2960),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("TimelineOps", 1600, { bold: true }),
            cell("pipeline.py", 2000),
            cell("片段裁剪/排序/截断/转场设置", 2800),
            cell("Agent微调剪辑方案，无需整体重渲染", 2960),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("MusicSelect", 1600, { bold: true }),
            cell("music模块", 2000),
            cell("配乐选择和音量混音", 2800),
            cell("Agent根据内容情绪匹配配乐", 2960),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("QualityCheck", 1600, { bold: true }),
            cell("新增", 2000),
            cell("成片质量检测（时长/画面/音轨）", 2800),
            cell("评估渲染结果，决定是否重新规划", 2960),
          ]}),
        ]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 六、实施路径
      h1("六、实施路径（分四阶段）"),

      h2("阶段一：Agent 基础设施搭建（1-2周）"),
      bullet("安装 LangGraph，创建 StateGraph 状态定义"),
      bullet("将现有 VL 分析、EDL 生成、渲染功能封装为 @tool 装饰器工具"),
      bullet("实现基础状态图：START \u2192 理解 \u2192 规划 \u2192 执行 \u2192 评估 \u2192 END"),
      bullet("接入 DeepSeek/智谱 作为 Agent LLM（复用现有 llm_config.py）"),

      h2("阶段二：智能编排与错误恢复（2-3周）"),
      bullet("实现 TaskPlanner：用户自然语言 \u2192 结构化任务计划"),
      bullet("实现 StateManager：状态持久化到 SQLite，支持断点恢复"),
      bullet("实现错误恢复策略：429重试、方案降级、回退重规划"),
      bullet("添加 QualityCheck 工具：自动检测成片时长/画面冻结/音轨缺失"),
      bullet("「实现」评估\u2192重规划「循环：评估不通过时自动调整方案重试"),

      h2("阶段三：人在回路与交互优化（1-2周）"),
      bullet("实现 HITL interrupt：关键步骤暂停等待用户确认"),
      bullet("前端适配：展示 Agent 推理过程（当前步骤/计划/工具调用日志）"),
      bullet("「用户可在中途修改指令（如」这段不要了，换下一段「），Agent 重新规划"),

      h2("阶段四：论文验证与实验（2-3周）"),
      bullet("设计对比实验：传统管道 vs Agent 工作流（成功率/效率/用户满意度）"),
      bullet("采集指标：工具调用成功率、错误恢复成功率、平均规划步数、Token消耗"),
      bullet("撰写论文，重点分析 Agent 中间件层的调度/容错/可观测机制"),

      new Paragraph({ children: [new PageBreak()] }),

      // 七、论文研究角度
      h1("七、论文研究角度"),
      p("「你的方向是」AI Agent 中间件机制「（不是上层 Agent 业务应用），闪剪AI 作为验证场景。论文核心研究对象是中间件层，不是剪辑功能本身。"),

      h2("7.1 研究问题"),
      bullet("LLM Agent 在多工具协作场景下，如何可靠地进行任务分解和工具选择？"),
      bullet("工具执行失败时，中间件如何自动恢复（重试/降级/重规划），保证最终成功？"),
      bullet("如何设计状态管理机制，使长时间运行的多步骤任务可中断、可恢复、可追溯？"),
      bullet("如何评估 Agent 中间件的调度效率和资源消耗（Token/时间）？"),

      h2("7.2 论文贡献点"),
      p("1. 提出面向视频编辑场景的 Agent 中间件架构，包含任务规划/工具路由/状态管理/错误恢复四个核心组件。"),
      p("2. 设计基于状态图的错误恢复策略（自动重试\u2192方案降级\u2192回退重规划），量化分析不同恢复策略的有效性。"),
      p("3. 实现状态持久化与断点恢复机制，解决长时间多步骤任务的可靠性问题。"),
      p("4. 通过闪剪AI 进行实验验证，对比传统管道与 Agent 工作流的性能差异。"),

      h2("7.3 与"应用"的区别"),
      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        columnWidths: [4680, 4680],
        rows: [
          new TableRow({ cantSplit: true, children: [
            cell("「Agent 应用（不是你的方向）」, 4680, { bold: true, shade: 「FFCDD2" }),
            cell("「Agent 中间件（你的方向）」, 4680, { bold: true, shade: 「C8E6C9" }),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("「研究」Agent做什么「——剪辑策略、内容理解", 4680),
            cell("「研究」Agent怎么调度「——规划/路由/恢复/可观测", 4680),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("纵向业务层创新", 4680),
            cell("横向系统层机制研究", 4680),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("视频编辑是研究主体", 4680),
            cell("视频编辑是验证场景，中间件是研究主体", 4680),
          ]}),
        ]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 八、技术风险
      h1("八、技术风险与应对"),

      new Table({
        width: { size: 100, type: WidthType.PERCENTAGE },
        columnWidths: [2000, 2800, 4560],
        rows: [
          new TableRow({ cantSplit: true, children: [
            cell("「风险」, 2000, { bold: true, shade: 「D5E8F0" }),
            cell("「影响」, 2800, { bold: true, shade: 「D5E8F0" }),
            cell("「应对」, 4560, { bold: true, shade: 「D5E8F0" }),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("LLM 推理不稳定", 2000),
            cell("任务分解质量波动，工具选择错误", 2800),
            cell("设置最大步数限制+质量评估回退到规则引擎", 4560),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("Token 消耗过大", 2000),
            cell("多轮规划+工具调用消耗大量Token", 2800),
            cell("缓存中间结果、限制循环次数、用轻量模型做规划", 4560),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("国产模型工具调用能力弱", 2000),
            cell("DeepSeek/智谱的 function calling 可能不如 GPT-4", 2800),
            cell("用结构化输出(JSON)替代原生 function calling", 4560),
          ]}),
          new TableRow({ cantSplit: true, children: [
            cell("渲染耗时长", 2000),
            cell("Agent 等待工具返回时阻塞", 2800),
            cell("异步工具调用+状态轮询，不阻塞主循环", 4560),
          ]}),
        ]
      }),

      p(""),
      h2("总结"),
      p("LangGraph + 现有代码工具化 是最优路径：框架成熟、国产模型兼容、循环工作流匹配视频编辑场景、可观测性满足论文需求。改造分四阶段推进，核心工作量在中间件层（规划/路由/状态/恢复），现有业务代码大部分封装复用。论文方向聚焦 Agent 中间件机制，闪剪AI 作为验证场景。"),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync('/Users/meta/Documents/AI_project/shanjian-ai/docs/闪剪AI_智能体改造方案.docx', buffer);
  console.log('Document generated successfully');
});
