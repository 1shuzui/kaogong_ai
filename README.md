# AI 公考面试测评项目

## 1. 项目定位

这是一个面向“公考面试作答测评”的评分引擎项目，目标不是简单让大模型直接打分，而是把评分拆成更可控的工程链路：

1. 接收文本、音频、视频作答。
2. 将音视频转成可分析的 `transcript`。
3. 根据 `question_id` 读取题库配置。
4. 先做“证据抽取”，再做“证据约束评分”。
5. 对模型输出做确定性校验、修正和收敛。
6. 支持回归测试、LLM 标定和题库样本迭代。

当前核心代码位于 [ai_gongwu_backend](/home/quyu/ai_interview/ai_gongwu_backend)。

在当前本地工作区里，它同时也是 `/home/quyu/kaogong_ai` 这套完整演示工程的评分内核：

1. `ai_interview/ai_gongwu_backend`
   角色：评分引擎与落库内核。
2. `kaogong_ai/civil-interview-backend`
   角色：前端兼容业务后端。
3. `kaogong_ai/civil-interview-frontend`
   角色：客户演示用 Vue 页面。

---

## 2. 当前状态

截至 2026-05-08，项目已经完成这些核心能力：

1. FastAPI 接口可提供文本、音频、视频测评。
2. 题库支持目录式多题加载，不再局限单题。
3. 评分链路已经升级为“两阶段证据评分”：
   - 第一阶段：只抽取证据
   - 第二阶段：只基于证据打分
4. 抽象扣分 / 加分理由必须绑定 `evidence_ids`。
5. 后处理会校验：
   - 维度名是否合法
   - 分项分与总分是否一致
   - 引用证据是否能在原文中核验
   - 缺失型扣分是否真的有对应 absence 证据
6. 已支持测评结果落库和记录查询。
7. 已新增湖南题库自动导入链路，并生成高 / 中 / 低三档回归样本。
8. 已提供：
   - 确定性回归脚本
   - 真实 LLM 回归 / 标定脚本
   - `repeat` 多次采样取中位数能力
   - `writeback` 回写 `llmExpectedMin/Max` 能力
9. 湖南自动导入样本已按 `analysis / organization / interpersonal / scene` 四类题型分别生成中低档模板。
10. `--writeback` 已收紧为“只允许稳定题回写”，当前保留 3 道已确认稳定题的保护区间，其余题目继续走子集回归后再决定是否升级。
11. 语速已从 mock 改为真实时长计算，并增加固定区间判定与硬性建议文案。
12. 评分完成后会额外生成一轮“答案改动建议”，失败时不阻断主评分。
13. `evaluation_records` 已补 `duration_seconds`，接口返回、落库和记录回查都同步了新增字段。

当前仓库内除了手工题库外，还包含湖南 / 安徽两套自动生成题库：

1. 湖南题库目录：`ai_gongwu_backend/assets/questions/generated_hunan/`
2. 安徽题库目录：`ai_gongwu_backend/assets/questions/generated_anhui/`
3. 样本目录：`ai_gongwu_backend/assets/regression_samples/generated_hunan/`、`ai_gongwu_backend/assets/regression_samples/generated_anhui/`
4. 通用导入脚本：`ai_gongwu_backend/scripts/import_question_bank.py`
5. 兼容入口：`ai_gongwu_backend/scripts/import_hunan_question_bank.py`
6. `.docx` 提取脚本：`ai_gongwu_backend/scripts/extract_docx_text.py`

---

## 3. 与 kaogong_ai 的联调关系

如果你只调评分链路，本仓库就够了。

如果你要“在前端页面上向客户展示功能”，当前推荐的本地联调关系是：

```text
civil-interview-frontend (3001)
        |
        |  /api 代理
        v
civil-interview-backend (8050)
        |
        |  直接 Python 导入
        v
ai_gongwu_backend / ai_gongwu.db / 题库与评分引擎
```

这意味着：

1. 页面演示时，前端并不是直接请求 `ai_gongwu_backend`。
2. `civil-interview-backend` 会直接复用本仓库里的 `QuestionBank`、`InterviewFlowService`、`EvaluationStore`。
3. `ai_gongwu_backend` 自己单独起一个 `9000` 端口更适合做 Swagger 调试、健康检查和接口核验，不是前端必须依赖的那一层。

---

## 4. 目录结构

建议先从下面这个结构理解项目：

```text
ai_interview/
├── README.md
├── docs/
│   ├── 项目修改记录.md
│   └── 回归与标定说明.md
├── sample_sets/
│   └── README.md
├── reports/
│   └── regression/
│       ├── README.md
│       └── *.json / *.md
├── ai_gongwu_backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints/
│   │   │       └── interview.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── dependencies.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── flow.py
│   │   │   ├── evaluation_store.py
│   │   │   ├── question_bank.py
│   │   │   ├── llm/
│   │   │   │   └── client.py
│   │   │   ├── media/
│   │   │   └── scoring/
│   │   │       ├── prompts.py
│   │   │       └── calculator.py
│   │   └── main.py
│   ├── assets/
│   │   ├── questions/
│   │   │   ├── README.md
│   │   │   ├── HN-LX-20200606-01.json
│   │   │   └── generated_hunan/
│   │   └── regression_samples/
│   │       ├── README.md
│   │       └── generated_hunan/
│   ├── scripts/
│   │   ├── import_hunan_question_bank.py
│   │   ├── run_regression.py
│   │   └── run_llm_regression.py
│   ├── tests/
│   ├── requirements.txt
│   └── run.sh
└── 湖南题库源文档 / extracted 文本 / 若干手工样本
```

---

## 5. 三条核心链路

### 5.1 测评链路

核心入口是 [flow.py](/home/quyu/ai_interview/ai_gongwu_backend/app/services/flow.py)。

完整流程如下：

1. 接口层接收 `question_id` 和输入文件。
2. 文本直接进入评分；音视频先经过媒体解析。
3. 根据 `question_id` 从题库中读取单题配置。
4. 第一阶段 Prompt 只抽取原文证据。
5. 系统对证据做对齐、补充 absence 证据、结构校验。
6. 第二阶段 Prompt 只基于证据包打分。
7. `calculator.py` 做确定性后处理。
8. 若允许持久化，则把 Prompt、原始输出、最终结果一起落库。

### 5.2 题库导入链路

核心脚本是 [import_hunan_question_bank.py](/home/quyu/ai_interview/ai_gongwu_backend/scripts/import_hunan_question_bank.py)。

作用：

1. 读取仓库根目录下的湖南题库源文档提取文本。
2. 解析题干、评分标准、扣分标准、参考答案、标签等信息。
3. 自动生成题目 JSON。
4. 自动生成高 / 中 / 低三档回归样本。
5. 为每题写入：
   - `scoreBands`
   - `regressionCases`
   - `llmExpectedMin`
   - `llmExpectedMax`

### 5.3 回归 / 标定链路

当前有两套脚本：

1. [run_regression.py](/home/quyu/ai_interview/ai_gongwu_backend/scripts/run_regression.py)
   用于确定性 / 常规链路回归。
2. [run_llm_regression.py](/home/quyu/ai_interview/ai_gongwu_backend/scripts/run_llm_regression.py)
   用于真实大模型回归、区间标定和回写。

推荐顺序：

1. 先重导入题库和样本。
2. 先跑 `run_regression.py` 看生成样本排序是否合理。
3. 再跑 `run_llm_regression.py --repeat 3` 看真实模型中位数。
4. 结果稳定后，再加 `--writeback` 回写 `llmExpectedMin/Max`。

---

## 6. 关键模块说明

### 6.1 [interview.py](/home/quyu/ai_interview/ai_gongwu_backend/app/api/endpoints/interview.py)

接口层，负责：

1. 题目列表与题目详情接口
2. 文本测评接口
3. 音视频测评接口
4. 测评记录列表与详情接口

### 6.2 [schemas.py](/home/quyu/ai_interview/ai_gongwu_backend/app/models/schemas.py)

数据合同层，定义：

1. 题目结构
2. 两阶段证据结构
3. 评分结果结构
4. 题目分档与回归样本结构
5. `duration_seconds`、语速字段、`answer_revision_suggestion`

当前题库回归相关字段主要是：

1. `scoreBands`
2. `regressionCases`
3. `llmExpectedMin`
4. `llmExpectedMax`

### 6.3 [prompts.py](/home/quyu/ai_interview/ai_gongwu_backend/app/services/scoring/prompts.py)

Prompt 构造层，负责：

1. 第一阶段证据抽取 Prompt
2. 第二阶段证据约束评分 Prompt
3. 评分后“答案改动建议” Prompt
4. 按题目动态生成本土化 / 岗位化提示，不再写死河南模板

### 6.4 [calculator.py](/home/quyu/ai_interview/ai_gongwu_backend/app/services/scoring/calculator.py)

确定性后处理层，负责：

1. 证据对齐
2. absence 证据补充
3. 理由与证据绑定校验
4. 分数收敛和排序校准
5. 规则型兜底评分
6. 语速判定与硬性建议文案

---

## 7. 环境准备

推荐使用 Python 3.10 及以上版本。

当前本地建议统一使用项目根目录下的虚拟环境：

```bash
cd /home/quyu/ai_interview
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip setuptools wheel
```

然后安装评分引擎和 `kaogong_ai` 兼容后端依赖：

```bash
cd /home/quyu/ai_interview
./.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch
./.venv/bin/pip install -r ai_gongwu_backend/requirements.txt
./.venv/bin/pip install -r /home/quyu/kaogong_ai/civil-interview-backend/requirements.txt
./.venv/bin/pip install python-dotenv
```

说明：

1. 本地联调优先推荐 CPU 版 `torch`
2. 先单独装 `torch`，再装其余依赖，可以避免 `pip` 自动拉取体积更大的 CUDA 版包

前端依赖单独安装：

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm install
```

系统依赖建议：

1. `ffmpeg`
2. `torch`
3. `openai-whisper`
4. `opencv-python-headless`

当前本机已验证：

1. `ffmpeg` 可用
2. 根 `.venv` 可用
3. `civil-interview-frontend` 可完成 `npm run build`

---

## 8. 环境变量

建议在 [ai_gongwu_backend](/home/quyu/ai_interview/ai_gongwu_backend) 下准备 `.env`：

```env
LLM_PROVIDER=DEEPSEEK
LLM_API_KEY=你的 DeepSeek 密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-v4-flash

QUESTION_DB_PATH=assets/questions
ASR_PROVIDER=whisper
ASR_DEVICE=cpu
WHISPER_MODEL_SIZE=base
WHISPER_CPU_THREADS=4
WHISPER_LANGUAGE=zh
FUNASR_MODEL_NAME=paraformer-zh
FUNASR_MODEL_REVISION=v2.0.4
FUNASR_VAD_MODEL_NAME=fsmn-vad
FUNASR_VAD_MODEL_REVISION=v2.0.4
FUNASR_PUNC_MODEL_NAME=ct-punc
FUNASR_PUNC_MODEL_REVISION=v2.0.4
MODELSCOPE_CACHE=storage/modelscope_cache
ENABLE_VISUAL_ANALYSIS=true

MIN_VALID_WORDS=15
MIN_WORDS_PENALTY_RATIO=0.2
SCORE_TOLERANCE=2.0
MAX_RATIONALE_CHARS=400
```

说明：

1. `QUESTION_DB_PATH` 现在默认应指向目录，而不是单个题目文件。
2. 若未配置 `LLM_API_KEY`，系统会回退到确定性评分兜底。
3. `ASR_PROVIDER` 当前支持 `whisper` 和 `funasr`，需要对比实验时直接切换即可。

---

## 9. 启动项目

如果你要看本地启动、日常维护、测试与排障的完整操作手册，请优先阅读 [docs/使用与维护与测试说明.md](docs/使用与维护与测试说明.md)。

### 方式一：标准命令启动

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
uvicorn app.main:app --reload --port 9000
```

### 方式二：直接运行入口文件

```bash
python /absolute/path/to/ai_gongwu_backend/app/main.py
```

也支持在 `ai_gongwu_backend` 目录内使用模块方式启动：

```bash
python -m app.main
```

### 方式三：运行脚本

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
bash run.sh
=======
### 9.1 只启动评分引擎

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
/home/quyu/ai_interview/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
>>>>>>> Stashed changes
```

启动后访问：

```text
http://127.0.0.1:9000/docs
http://127.0.0.1:9000/health
```

### 9.2 启动客户演示最小闭环

页面演示推荐至少起这两层：

1. `civil-interview-backend`
2. `civil-interview-frontend`

如果只是本地演示，先强制走规则兜底，避免页面因为模型密钥或外网抖动而失败：

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
LLM_API_KEY='' COMPAT_FORCE_RULE_BASED=true /home/quyu/ai_interview/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8050
```

再起前端：

```bash
cd /home/quyu/kaogong_ai/civil-interview-frontend
npm run dev -- --host 127.0.0.1 --port 3001
```

页面地址：

```text
http://127.0.0.1:3001/
```

说明：

1. 前端默认把 `/api` 代理到 `http://127.0.0.1:8050`
2. 因此前端演示时，`8050` 必须在线
3. `9000` 端口不是前端必须依赖，但建议同时开着，便于你看 Swagger 和原始引擎输出

### 9.3 使用真实模型联调

如果你要演示真实大模型评分：

1. 确保 [ai_gongwu_backend/.env](/home/quyu/ai_interview/ai_gongwu_backend/.env) 里有有效 `LLM_API_KEY`
2. 启动 `civil-interview-backend` 时不要再传 `COMPAT_FORCE_RULE_BASED=true`

示例：

```bash
cd /home/quyu/kaogong_ai/civil-interview-backend
/home/quyu/ai_interview/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8050
```

---

## 10. 如何测试和演示

### 10.1 我已经本地验证通过的项

1. 评分引擎健康检查：
   - `GET http://127.0.0.1:9000/health`
2. 兼容后端题库接口：
   - `GET http://127.0.0.1:8050/questions?page=1&pageSize=2`
3. 兼容后端评分接口：
   - `POST http://127.0.0.1:8050/scoring/evaluate`
4. 前端构建：
   - `npm run build`
5. 前端开发页：
   - `http://127.0.0.1:3001/`

### 10.2 你自己本地最推荐的测试顺序

1. 打开 `http://127.0.0.1:3001/`
2. 先登录
   兼容后端当前支持“首次登录自动创建用户”
3. 进入题库页
   检查题目是否能正常加载
4. 进入练习或考试页
   先用文本评分链路做演示，最稳定
5. 提交一次作答
   观察结果页、维度分、评语、关键词命中
6. 打开历史记录页
   确认刚才的测评已入库并能回查

### 10.3 给客户演示时建议优先展示的页面

1. 首页 / 登录页
2. 题库列表页
3. 考试准备页
4. 考试作答页
5. 结果页
6. 历史记录页
7. 定向备面 / 专项训练页

### 10.4 演示时最稳的策略

1. 如果网络或模型稳定性不确定，先用：
   - `LLM_API_KEY=''`
   - `COMPAT_FORCE_RULE_BASED=true`
2. 如果客户要看“真实模型效果”，再切回真实模型配置
3. 音频录制演示前，先确认浏览器已授权麦克风
4. 如果只是展示流程，不一定要先演示视频上传，文本和音频已经足够说明链路

---

## 11. 主要接口

### 11.1 题目接口

1. `GET /api/v1/interview/questions`
2. `GET /api/v1/interview/questions/{question_id}`

### 11.2 测评接口

1. `POST /api/v1/interview/evaluate`
   音频 / 视频输入
2. `POST /api/v1/interview/evaluate/text`
   文本输入

### 11.3 测评记录接口

1. `GET /api/v1/interview/records`
2. `GET /api/v1/interview/records/{record_id}`

---

## 12. 常用脚本

### 10.1 重新提取 / 导入题库

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
./venv/bin/python scripts/extract_docx_text.py ../2020-2025第二批次完全版.docx
./venv/bin/python scripts/import_question_bank.py --profile anhui
./venv/bin/python scripts/import_question_bank.py --profile hunan
```

执行后会刷新：

1. `assets/questions/generated_hunan/` 或 `assets/questions/generated_anhui/`
2. `assets/regression_samples/generated_hunan/` 或 `assets/regression_samples/generated_anhui/`
3. 对应目录下的 `import_summary.txt`

### 12.2 跑确定性回归

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
/home/quyu/ai_interview/.venv/bin/python scripts/run_regression.py
```

### 12.3 跑真实 LLM 回归

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
/home/quyu/ai_interview/.venv/bin/python scripts/run_llm_regression.py --repeat 3
```

### 12.4 跑真实 LLM 回归并回写区间

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
/home/quyu/ai_interview/.venv/bin/python scripts/run_llm_regression.py --repeat 3 --writeback
```

### 10.5 跑 ASR 小批量基准

```bash
cd /home/quyu/ai_interview/ai_gongwu_backend
./venv/bin/python scripts/benchmark_asr.py
```

说明：

1. `--repeat 3` 用多次采样中位数抵消单次模型波动。
2. `--writeback` 现在只会对“高 / 中 / 低三档都通过、排序正确、波动可接受”的稳定题目回写 `llmExpectedMin/Max`。
3. 真正批量标定前，建议先用 `--question-id` 跑小子集。
4. `benchmark_asr.py` 会对 `Whisper` 和 `FunASR` 各做一次 warm-up，再对 3 条小样本输出 `reports/asr/` 对比报告。

---

## 13. 题库与样本文件怎么理解

### 13.1 单题 JSON

每题一个 JSON，至少包含：

1. `id`
2. `type`
3. `province`
4. `fullScore`
5. `question`
6. `dimensions`

建议同时包含：

1. `scoreBands`
2. `regressionCases`
3. `sourceDocument`
4. `referenceAnswer`
5. `tags`

### 13.2 regressionCases

当前约定每题至少有 3 条：

1. 文档高分基准答案
2. 程序化中档参考答案
3. 程序化低档参考答案

其中：

1. `expected_min/max` 主要对应当前确定性排序结果
2. `llmExpectedMin/Max` 对应真实大模型回归后的推荐区间

### 13.3 generated_hunan

这是脚本自动生成目录，不建议手工逐个改动。  
如果你调整了导入或样本生成规则，应重新运行导入脚本，让生成产物整体刷新。

---

## 14. 当前文档索引

如果你是日常维护者，建议先看 [docs/使用与维护与测试说明.md](docs/使用与维护与测试说明.md)；本 README 继续主要承担项目总览职责。

如果你是日常维护者，建议先看 [docs/使用与维护与测试说明.md](docs/使用与维护与测试说明.md)；本 README 继续主要承担项目总览职责。

1. [docs/项目修改记录.md](/home/quyu/ai_interview/docs/项目修改记录.md)
2. [docs/使用与维护与测试说明.md](docs/使用与维护与测试说明.md)
3. [docs/回归与标定说明.md](/home/quyu/ai_interview/docs/回归与标定说明.md)
4. [ai_gongwu_backend/assets/questions/README.md](/home/quyu/ai_interview/ai_gongwu_backend/assets/questions/README.md)
5. [ai_gongwu_backend/assets/regression_samples/README.md](/home/quyu/ai_interview/ai_gongwu_backend/assets/regression_samples/README.md)
6. [reports/regression/README.md](/home/quyu/ai_interview/reports/regression/README.md)
7. [sample_sets/README.md](/home/quyu/ai_interview/sample_sets/README.md)

---

## 15. 当前注意事项

1. `sample_sets/` 主要是早期人工整理的河南样本分类目录，不等同于当前 `generated_hunan` 回归集。
2. 真实 LLM 分数仍然会抖动，所以正式标定建议固定使用 `--repeat 3`。
3. 组织策划题和综合分析题现在已经拆成独立的中低档模板生成器，但仍建议持续做题型级微调。
4. 如果修改了：
   - `prompts.py`
   - `calculator.py`
   - `import_hunan_question_bank.py`
   最好同步重跑导入和回归，而不是只测单条接口。
5. 当前仓库本身没有单独的前端工程；你要做页面演示时，应使用同机的 `kaogong_ai/civil-interview-frontend`。

---

## 16. 后续建议

当前最值得继续推进的方向：

1. 对剩余题型继续做模板化样本生成，而不是统一抽句降档。
2. 把全量 `repeat=3` 标定跑完，并持续回写 `llmExpectedMin/Max`。
3. 为关键题型建立人工标注对照集，校验 LLM 中位数与人工目标分差。
4. 给回归脚本补题型分组统计和异常样本自动汇总。
5. 对测评记录增加“人工复核状态”和“版本号”字段，便于后续追踪。
