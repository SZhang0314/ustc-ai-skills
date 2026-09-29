# report.json Schema

唯一内容源。三个生成器（docx / tex / pdf）都读取此文件。
所有公式使用 LaTeX 数学语法；在 JSON 字符串中反斜杠写作 `\\`。

## 顶层结构

```jsonc
{
  "meta": {
    "title": "用示波器观测 RLC 电路的暂态过程",   // 实验题目
    "author": "姓名",
    "student_id": "学号",
    "course": "大学物理实验",
    "institution": "中国科学技术大学",
    "department": "物理学院",
    "instructor": "指导教师",
    "date": "2026-09-20",
    "type": "实验报告"          // 文档类型，用于页眉/标题
  },

  "abstract": "本文通过……（摘要正文，200-400 字）。",

  "keywords": ["RLC 电路", "暂态过程", "阻尼振荡", "不确定度"],

  "introduction": [
    "第一段：研究背景与意义。",
    "第二段：本实验要解决的问题与本文结构安排。"
  ],

  "purpose": [
    "1. 掌握用示波器观测 RLC 电路暂态过程的方法。",
    "2. 测定电路的时间常数与品质因数。",
    "3. 学习不确定度的评定与数据处理方法。"
  ],

  "principle": [
    { "heading": "2.1 二阶电路的微分方程", "body": ["段落文本...", "$$L\\frac{d^2q}{dt^2}+R\\frac{dq}{dt}+\\frac{q}{C}=0$$", "对式(1)两边除以 $L$ 得……"] },
    { "heading": "2.2 三种阻尼情形", "body": ["..."] },
    { "heading": "2.3 物理图像解释", "body": ["..."] }
  ],

  "content": {
    "apparatus": [
      { "name": "数字示波器", "model": "TBS1102", "qty": "1", "usage": "观测并记录电压波形" },
      { "name": "函数信号发生器", "model": "DG1022Z", "qty": "1", "usage": "提供方波激励" }
    ],
    "design": {
      "overview": ["实验总体设计段落..."],
      "uncertainty": {
        "intro": ["不确定度评定按 JJF 1059.1-2012 进行……"],
        "type_a": {
          "title": "A 类不确定度",
          "body": [
            "对某一量 $x$ 进行 $n$ 次等精度测量，A 类不确定度为",
            "$$u_A(x)=\\frac{s(x)}{\\sqrt{n}}=\\sqrt{\\frac{\\sum_{i=1}^{n}(x_i-\\bar{x})^2}{n(n-1)}}$$",
            "其中 $\\bar{x}=\\frac{1}{n}\\sum x_i$ 为算术平均值，$s(x)$ 为样本标准差。"
          ]
        },
        "type_b": {
          "title": "B 类不确定度",
          "body": [
            "由仪器误差限 $\\Delta_{ins}$ 估计的 B 类不确定度为",
            "$$u_B(x)=\\frac{\\Delta_{ins}}{\\sqrt{3}}\\quad(\\text{均匀分布})$$",
            "对数字仪表读数分辨力 $\\delta$，有 $u_B(\\delta)=\\frac{\\delta}{2\\sqrt{3}}$。"
          ]
        },
        "combined": {
          "title": "合成不确定度与扩展不确定度",
          "body": [
            "$$u_C(x)=\\sqrt{u_A^2(x)+u_B^2(x)}$$",
            "$$U=k\\,u_C(x),\\quad k=2\\ (P=95\\%)$$"
          ]
        }
      }
    },
    "procedure": [
      { "heading": "4.1 电路搭建", "body": ["..."] },
      { "heading": "4.2 波形观测", "body": ["..."] }
    ]
  },

  "data_processing": {
    "intro": ["数据处理方法与公式说明，含不确定度传播……"],
    "tables": [
      {
        "caption": "表 1  RLC 电路阻尼振荡周期测量数据",
        "columns": ["次数 $i$", "$T_i$/ms", "$u_A(T_i)$/ms", "$u_B(T_i)$/ms"],
        "rows": [
          ["1", "1.204", "0.003", "0.002"],
          ["2", "1.201", "0.003", "0.002"]
        ],
        "note": "仪器误差限 $\\Delta=0.002$ ms。"
      }
    ],
    "steps": [
      "1. 由表 1 计算平均值 $\\bar{T}=1.202$ ms。",
      "2. 合成不确定度：$$u_C(T)=\\sqrt{u_A^2+u_B^2}=0.0036\\ \\text{ms}$$",
      "3. 最终结果：$T=(1.202\\pm0.007)$ ms，$k=2$。"
    ],
    "figures": [
      { "path": "figs/curve.png", "caption": "图 1  阻尼振荡电压波形拟合", "width_cm": 12 }
    ]
  },

  "conclusion": {
    "summary": [
      "本实验通过……，得到主要结果如下……",
      "结果与理论值比较：相对偏差 1.2%，在不确定度范围内相符。"
    ],
    "discussion": [
      "误差来源分析……",
      "改进建议……"
    ],
    "questions": [
      {
        "q": "思考题 1：为什么过阻尼时不出现振荡？",
        "a": ["过阻尼时特征方程有两不等实根……（含公式 $\\Delta=R^2-4L/C>0$）……"]
      },
      {
        "q": "思考题 2：如何由波形测量品质因数 $Q$？",
        "a": ["由相邻同向峰值之比…… $Q=\\pi/\\ln(A_n/A_{n+1})$。"]
      }
    ]
  },

  "references": [
    "[1] 张三, 李四. 大学物理实验[M]. 3版. 北京: 高等教育出版社, 2020: 125-131.",
    "[2] 国家质量监督检验检疫总局. JJF 1059.1-2012 测量不确定度评定与表示[S]. 北京: 中国计量出版社, 2012."
  ]
}
```

## 字段规则

| 字段 | 说明 |
| --- | --- |
| `meta.*` | 均可省略；缺失时填空或省略对应显示。 |
| `abstract` | 字符串，一段即可。 |
| `keywords` | 字符串数组，生成时用 `；` 或 `,` 连接。 |
| `introduction` / `purpose` | 段落/条目字符串数组。`purpose` 按原材料写。 |
| `principle[]` | `{heading, body}`；`body` 内可混排正文与 `$$公式$$`。 |
| `content.apparatus[]` | `{name, model, qty, usage}`。 |
| `content.design.uncertainty` | **必填**，须含 type_a / type_b / combined 公式。 |
| `content.procedure[]` | `{heading, body}`。 |
| `data_processing` | `intro`,`tables`,`steps`,`figures`；不确定度在此体现。 |
| `tables[].columns/rows` | 字符串二维数组；单元格内可含行内公式。 |
| `conclusion` | `summary`,`discussion`,`questions[]{q,a}`。 |
| `references` | GB/T 7714 字符串数组，自带 [n] 编号。 |

## 约定
- 数字与单位之间留空格：`1.202 ms`。
- 不确定度写法：`(1.202 \pm 0.007)`。
- 公式编号由生成器自动添加，正文引用用 `(1)` `(2)` 手工对齐或由用户统一。
- 图片路径相对于 `report.json` 所在目录或 `--outdir`。
