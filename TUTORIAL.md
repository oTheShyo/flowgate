# flowgate 完全教程：用 66 个问题从安装走到生产

这份教程按问题组织。每个问题都对应一个你在接入时会真实遇到的岔路口，答案尽量给到代码级，而不是停留在概念。

**读法建议**：第一次读，按顺序读完第一到第三部分（定位、跑起来、机制），这三部分决定了你后面会不会用错。第四部分之后可以按需跳读。

**版本**：对应 `flowgate` 1.2.0，Python 3.9+，TypeScript 5.x。

**约定**：文中出现的 `agent` 均指 `CascadeAgent` 实例；代码默认在 `async` 上下文中运行，`run()` 是协程。

---

## 目录

- [第一部分 定位：它到底解决什么问题](#第一部分-定位它到底解决什么问题)
- [第二部分 跑起来](#第二部分-跑起来)
- [第三部分 机制：级联如何工作](#第三部分-机制级联如何工作)
- [第四部分 路由：把请求送到正确的模型](#第四部分-路由把请求送到正确的模型)
- [第五部分 成本](#第五部分-成本)
- [第六部分 流式输出](#第六部分-流式输出)
- [第七部分 工具调用](#第七部分-工具调用)
- [第八部分 Harness：预算、KPI、合规](#第八部分-harness预算kpi合规)
- [第九部分 不花钱的验证](#第九部分-不花钱的验证)
- [第十部分 集成](#第十部分-集成)
- [第十一部分 配置与部署](#第十一部分-配置与部署)
- [第十二部分 扩展开发](#第十二部分-扩展开发)
- [第十三部分 排错](#第十三部分-排错)
- [第十四部分 这个仓库的现状](#第十四部分-这个仓库的现状)
- [附录 A 模块地图](#附录-a-模块地图)
- [附录 B 术语表](#附录-b-术语表)

---

# 第一部分 定位：它到底解决什么问题

### Q1. flowgate 是什么？

一个**库**，不是框架，也不是网关。它嵌在你的 agent 循环内部，在每次模型调用之前做决策：这次该用哪个模型、花多少钱、要不要拦下来。

它的自我定位是 "in-process intelligence layer" —— 进程内的智能层。关键词是**进程内**：它不需要你把请求发到另一个服务再转发回来。

核心 API 只有三个东西：

```python
from flowgate import CascadeAgent, ModelConfig

agent = CascadeAgent(models=[便宜模型, 贵模型])
result = await agent.run("你的问题")
```

### Q2. 它和 LiteLLM、OpenRouter 这类网关有什么区别？

差在**决策位置**。

| 维度 | 外部网关 | flowgate |
|---|---|---|
| 看到的东西 | HTTP 请求边界 | agent 执行循环内部 |
| 能拿到 agent 状态 | 拿不到 | 能拿到（当前第几步、用了哪些工具、还剩多少预算） |
| 决策粒度 | 整个请求 | 单次模型调用、单次工具调用 |
| 额外延迟 | 10–50ms 网络往返 | 官方标称 < 5ms |
| 能否拦截 | 一般只观察 | 能 `stop` / `deny_tool` / `switch_model` |

一个具体差别：网关不知道"这是 agent 第 7 步，前面已经花了 0.8 美元"，flowgate 知道。所以它能做"这一步太贵了，降级"这种决策。

### Q3. "级联"到底做了什么？

三个步骤：

1. **先让便宜模型试**（drafter）。它给出一个答案。
2. **给这个答案打分**（quality score），跟当前难度对应的阈值比。
3. **分够了就返回，分不够才叫贵的**（verifier）重答。

只有第 3 步发生时才付两次钱。所以级联的收益完全取决于一个比例：**有多大比例的请求，小模型的答案能过关**。

这个比例叫**接受率**（acceptance rate）。代码注释里写的设计目标是 50–60%。

### Q4. 省钱的原理是什么？

不是"小模型更便宜"这么简单，真正的假设是：**大多数请求不需要旗舰模型**。

文档里的论证是 40–70% 的查询不需要慢而贵的旗舰模型，而且领域专用的小模型在专门任务上常常打赢通用大模型。

所以省钱的公式近似是：

```
节省比例 ≈ 接受率 × (1 - 小模型单价 / 大模型单价)
```

接受率 55%、单价差 16 倍（0.375 对 6.25 美元每百万 token）时，理论上省一半以上。这也是为什么 README 敢写 69%、93% 这些数——它们强烈依赖你的查询分布。

### Q5. 什么样的负载能省钱？

省钱的负载长这样：

- 请求量足够大，且**难度分布偏简单**（客服问答、分类、信息抽取、格式转换、简单代码补全）
- 答案质量有**可自动判定的标准**（有参考答案、有结构约束、有相似度可比）
- 质量不达标时**允许重试**，多花一次钱不会造成业务事故

反例：一次生成就要交付给客户的合同条款，重试的代价远大于省下的钱。

### Q6. 什么场景不该用？

- **质量零容忍**：医疗诊断、法律意见、金融合规文本。哪怕 3% 的质量下降也不可接受。
- **单模型系统**：只有一个模型，级联无从谈起（代码会打 warning 并自动关掉级联）。
- **请求极短极便宜**：单次调用本来就只有几厘钱，级联的判定开销占比反而变高。
- **延迟敏感且不可预测**：被拒绝的 draft 意味着**白等一次**（`cascade_overhead_ms` 会体现出来）。

### Q7. Python 和 TypeScript 两个版本是什么关系？

两份**平行实现**，不是绑定关系。Python 在 `flowgate/`，TypeScript 在 `packages/core/`。TS 侧有 40 多个模块，`agent.ts`、`complexity.ts`、`alignment.ts`、`telemetry/`、`routers/` 大致能跟 Python 一一对上。

要注意的是：**两边能力并不完全同步**。比如 Python 有 `resilience/circuit_breaker`、`guardrails/pii_detector`，TS 侧对应能力分散在 `rate-limiter.ts`、`guardrails.ts` 里，边界不一样。跨语言迁移时不要假设功能对等。

---

# 第二部分 跑起来

### Q8. 怎么安装？

从源码装（当前还没有发布到 PyPI）：

```bash
git clone https://github.com/oTheShyo/flowgate.git
cd flowgate
pip install -e .
```

按需装 provider 依赖：

```bash
pip install -e ".[openai]"        # 只用 OpenAI
pip install -e ".[providers]"     # openai + anthropic + groq
pip install -e ".[local]"         # vLLM
pip install -e ".[semantic]"      # 语义路由和质量检测（sentence-transformers）
pip install -e ".[dev]"           # 跑测试
```

基础依赖只有三个：`pydantic`、`httpx`、`tiktoken`。Ollama 不需要 Python 包，它走 `localhost:11434` 的 HTTP。

### Q9. 最小可运行程序长什么样？

```python
import asyncio
from flowgate import CascadeAgent, ModelConfig

async def main():
    agent = CascadeAgent(
        models=[
            ModelConfig(
                name="gpt-4o-mini",
                provider="openai",
                cost=0.000375,          # 每 1K token 的美元价
                quality_threshold=0.7,  # 这个模型单独覆写阈值
            ),
            ModelConfig(
                name="gpt-4o",
                provider="openai",
                cost=0.00625,
            ),
        ]
    )
    result = await agent.run("法国的首都是哪里？", max_tokens=100)
    print(result.content)
    print(result.model_used, result.total_cost)

asyncio.run(main())
```

几个容易踩的点：

1. `run()` 的 `max_tokens` **默认只有 100**。长回答一定要显式传。
2. `cost` 的单位是**每 1K token 的美元数**，不是每百万。
3. API key 从环境变量读（`OPENAI_API_KEY` 等），也可以直接传给 `ModelConfig(api_key=...)`，但别写进代码。

还有一个隐蔽的：**没有配置任何 key 时，构造函数不会报错**，只在日志里打一行 `No providers could be initialized. Agent will be created, but running queries will fail...`。真正的失败发生在第一次 `run()`。看到这行就该去查环境变量，别在级联逻辑里找问题。

### Q10. 没有 API key 能验证吗？

能，用离线模拟。`simulate()` 只跑复杂度检测和路由管线，**不发任何网络请求**：

```python
from flowgate import simulate, ModelConfig

models = [
    ModelConfig(name="gpt-4o-mini", provider="openai", cost=0.000375),
    ModelConfig(name="gpt-4o", provider="openai", cost=0.00625),
]

report = simulate(
    ["法国首都？", "设计一个高可用电商微服务架构", "解释量子纠缠对密码学的影响"],
    models=models,
    quality_threshold=0.7,
)

print(report.projected_cost)
print(report.escalation_rate)          # 预估升级率
print(report.model_distribution)       # 各模型分到多少条
print(report.complexity_distribution)  # 复杂度分布
```

`simulate()` 要求**至少两个模型**，否则直接抛 `ValueError`。这是整份教程里性价比最高的一个 API：上线前先用真实查询样本跑一遍，能提前知道接受率大概多少。

### Q11. `run()` 返回什么？

返回 `CascadeResult`，34 个字段。别一次全看，按用途分五组：

| 用途 | 字段 |
|---|---|
| 你真正要的 | `content`、`model_used`、`total_cost`、`latency_ms` |
| 有没有升级 | `cascaded`、`draft_accepted`、`routing_strategy`、`reason` |
| 质量判定细节 | `quality_score`、`quality_threshold`、`quality_check_passed`、`rejection_reason` |
| 成本拆解 | `draft_cost`、`verifier_cost`、`cost_saved` |
| 耗时拆解 | `complexity_detection_ms`、`draft_generation_ms`、`quality_verification_ms`、`verifier_generation_ms`、`cascade_overhead_ms` |

还有 `draft_model` / `verifier_model` / `draft_confidence` / `verifier_confidence` / `metadata`。

### Q12. 怎么知道它实际走了哪条路？

打这三个字段就够了：

```python
print(result.routing_strategy)  # "direct" 或 "cascade"
print(result.draft_accepted)    # 只有 cascade 时才有意义
print(result.reason)            # 人读的路由原因
```

典型组合：

- `routing_strategy="direct"` → 判定太复杂，直接上大模型，没试小模型
- `routing_strategy="cascade"` + `draft_accepted=True` → 小模型过了，省了钱
- `routing_strategy="cascade"` + `draft_accepted=False` → 小模型被拒，白等一次再升级

---

# 第三部分 机制：级联如何工作

### Q13. drafter 和 verifier 是谁？

不是固定角色，是**按成本排序后的位置**。

`CascadeAgent.__init__` 里有一行关键的：

```python
self.models = sorted(models, key=lambda m: m.cost)
```

最便宜的是 drafter，最贵的（或按策略选出的）是 verifier。所以你给模型起什么名字都无所谓，`cost` 才决定角色。

### Q14. `models` 列表的顺序重要吗？

不重要，**会被按 `cost` 重排**。但填错 `cost` 会直接改变行为——你把一个贵的模型 `cost` 填成 0.0001，它就会被当成 drafter 先用。

`cost` 是唯一的排序依据，也是成本计算的依据，务必填真实值。

### Q15. 质量分数是怎么算出来的？

由 `quality/` 这层算，主入口是 `QualityValidator.validate()`，其中对齐打分在 `quality/alignment_scorer.py`（2,281 行，是全项目第二大文件）。

判定不只看一个数，配置项暴露了它的维度：

```python
QualityConfig(
    confidence_thresholds=...,      # 按难度分档的阈值
    min_length_thresholds=...,      # 按难度分档的最短长度
    require_specifics_for_complex=True,  # 复杂问题必须有具体细节
    max_hedging_ratio=0.2,          # 允许的"含糊措辞"比例上限
    min_specificity_score=0.3,      # 最低具体性得分
    enable_hallucination_detection=True, # 幻觉检测
    enable_comparative=False,       # 对比校验（更准但更慢）
    enable_adaptive=False,          # 自适应阈值
)
```

也就是说，一个 draft 被拒可能不是因为"答得不对"，而是因为**太短**、**太含糊**（"这取决于多种因素……"）、或者**缺乏具体细节**。

### Q16. 默认阈值是多少？

这是整份教程里最反直觉的一点：**默认阈值不是 0.7，而且不是一个固定数**。

`CascadeAgent` 默认用 `QualityConfig.for_cascade()`，阈值按复杂度分档：

| 复杂度 | 默认阈值 |
|---|---|
| trivial | 0.25 |
| simple | 0.40 |
| moderate | 0.55 |
| hard | 0.70 |
| expert | 0.80 |

而且**自适应是开的**（`enable_adaptive=True`），阈值会随运行反馈调整。

反过来说：`QualityConfig()` 的裸默认值又是另一套（0.55 / 0.50 / 0.45 / 0.42 / 0.40），比 cascade 版更严格。这三个"默认"不是一回事。

### Q17. `ModelConfig(quality_threshold=...)` 和 `QualityConfig` 是什么关系？

- `QualityConfig` 是**全局判定配置**，按难度分档。
- `ModelConfig(quality_threshold=0.7)` 是**对这个模型的单点覆写**，示例代码里常见。

两者同时存在时，单模型的值优先生效。实践建议：先在全局配好分档阈值，只在特定模型（比如特别不靠谱的 drafter）上做单点收紧，不要每个模型都写一遍。

### Q18. 什么时候会升级到 verifier？

三个触发条件，按发生频率排：

1. **质量分低于当前难度档的阈值**（最主要）
2. **复杂度判定为高**：某些情况下直接走 direct，根本不试 drafter
3. **事实风险路由**：开启了 `enable_factual_risk_routing=True` 时，高风险提示词直接送 verifier

### Q19. 什么叫 "direct" 路由？

不试小模型，直接调大模型。发生在：

- 复杂度判定很高（试了大概率也被拒，不如省掉那一次白等）
- 你显式传了 `force_direct=True`
- 只有一个模型（级联被关掉）

`direct` 不是"没生效"，是"判定这一步不值得试"。如果你发现大量请求走 direct，说明复杂度检测认为你的流量偏难——这时候级联对你的价值本来就有限。

### Q20. `cascade_overhead_ms` 是什么？

级联决策带来的**净浪费延迟**。定义很清楚：

| 情况 | 值 |
|---|---|
| draft 被接受 | 0（省下了 verifier 的时间） |
| draft 被拒绝 | 完整的 draft 耗时（这次白等） |
| direct 路由 | 0（没有级联） |

这是评估"级联到底值不值"最直接的指标。接受率低的时候，这个数会很难看。

### Q21. 能配三个以上模型吗？

能，`models` 接受任意长度列表，按 `cost` 排序后形成梯子。但要注意：

- 默认策略是 **drafter（最便宜）+ verifier（最贵）** 的两级思路
- 多级需要 `core/cascade.py` 里的 `MultiStepCascadeExecutor` 或自定义 `ExecutionPlan` 才能发挥
- 级联层数越多，判定开销越多，收益递减

实务建议：先用两级跑出接受率数据，再决定要不要加中间层。

---

# 第四部分 路由：把请求送到正确的模型

### Q22. 复杂度是怎么判断的？

`ComplexityDetector`（`quality/complexity.py`，1,883 行）做确定性判定，输出五档：`trivial` / `simple` / `moderate` / `hard` / `expert`。

它**不是**再调一次模型去判断，而是基于规则的启发式，所以零成本、零延迟、可预测。这也意味着它可以被绕过——你的查询措辞会显著影响判定结果。

### Q23. 什么时候该用 `complexity_hint`？

当你知道答案的时候：

```python
result = await agent.run(question, complexity_hint="hard")
```

三个典型场景：

- 上游已经分类过（比如请求来自"架构咨询"这个业务线，天然是 hard）
- 压测时想强制构造某种分布
- 发现检测器系统性低估某类查询，先用 hint 兜住，再考虑改检测器

### Q24. 领域路由怎么开？

```python
agent = CascadeAgent(
    models=[...],
    enable_domain_detection=True,   # 打开领域检测
    use_semantic_domains=True,      # 用语义（embedding）而不是纯关键词
)
```

也可以给每个领域配独立的级联策略：

```python
from flowgate.schema import DomainConfig

agent = CascadeAgent(
    models=[...],
    domain_configs={"code": DomainConfig(...), "medical": DomainConfig(...)},
)
```

`routing/domain.py` 有 1,647 行，是这个模块里最重的部分。领域识别的结果会影响阈值——同一个问题在"医疗"领域该比在"闲聊"领域判得更严。

### Q25. 语义检测需要额外依赖吗？

需要。语义领域检测和语义质量校验都依赖 embedding 模型，来自 `sentence-transformers` 或 `fastembed`：

```bash
pip install -e ".[semantic]"
```

不想装的话用纯规则版（`use_semantic_domains=False`），准确度低一些但零依赖。

### Q26. 工具路由是什么？

`routing/tool_router.py` + `routing/tool_risk.py` + `routing/tool_complexity.py` 三个文件负责的事：**这次要调的工具，风险多高、多复杂，该让哪个模型来决策**。

配置项是 `enable_tool_complexity_routing=True`（默认开）。它解决的问题是：读天气和转账是两种不同量级的工具调用，不该用同一个模型来决定。

### Q27. `force_direct` 用在哪？

跳过级联，直接走最强模型。典型用途：

- 调试：怀疑级联逻辑有问题时，先确认直连是对的
- 兜底：检测到某类请求总在升级，与其白试一次不如直接上
- 回归测试：给质量一个"上限基准"

```python
result = await agent.run(q, force_direct=True)
```

---

# 第五部分 成本

### Q28. `cost` 字段到底填什么？

**每 1,000 token 的美元价格**。注释写的是 blended 价（输入输出混合估算）。

```python
ModelConfig(name="gpt-4o-mini", provider="openai", cost=0.000375)  # $0.375 / 1M
ModelConfig(name="gpt-4o",      provider="openai", cost=0.00625)   # $6.25 / 1M
```

`cost` 有三重作用：决定排序（谁是 drafter）、参与成本计算、参与 savings 计算。填错等于三处全错。

如果你的 provider 输入输出价差很大，用 blended 值会有系统性偏差，建议按你的实际输入输出比例加权算一个。

### Q29. 成本是怎么聚合的？

```
total_cost = draft_cost + verifier_cost
```

这个聚合曾经出过 bug：早期版本级联时只记了 draft 的成本，漏掉 verifier。v2.5 的修法是把所有计算收进 `telemetry/cost_calculator.py`，让 agent 只做编排、不自己算钱。

如果你要改成本逻辑，改 `CostCalculator`，不要在 `agent.py` 里加算术。

### Q30. `cost_saved` 怎么算？

对照基准是"全程都用最强模型"。所以：

```
cost_saved = 全程用 verifier 的成本 - 实际成本
```

含义是"因为级联省下了多少"。draft 被接受时它最大；draft 被拒时它可能变成负数（因为多付了一次 draft 钱）。

### Q31. 为什么 `total_cost` 和我云厂商账单对不上？

四个常见原因，按影响大小：

1. **token 数是估算的**。`_estimate_tokens_from_text` 用 tiktoken 本地计数，跟 provider 的实际计费口径（含 system prompt、缓存命中、特殊 token）会有出入。
2. **`cost` 是 blended 价**，不是精确的输入/输出分段价。
3. **没算缓存折扣**。Anthropic、OpenAI 的 prompt caching 不计入这里。
4. **重试和失败请求**不一定进统计。

把它当**相对指标**用（比较不同策略谁更省），不要当**绝对账目**用。

### Q32. 批处理怎么更省？

`core/batch.py` 提供 `BatchProcessor`，配 `BatchConfig` 和 `BatchStrategy`：

```python
from flowgate.core.batch import BatchProcessor, BatchConfig, BatchStrategy
```

两种策略：

| 策略 | 前提 | 行为 |
|---|---|---|
| `LITELLM_NATIVE` | 装了 `litellm` | 走 `batch_completion`，真正的批量提交 |
| `SEQUENTIAL` | 无依赖 | 逐条跑，只是串行封装 |

没装 litellm 时**自动退化为 SEQUENTIAL**（`_resolve_strategy` 里判断 `HAS_LITELLM_BATCH`），不会报错，但也就没有什么批处理红利了。

离线任务（数据标注、批量摘要、历史回填）适合这条路；在线请求别用，它换的是吞吐不是延迟。

### Q33. 成本预测和异常检测是什么？

`telemetry/` 下有三个进阶文件：

- `forecasting.py` —— 基于历史消耗预测未来成本
- `anomaly.py` —— 检测异常消耗（某个 agent 突然烧钱）
- `degradation.py` —— 检测质量退化

这三个是给"跑在生产上、有人盯着"的场景用的。个人项目阶段可以先忽略。

---

# 第六部分 流式输出

### Q34. 流式还能级联吗？

能，而且这是它比网关强的地方之一：网关流式出去了就回不了头，进程内可以中途切换。

机制是：drafter 边生成边打分，分数不够就在流中途切到 verifier。代价是用户可能已经看到半截被丢弃的内容。

### Q35. `stream()` 有哪几类事件？

`streaming/base.py` 定义了六种：

| 事件 | 含义 |
|---|---|
| `ROUTING` | 路由决策已定（走 direct 还是 cascade） |
| `CHUNK` | 一个文本片段 |
| `DRAFT_DECISION` | draft 是否被接受 |
| `SWITCH` | 正在切换到 verifier |
| `COMPLETE` | 结束（带最终汇总） |
| `ERROR` | 出错 |

用法：

```python
from flowgate.streaming import StreamEventType

async for event in agent.stream("解释一下 Python 的 GIL", max_tokens=300):
    if event.type == StreamEventType.CHUNK:
        print(event.content, end="", flush=True)
    elif event.type == StreamEventType.SWITCH:
        print("\n[模型升级中]", flush=True)
```

### Q36. 怎么在 UI 上提示"正在升级到更强的模型"？

监听 `SWITCH` 事件。这是整套流式协议里最有产品价值的事件——用户知道"要等一下，但结果会更好"，体验上比莫名其妙卡住好得多。

### Q37. 流式下还能拿到成本吗？

能，`COMPLETE` 事件里带汇总信息。也可以在流结束后读 `agent` 的累计统计：

```python
print(agent.get_stats())
```

---

# 第七部分 工具调用

### Q38. `tools` 参数长什么样？

`run()` 要的是普通 dict 列表，每项含 `name`、`description`、`parameters`（JSON Schema）。`ToolConfig` 是用来定义工具和绑函数的，`from_function` 能直接从类型注解推导 schema：

```python
from flowgate.tools import ToolConfig, ToolExecutor

def get_weather(location: str, unit: str = "celsius") -> dict:
    return {"location": location, "temp": 22, "unit": unit}

cfg = ToolConfig.from_function(get_weather, description="Get weather for a city")

# from_function 自动推导出：
# {'type': 'object',
#  'properties': {'location': {'type': 'string'}, 'unit': {'type': 'string'}},
#  'required': ['location']}

tools = [
    {"name": c.name, "description": c.description, "parameters": c.parameters}
    for c in [cfg]
]
executor = ToolExecutor([cfg])
```

想要对 schema 完全控制（枚举值、默认值、字段描述），就手写 `ToolConfig(name=..., description=..., parameters={...}, function=...)`。

注意 `parameters` 必须是合法 JSON Schema，模型侧不做容错——写错了是静默失效，不是报错。

### Q39. 一次 `run()` 会自动执行工具吗？

**默认不会**。`run()` 返回的 `result.tool_calls` 是模型"想调用什么"，执行权在你手里。

```python
result = await agent.run(query, tools=tools)
if result.has_tool_calls:
    for call in result.tool_calls:
        print(call["name"], call["arguments"])   # 只是意图
```

这个设计是刻意的：工具执行涉及权限，库不该替你做决定。要自动执行，传 `tool_executor` 给构造函数。

### Q40. 多轮工具循环怎么写？

标准 agent 循环：把工具结果塞回 messages，再跑一次。

```python
import json

messages = [{"role": "user", "content": query}]

for _ in range(max_turns):
    result = await agent.run(query, messages=messages, tools=tools, max_tokens=500, max_steps=5)

    if not result.has_tool_calls:
        break

    messages.append({
        "role": "assistant",
        "content": result.content or "",
        "tool_calls": [
            {"id": c["id"], "type": "function",
             "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
            for c in result.tool_calls
        ],
    })

    for call in result.tool_calls:
        output = run_my_tool(call["name"], call["arguments"])   # 你的执行逻辑
        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": json.dumps(output),
        })
```

两个细节值得注意：

1. **`result.tool_calls` 的字段形状随 provider 变**。OpenAI 风格是 `{"id","function":{"name","arguments"}}`，有的 provider 拍平成 `{"name","arguments"}`，`arguments` 还可能是 JSON 字符串。官方示例里专门写了 30 多行 `normalize_tool_call()` 来抹平这些差异（`examples/tool_execution.py:281`），生产代码建议照抄而不是自己猜。

2. `max_steps`（默认 5）限制单次 `run()` 内部步数，`max_turns` 是你外层循环的上限。两个都要设，否则一个会推理的工具能把你的预算跑穿。

想用库自带的执行器，`ToolExecutor.execute(tool_call)` 接收 `ToolCall` 对象（含 `id`、`name`、`arguments`、`provider_format`），比手写 dict 处理省事，但转换那一步还是得做。

### Q41. 工具调用会影响选模型吗？

会。`ToolRouter` 会先按 `supports_tools` 过滤掉不支持工具的模型，再按复杂度决定谁来处理。

如果你的便宜模型不支持 function calling，一定要设 `supports_tools=False`，否则会被选中然后失败。

---

# 第八部分 Harness：预算、KPI、合规

### Q42. harness 是什么？和 `CascadeAgent` 什么关系？

harness 是一层**旁挂的约束层**，不改变 `CascadeAgent` 的行为，只在外面加预算、追踪、合规的账本。

```python
from flowgate import init, run

init(mode="observe", budget=1.0, max_tool_calls=6)

with run(budget=0.5, max_tool_calls=4) as session:
    result = await agent.run("...")
    print(session.cost, session.budget_remaining)
```

一句话：`CascadeAgent` 决定"用哪个模型"，harness 决定"还能不能继续花"。

### Q43. `init()` 有哪些参数？

```python
init(
    mode="off",              # off | observe | enforce
    verbose=False,
    budget=0.5,              # 美元上限
    max_tool_calls=10,       # 工具调用次数上限
    max_latency_ms=30000,    # 累计延迟上限
    max_energy=100.0,        # 能耗预算
    kpi_targets={"cost": 0.8},
    kpi_weights={"cost": 1.0, "latency": 0.5},
    compliance="gdpr",       # gdpr | hipaa | pci | strict
)
```

传非法值会直接抛 `ValueError`：`mode` 必须是三个值之一，`budget` 不能为负。

### Q44. `mode` 的三种值有什么区别？

| mode | 行为 |
|---|---|
| `off` | 完全关闭，零开销，连记账都不做 |
| `observe` | 记录成本和决策，但**不拦截**。用来先看真实消耗 |
| `enforce` | 超限就动手：拦下调用、抛 `BudgetExceededError` |

上线顺序建议是 `off` → `observe` 跑一周看真实分布 → 把预算设成 p95 的 1.2 倍再切 `enforce`。直接上 `enforce` 容易在流量尖峰时把用户请求打死。

### Q45. `with run(...)` 的作用域是什么？

创建一个**作用域账本**，里面的参数覆盖 `init()` 的全局值，出了 `with` 块就失效。

典型用法是按请求开作用域：

```python
init(mode="enforce", budget=100.0)         # 全天总额

async def handle(request):
    with run(budget=request.user_daily_remaining) as session:
        ...
```

### Q46. `session` 上能读到什么？

```python
session.cost              # 累计花费
session.budget_remaining  # 剩余预算
session.savings           # 级联省下的钱
session.step_count        # 步数
session.tool_calls        # 工具调用次数
session.latency_used_ms   # 累计延迟
session.energy_used       # 能耗
session.model_used        # 用过哪些模型
session.last_action       # 最后一次决策动作
session.trace()           # 决策轨迹（可迭代）
session.summary()         # 汇总
session.save()            # 导出会话（JSONL，可回灌给 simulate）
```

`trace()` 是最有价值的一个——它是审计和调参的依据。每次"为什么走了这条路"都有记录。

### Q47. 超预算会怎样？

`enforce` 模式下抛 `BudgetExceededError`（定义在 `schema/exceptions.py`，从包根可以直接 import）。

```python
from flowgate import BudgetExceededError

try:
    with run(budget=0.01) as session:
        await agent.run("很长的任务...")
except BudgetExceededError as e:
    log.warning(f"预算耗尽: {e}")
    return fallback_response()
```

实践要点：**一定要在处理函数最外层捕获**，并且准备好降级响应。这是生产可用的前提。

### Q48. `compliance` 支持哪些值？

`gdpr`、`hipaa`、`pci`、`strict`。设置后会影响 `guardrails/` 的检查强度——比如 PII 检测（`pii_detector.py`）、内容审核（`content_moderator.py`）。

注意边界：这层是**代码级规则**，不是法律合规认证。别把它当"我们符合 GDPR 了"的证据。

---

# 第九部分 不花钱的验证

### Q49. 怎么在没 key 的情况下预测成本？

`simulate()`。它复用确定性的复杂度检测和领域路由，逐条投影"会落到哪个模型"，然后按 `cost` 算总账。

```python
report = simulate(queries, models=[drafter, verifier], quality_threshold=0.7)
print(f"预估成本 ${report.projected_cost:.4f}")
print(f"预估升级率 {report.escalation_rate:.1%}")
print(f"模型分布 {report.model_distribution}")
```

返回 `SimulationResult`，含 `total_queries`、`projected_cost`、`escalation_rate`、`model_distribution`、`complexity_distribution`、`domain_distribution`。

**这是选型阶段最该先跑的 API**：把你的真实查询样本丢进去，先看升级率。如果升级率 80%，说明你的流量本来就难，级联省不了钱，别浪费时间调阈值。

### Q50. 怎么用真实流量回放？

`simulate()` 的 `queries` 参数除了接受字符串列表，还接受 **JSONL 文件路径**，每行一个带 `query` 字段的对象——正好是会话导出（`session.save()`）的格式。

所以流程是：生产上跑一段 `observe` 模式 → 导出会话 → 回放模拟 → 调阈值 → 再发布。

---

# 第十部分 集成

### Q51. LangChain 怎么接？

先装可选依赖：

```bash
pip install -e ".[langchain]"
```

然后：

```python
from flowgate.integrations.langchain import FlowGate

llm = FlowGate(...)
```

实现住在 `flowgate/integrations/langchain/`（11 个文件，`wrapper.py` 有 2,046 行）。`flowgate/langchain/` 那个单文件目录只是向后兼容的转发 shim，别删。

注意：这个模块 import 时会要求 `langchain_core`，没装的话报 `ModuleNotFoundError`，不是代码坏了。

### Q52. OpenAI Agents SDK 呢？

```python
from flowgate.integrations.openai_agents import ...
```

对应文件是 `integrations/openai_agents.py`，它里面会调用预算检查并抛 `BudgetExceededError`（第 206 行），是少数几个默认就会拦截的集成。

### Q53. CrewAI、PydanticAI、Google ADK 呢？

三个都有独立的 harness 适配，模式一致：先 `init()`，再 `enable()`，最后在 `with run(...)` 里跑原生代码。

```python
from flowgate.integrations.crewai import CrewAIHarnessConfig, enable

init(mode="observe", budget=1.0, max_tool_calls=6)
enable(config=CrewAIHarnessConfig(fail_open=True, enable_budget_gate=True))

with run(budget=0.5, max_tool_calls=4) as session:
    result = crew.kickoff()
    print(session.cost, session.trace())
```

`fail_open=True` 的含义：集成钩子不可用时放行而不是报错。生产上建议 `True`，本地调试时用 `False` 好发现问题。

### Q54. Vercel AI SDK / n8n 呢？

TypeScript 侧的事：

- `packages/integrations/vercel-ai/` —— Vercel AI SDK 适配
- `packages/integrations/n8n/` —— n8n 节点（`@flowgate/n8n-nodes-flowgate`，含 `FlowGateAgent` 和 `LmChatFlowGate` 两个节点）

n8n 那条路适合不写代码的团队：拖节点、填 key、配模型对，就能跑级联。

### Q55. HTTP 网关模式适合谁？

`proxy/server.py`（1,605 行），启动命令 `flowgate-gateway`。

适合：**改不了代码的系统**。老应用、第三方 SaaS、写死 endpoint 的客户端。它们只认 HTTP，那就把 flowgate 伪装成一个 OpenAI 兼容端点。

代价是丢掉进程内的能力（拿不到 agent 状态、看不到工具调用），退化成普通网关。所以优先选 SDK 集成，网关当兜底。

---

# 第十一部分 配置与部署

### Q56. 配置优先级是什么？

三层，从高到低：

1. **代码参数**（`init()` / `CascadeAgent(...)` 里传的）
2. **配置文件**（`.flowgate.json`）
3. **环境变量**（`FLOWGATE_*`）

解析逻辑在 `harness/api.py` 的 `_read_file_config()` / `_read_env_config()`。

注意这里跟常见约定相反：多数框架是"环境变量覆盖配置文件"，这里是代码 > 文件 > 环境变量。部署时容易踩。

### Q57. 有哪些环境变量？

前缀统一是 `FLOWGATE_`（从上游的 `CASCADEFLOW_` 改过来的）。主要几组：

| 变量 | 用途 |
|---|---|
| `FLOWGATE_MODE` | harness 模式 |
| `FLOWGATE_CONFIG` | 配置文件路径 |
| `FLOWGATE_BUDGET` | 全局预算上限 |
| `FLOWGATE_HARNESS_MODE` | harness 模式（显式版） |
| `FLOWGATE_HARNESS_BUDGET` | 预算 |
| `FLOWGATE_HARNESS_MAX_TOOL_CALLS` | 工具调用上限 |
| `FLOWGATE_HARNESS_MAX_LATENCY_MS` | 延迟上限 |
| `FLOWGATE_HARNESS_KPI_TARGETS` | KPI 目标（JSON） |
| `FLOWGATE_HARNESS_KPI_WEIGHTS` | KPI 权重（JSON） |
| `FLOWGATE_HARNESS_COMPLIANCE` | 合规档位 |
| `FLOWGATE_DECISION_LOG` | 决策日志路径 |
| `FLOWGATE_GATEWAY_URL` | 网关地址 |

完整清单见 `.env.example`。

### Q58. 多租户、多渠道怎么配？

`CascadeAgent` 的构造参数里有四个跟这个相关：

```python
CascadeAgent(
    models=[...],
    tenant_rules={"tenant_a": {...}},        # 按租户覆写路由
    channel_models={"web": ["gpt-4o-mini"]}, # 按渠道限制可用模型
    channel_failover={"web": "backup"},      # 渠道故障转移
    channel_strategies={"web": "cheap_first"},
)
```

`run()` 时传 `tenant_id=` 和 `channel=` 激活。这是给"一个服务多个客户"的场景准备的，个人项目用不到。

### Q59. 怎么部署？

三种形态，按侵入性排：

1. **同进程库**（推荐）：`pip install` 进你的服务，跟业务代码一起跑。延迟最低，能力最全。
2. **网关服务**：`flowgate-gateway` 独立跑，业务方当它是 OpenAI endpoint。
3. **MCP server**：`flowgate-mcp`，给 MCP 客户端用。

生产环境记得配 `FLOWGATE_MODE=enforce` + 合理的 `budget`，并在最外层捕获 `BudgetExceededError`。

---

# 第十二部分 扩展开发

### Q60. 怎么加一个新 provider？

继承 `BaseProvider`（`providers/base.py`，1,695 行），实现核心方法，然后注册进 `PROVIDER_REGISTRY`。

```python
from flowgate.providers.base import BaseProvider, ModelResponse

class MyProvider(BaseProvider):
    async def complete(self, model: str, messages, **kwargs) -> ModelResponse:
        ...

PROVIDER_REGISTRY["myprovider"] = MyProvider
```

`ModelResponse` 是统一返回结构，级联层只认它，不认各家 SDK 的对象。这是它支持 9 个 provider 的原因。

### Q61. 想换掉质量校验怎么办？

两种做法：

- **改配置**：调 `QualityConfig` 的阈值、长度、具体性要求。80% 的需求在这一层能解决。
- **换校验器**：`QualityValidator` 是可替换的，`ComparativeValidator` 是另一种实现（用两个模型对比答案，更准但更慢，所以默认关）。参考 `examples/custom_validation.py`。

如果你要接自己的评估模型（比如用另一个 LLM 打分），从 `ComparativeValidator` 抄结构最快。

### Q62. 自定义路由怎么写？

继承 `Router`（`routing/base.py`）实现 `route()`，然后塞进 `RouterChain`：

```python
from flowgate.routing.base import Router, RouterChain

class MyRouter(Router):
    def route(self, query, context):
        ...

agent = CascadeAgent(models=[...], rule_engine=RuleEngine(...))
```

更轻量的做法是往 `rules/engine.py` 里加规则（`rules/decision.py` 定义决策结构），不用改代码结构。

---

# 第十三部分 排错

### Q63. 钱没省下来，从哪查？

按顺序看四个数：

1. `report.escalation_rate`（离线）或 `result.draft_accepted` 的统计（线上）—— 升级率超过 60% 就别指望省钱了
2. `result.complexity` 的分布 —— 如果大量是 hard/expert，级联本来就不适用
3. `result.routing_strategy` —— 如果大量是 direct，说明根本没试小模型
4. `result.rejection_reason` —— 如果大量是"太短"或"太含糊"，是提示词问题，不是模型能力问题

第 4 条最常被忽略。小模型答得对但答得太短被拒，加一句"请详细回答"就能把接受率拉上去。

### Q64. 一直报 `BudgetExceededError`？

三个原因：

- `budget` 单位是**美元**，你是不是填了 0.001 这种量级
- `run` 作用域嵌套了，内层预算被外层残值限制
- 前面有失败请求也计了费

先用 `mode="observe"` 跑一遍看 `session.cost` 实际到多少，再定预算。

### Q65. 延迟变高了？

先看 `result.cascade_overhead_ms`：

- 如果是 0，级联不是元凶，去查 provider 本身（换 Groq 之类的快 provider）
- 如果接近 draft 耗时，说明 draft 经常被拒，测试成本直接变成了延迟成本

两种缓解：抬高阈值档位不现实时，用 `force_direct` 对已知难查询跳过试错；或者换更快的 drafter。

### Q66. 结果质量下降了？

级联的固有代价。三个补偿手段：

1. 提高对应难度档的阈值（`confidence_thresholds`）
2. 关掉 `enable_adaptive`，避免阈值漂移
3. 用 `QualityConfig.for_production()` 之类的严格预设（如果这是面向客户的质量敏感场景）

记住设计文档里的取舍：默认配置是"用 3% 质量换 28% 接受率、2 倍速度"。这个交换在客服场景合理，在合同场景不合理。

---

# 第十四部分 这个仓库的现状

这一节必须说实话，因为你在读的是一个改名后的衍生仓库。

**技术来源**：代码基于 [cascadeflow](https://github.com/lemony-ai/cascadeflow)（MIT License，Copyright 2025 Lemony Inc.）。本仓库做了包名、命名空间、CLI、npm scope、环境变量前缀的重命名和文档重写，LICENSE 保留原版权声明，衍生关系记录在 `NOTICE.md`。

**已验证的**：Python 侧 1,008 个测试通过（另有 12 个失败是因为环境缺 `sentence-transformers`，2 个模块因缺 `numpy` / `google-adk` 无法收集）。核心链路 `import`、`CascadeAgent.run`、`server`、`mcp_server` 均正常。

**还没验证的**：

- TypeScript 侧没有跑过 `tsc` 和 `pnpm test`（当前环境没装 node_modules）
- n8n 节点的产品截图还是上游界面，与改名后的节点名不一致
- README 里的成本节省数字（69% / 93% 等）是上游的基准数据，**没有在本仓库复现过**

**所以怎么引用它**：说"基于 cascadeflow 的二次开发与改造"是准确的；说"自研的级联框架"是不准确的，源码结构、算法、测试都是上游的。

如果要让它真正成为自己的东西，两个最有价值的切入点是：

1. 做一份 Python / TypeScript 能力对照表，把漂移点标出来
2. 拆 `agent.py` 那个 3,346 行的上帝对象——它是现在所有改动的瓶颈

---

# 附录 A 模块地图

| 路径 | 规模 | 职责 |
|---|---|---|
| `flowgate/agent.py` | 3,346 行 | 唯一编排入口 |
| `flowgate/core/cascade.py` | 1,855 行 | 三种级联策略 + 执行计划 |
| `flowgate/quality/alignment_scorer.py` | 2,281 行 | 对齐打分 |
| `flowgate/quality/complexity.py` | 1,883 行 | 复杂度检测 |
| `flowgate/routing/` | 13 文件 | 预路由、领域、复杂度、工具 |
| `flowgate/providers/` | 11 文件 | 9 个 provider 适配 |
| `flowgate/telemetry/` | 9 文件 | 成本、指标、异常、预测 |
| `flowgate/harness/` | 5 文件 | 预算与追踪的旁挂层 |
| `flowgate/guardrails/` | 4 文件 | PII、内容审核 |
| `flowgate/proxy/server.py` | 1,605 行 | HTTP 网关 |
| `flowgate/integrations/` | 9 文件 + 4 子包 | 各家框架适配 |
| `packages/core/` | 40+ TS 模块 | TypeScript 平行实现 |

Python 侧合计约 70,500 行，167 个文件，31 个子包。

# 附录 B 术语表

| 术语 | 含义 |
|---|---|
| drafter | 先试的便宜模型，按 `cost` 排序后的第一个 |
| verifier | 兜底的强模型 |
| 接受率 | draft 通过质量判定的比例，决定省钱效果 |
| direct | 跳过试错，直接调强模型 |
| cascade | 先 draft 后 verifier 的常规路径 |
| 质量分 | 对 draft 答案的 0–1 打分 |
| 阈值 | 质量分必须达到的门槛，按复杂度分档 |
| 升级 | draft 被拒后调用 verifier |
| `cascade_overhead_ms` | 级联决策造成的净浪费延迟 |
| harness | 预算/trace 的旁挂约束层，不改变主流程 |
| `cost_saved` | 相对"全程用最强模型"省下的钱 |

---

写到这里，你已经能覆盖从"跑通第一个例子"到"上线并排查成本异常"的完整链路。真正需要动手改代码时，从 `agent.py` 的 `run()` 和 `core/cascade.py` 的 `SpeculativeCascade` 这两处切入，其余模块都是被它们调用的。
