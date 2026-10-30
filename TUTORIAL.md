# flowgate 完全教程：用 66 个问题从安装走到生产

写这份东西的起因很简单：官方 README 告诉你它省钱，但没告诉你它在什么情况下不省钱、哪个参数的默认值和你想的不一样、以及第一次跑起来看到空结果时该往哪儿查。所以这里按"你会遇到的问题"来组织，一个问题接一个问题往下走，尽量给到能直接抄的代码，而不是停在概念上。

读法上我建议第一次别跳。前三部分（它是什么、怎么跑起来、级联怎么运作）决定了你后面会不会用错方向，这三节看完再往后挑着看。后面那些路由、成本、流式、工具、harness 的部分，可以等你真碰到对应需求了再翻。

这份文档对应 `flowgate` 1.2.0，Python 3.9 以上，TypeScript 5.x。文里说的 `agent` 都是 `CascadeAgent` 的实例，代码默认跑在 `async` 环境里，因为 `run()` 本身是个协程。

---

## Q1. flowgate 到底是什么东西？

先说结论：它是一个库，不是框架，也不是网关。

这话得解释一下，因为这三个词的界限很多人搞混。框架会接管你的控制流，你往里填业务逻辑；网关是独立进程，你把请求发给它，它转发出去。flowgate 两样都不是——它嵌在你自己的 agent 循环里，在每次模型调用之前插一句："这次该用哪个模型？花多少钱？要不要拦下来？"

它自己的说法叫 in-process intelligence layer，进程内的智能层。关键词是"进程内"，意思是它不把请求发到别的服务再转回来，没有那一圈网络往返。

用起来就三个东西：导入 `CascadeAgent` 和 `ModelConfig`，构造一个 agent，`await agent.run()`。就这样。

---

## Q2. 那它和 LiteLLM、OpenRouter 这类网关差在哪？

差在决策发生在哪一层。

外面的网关看到的是一个 HTTP 请求，从请求进来到响应出去，中间发生了什么它不知道。flowgate 待在你的进程里，所以它知道现在这是 agent 的第 7 步、前面已经花了 0.8 美元、刚才调过两个工具、预算还剩 0.2。

这个差别不是学术性的。正因为知道这些，它才能做"这一步太贵了，降一档"这种决策；网关做不到，网关连"这一步"这个概念都没有。

粒度也不一样。网关的决策单位是整个请求，flowgate 的决策单位是单次模型调用、甚至单次工具调用。延迟上，网关一般多 10 到 50 毫秒的网络往返，flowgate 官方标称 5 毫秒以内——因为它就是几个函数调用，没有序列化。

还有一点是能不能动手。网关大多只能观察和记录，flowgate 可以在中途 `stop`、`deny_tool`、`switch_model`。这个能力在预算控制和工具权限上挺关键。

---

## Q3. 所谓"级联"，具体做了哪几件事？

三步，很简单。

第一步，让便宜模型先答，这个角色叫 drafter。它给出一个完整答案。

第二步，给这个答案打个质量分，跟当前难度档位对应的阈值比一比。

第三步，分够了就直接返回，分不够才把贵的那个叫上来重答，这个角色叫 verifier。

只有第三步真的发生了，你才付两次钱。所以整个级联的收益，完全取决于一个比例：有多大比例的请求，小模型的答案能过关。

这个比例有个名字，叫接受率。代码注释里写的设计目标是 50% 到 60%。

---

## Q4. 那省钱的原理是什么？就因为小模型便宜？

不完全是。真正的假设是：大多数请求根本不需要旗舰模型。

文档里的论证是，40% 到 70% 的查询用不着又慢又贵的旗舰模型，而且领域专用的小模型在专门任务上经常打赢通用大模型——翻译、分类、结构化抽取这类活儿，专门训过的小模型又快又准。

所以省钱的公式近似成这样：

```
节省比例 ≈ 接受率 × (1 - 小模型单价 / 大模型单价)
```

你看这个式子就明白了。接受率 55%、单价差 16 倍（0.375 对 6.25 美元每百万 token），理论上能省一半以上。README 里敢写 69%、93% 这些数，就是因为它们强烈依赖你自己的查询分布，换个场景数字就完全不同。

---

## Q5. 什么样的负载用它才真能省钱？

符合三个特征的负载，级联才有意义。

第一，请求量够大，而且难度分布偏简单。客服问答、分类、信息抽取、格式转换、简单代码补全，这些都属于"绝大多数请求一次就能答对"的类型。

第二，答案质量有可自动判定的标准。要么有参考答案，要么有结构约束（必须是合法 JSON），要么有相似度可比。没法判定的任务，级联连判断该不该升级的依据都没有。

第三，质量不达标的时候允许重试，多花一次钱不会出事故。这条经常被忽略，但它是前提。

反过来说，你要一次生成就要交给客户的合同条款，那重试的代价远大于省下的那点钱，这种活不该用级联。

---

## Q6. 什么场景明确不该用？

四种，我按踩坑频率排。

质量零容忍的场景：医疗诊断、法律意见、金融合规文本。哪怕 3% 的质量下降也不可接受，这时候省钱不是目标。

单模型系统：你只有一个模型，级联无从谈起。代码会打一条 warning 然后自动把级联关掉，不会崩，但你得知道它没在干活。

请求极短极便宜的：单次调用本来就只有几厘钱，级联的判定开销占比反而变高，净亏。

延迟敏感且接受率不高的：draft 被拒意味着白等一次，这个时间是要用户承担的，`cascade_overhead_ms` 会把它算出来给你看。

---

## Q7. Python 和 TypeScript 两个版本是什么关系？

两份平行实现，不是绑定关系。Python 在 `flowgate/` 目录，TypeScript 在 `packages/core/`。

TS 侧有 40 多个模块，`agent.ts`、`complexity.ts`、`alignment.ts`、`telemetry/`、`routers/` 大致能跟 Python 那边一一对上。

但有个地方要注意：两边能力并不完全同步。Python 有 `resilience/circuit_breaker`、`guardrails/pii_detector`，TS 侧的对应能力散在 `rate-limiter.ts`、`guardrails.ts` 里，划分边界不一样。你要跨语言迁移，别假设功能对等，先去翻一眼对面有没有这个东西。

---

## Q8. 怎么装上？

当前还没发到 PyPI，从源码装：

```bash
git clone https://github.com/oTheShyo/flowgate.git
cd flowgate
pip install -e .
```

基础依赖只有三个：`pydantic`、`httpx`、`tiktoken`。挺克制的，没什么奇怪的传递依赖。

然后按你实际用哪个 provider 装可选依赖。只用 OpenAI 就 `pip install -e ".[openai]"`，要 openai 加 anthropic 加 groq 就 `.[providers]`，跑 vLLM 用 `.[local]`，要语义路由和质量检测用 `.[semantic]`（这个会拉 sentence-transformers，比较重），要跑测试就 `.[dev]`。

Ollama 是个例外，它不需要任何 Python 包，走 `localhost:11434` 的 HTTP 接口。

---

## Q9. 最小能跑起来的程序长什么样？

这样：

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

有几个坑得提前说，不然你会在莫名其妙的地方卡住。

第一个，`run()` 的 `max_tokens` 默认只有 100。这是真的，不是打错字。你问一个需要展开回答的问题，拿到半截就断了，先怀疑这个参数。

第二个，`cost` 的单位是每 1K token 的美元数，不是每百万。这个跟大部分厂商的报价方式反着来，很容易填错一位。`0.000375` 对应的其实是每百万 0.375 美元。

第三个，API key 从环境变量读（`OPENAI_API_KEY` 之类），也可以直接传给 `ModelConfig(api_key=...)`，但别写进代码。

还有一个最隐蔽的：没配任何 key 的时候，构造函数不会报错。它只在日志里打一行 `No providers could be initialized. Agent will be created, but running queries will fail...`，然后正常返回。真正的失败发生在第一次 `run()`。所以你要是看到这行，直接去查环境变量，别在级联逻辑里找问题——这不是逻辑 bug，是压根没连上。

---

## Q10. 没有 API key 能不能先验证一下？

能，用离线模拟。`simulate()` 只跑复杂度检测和路由管线，一个网络请求都不发。

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

只有一个限制：`simulate()` 要求至少两个模型，给一个直接抛 `ValueError`。

我个人觉得这是整份文档里性价比最高的一个 API。上线前拿真实查询样本跑一遍，你就大概知道接受率是多少了，不用先花一笔钱试错。

---

## Q11. `run()` 返回的那个东西里有什么？

`CascadeResult`，34 个字段。一次全看完会晕，按用途分成几组就好理解了。

你真正要用的其实只有四个：`content`、`model_used`、`total_cost`、`latency_ms`。剩下三十个都是给排查和调优准备的。

想知道它到底有没有升级，看 `cascaded`、`draft_accepted`、`routing_strategy`、`reason` 这四个。

想搞明白质量判定为什么那样，看 `quality_score`、`quality_threshold`、`quality_check_passed`、`rejection_reason`。

想拆成本，看 `draft_cost`、`verifier_cost`、`cost_saved`。

想拆耗时，看 `complexity_detection_ms`、`draft_generation_ms`、`quality_verification_ms`、`verifier_generation_ms`、`cascade_overhead_ms`。

另外还有 `draft_model`、`verifier_model`、`draft_confidence`、`verifier_confidence`、`metadata` 这些补充信息。

---

## Q12. 怎么知道它实际走了哪条路？

打三个字段就够了：

```python
print(result.routing_strategy)  # "direct" 或 "cascade"
print(result.draft_accepted)    # 只有 cascade 时才有意义
print(result.reason)            # 人读的路由原因
```

三种典型组合，记住它们的含义就不会误判。

看到 `routing_strategy="direct"`，说明判定这题太复杂，直接上了大模型，压根没试小模型。

看到 `"cascade"` 加 `draft_accepted=True`，说明小模型过关了，这次省了钱。

看到 `"cascade"` 加 `draft_accepted=False`，说明小模型被拒了，白等一次然后升级——这次是亏的。

---

## Q13. drafter 和 verifier 到底是谁？

它们不是固定的两个模型，是排序之后的位置。

`CascadeAgent.__init__` 里有一行很关键：

```python
self.models = sorted(models, key=lambda m: m.cost)
```

最便宜的那个自动成为 drafter，最贵的（或者按策略选出来的）成为 verifier。所以你给模型起什么名字都无所谓，`cost` 才决定角色。

---

## Q14. 那我 `models` 列表的顺序重要吗？

不重要，会被按 `cost` 重排。

但这里有个反向的坑：填错 `cost` 会直接改变行为。你要是把一个贵模型的 `cost` 写成 0.0001，它就会被当成 drafter 先用——于是你以为自己在省钱，实际上每次都在用最贵的模型打头阵，然后可能还被拒，再叫另一个贵的来重答。

`cost` 是唯一排序依据，也是成本计算的依据，还是 savings 计算的依据。它一错，三处全错。务必填真实值。

---

## Q15. 质量分数是怎么算出来的？

由 `quality/` 这一层算，主入口是 `QualityValidator.validate()`。里面最重的部分是对齐打分，在 `quality/alignment_scorer.py`，2,281 行，是整个项目第二大的单文件。

判定不只看一个数字，从配置项就能看出来它考虑了哪些维度：

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

这意味着什么？一个 draft 被拒，可能根本不是因为"答得不对"。可能因为它太短，可能因为它满篇"这取决于多种因素""需要结合具体情况分析"这种含糊话，可能因为它缺乏具体细节。这三种情况的处理方式完全不一样，后面排错那节会讲。

---

## Q16. 默认阈值是多少？

这是整份文档里最反直觉的一点，我先把它摆在最前面：默认阈值不是 0.7，而且根本不是一个固定数。

`CascadeAgent` 默认用 `QualityConfig.for_cascade()`，阈值按复杂度分成五档。trivial 是 0.25，simple 是 0.40，moderate 是 0.55，hard 是 0.70，expert 是 0.80。

也就是说简单问题只要 0.25 分就算过，专家级问题要 0.80。这个设计是对的——用同一个阈值卡所有难度，要么简单题的接受率被压死，要么难题的质量被放水。

而且自适应是开着的，`enable_adaptive=True`，阈值会随运行反馈自己调整。

再补一个容易混淆的：`QualityConfig()` 的裸默认值又是另一套，0.55、0.50、0.45、0.42、0.40，比 cascade 版更严格，而且是递减的。这三个"默认"不是一回事，你写 `QualityConfig()` 和用 `for_cascade()` 得到的行为完全不同。

---

## Q17. `ModelConfig(quality_threshold=...)` 和 `QualityConfig` 什么关系？

一个是全局，一个是单点覆写。

`QualityConfig` 是全局判定配置，按难度分档，管所有请求。

`ModelConfig(quality_threshold=0.7)` 是对这个模型的单点覆写，示例代码里常见，因为写起来直观。

两个同时存在时，单模型的值优先生效。我的建议是：全局按档位配好，只在特定模型上做单点收紧（比如你有个特别不靠谱的 drafter），别每个模型都写一遍——写多了以后改阈值你会不知道改哪个生效。

---

## Q18. 什么情况下会升级到 verifier？

三个触发条件，按实际发生频率排。

最常见的是质量分低于当前难度档的阈值，这是主路径，90% 的升级都来自这里。

第二种是复杂度被判得很高，某些情况下直接走 direct，根本不试 drafter——严格说这不算升级，是跳过。

第三种是事实风险路由，开了 `enable_factual_risk_routing=True` 之后，高风险提示词直接送 verifier，不做试错。

---

## Q19. 什么叫 direct 路由？

就是不用小模型试，直接调大模型。

三种情况会这样：复杂度判定很高（既然试了大概率也被拒，不如省掉那一次白等）、你显式传了 `force_direct=True`、或者你只配了一个模型（级联被关掉了）。

这里要澄清一个误解：direct 不是"级联没生效"，是"判定这一步不值得试"。这两件事性质不同。

但如果你发现大部分请求都在走 direct，那说明复杂度检测认为你的流量整体偏难。这种情况下级联对你的价值本来就有限，别硬调阈值，那不是问题所在。

---

## Q20. `cascade_overhead_ms` 是什么意思？

它衡量的是级联决策带来的净浪费延迟。

draft 被接受的时候它是 0，因为你还省下了 verifier 的时间，纯赚。draft 被拒绝的时候它等于完整的 draft 耗时，就是这次白等的时间。走 direct 的时候也是 0，因为压根没有级联。

这个指标是判断"级联到底值不值"最直接的东西。接受率低的时候，这个数会非常难看，而它难看的部分是要用户来承担的。

---

## Q21. 能不能配三个以上的模型？

能，`models` 接受任意长度的列表，按 `cost` 排序后自然形成一个梯子。

但有两个现实约束。默认策略其实是 drafter 加 verifier 的两级思路，你给三个模型，中间那个默认情况下并不参与决策。真要发挥多级效果，得用 `core/cascade.py` 里的 `MultiStepCascadeExecutor`，或者自己定义 `ExecutionPlan`。

另一个是收益递减。级联层数越多，判定开销越多，而且每一层都要重算一次质量，这部分开销是纯加的。

所以实务上我的建议是：先用两级跑出接受率数据，看清楚分布再决定要不要加中间层。上来就配五级，你连哪一级在起作用都不知道。

---

## Q22. 复杂度是怎么判断的？又调了一次模型？

没有。这是很多人的第一反应，但答案是：它不调模型。

`ComplexityDetector` 在 `quality/complexity.py`，1,883 行，做的是确定性判定，用规则和启发式，输出五档：trivial、simple、moderate、hard、expert。

因为是规则，所以零成本、零延迟、结果可预测、可复现。这是它敢放在热路径上的原因。

代价是它可以被绕过。你的查询措辞会显著影响判定结果——同一个问题，加一句"请详细分析"就可能从 simple 跳到 hard。知道这一点，你在做压测构造数据的时候会方便很多。

---

## Q23. 什么时候该用 `complexity_hint`？

当你知道答案的时候：

```python
result = await agent.run(question, complexity_hint="hard")
```

三个典型场景。一是上游已经分类过了，比如这个请求来自"架构咨询"业务线，天然就是 hard，没必要让检测器再猜一遍。二是压测想强制构造某种分布，你要测 expert 档的表现，就直接指定。三是你发现检测器对某类查询系统性低估，先用 hint 兜住，等有空了再去改检测器本身。

---

## Q24. 领域路由怎么开？

两个开关一起给：

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

`routing/domain.py` 有 1,647 行，是这个模块里最重的部分。它之所以值得这么多代码，是因为领域识别的结果会影响阈值判定——同样一个问题，在"医疗"领域应该比在"闲聊"领域判得更严，医疗答错是要出事的。

---

## Q25. 语义检测要装额外依赖吗？

要。语义领域检测和语义质量校验都依赖 embedding 模型，来自 `sentence-transformers` 或者 `fastembed`：

```bash
pip install -e ".[semantic]"
```

不想装也行，把 `use_semantic_domains=False` 用纯规则版，准确度低一些但零依赖。这个取舍看你部署环境——有些环境装 torch 很痛苦，为了几个百分点的准确率不值得。

---

## Q26. 工具路由是在解决什么问题？

`routing/` 下有三个文件管这事：`tool_router.py`、`tool_risk.py`、`tool_complexity.py`。它们回答的是：这次要调的这个工具，风险多高、多复杂，该让哪个模型来决策。

配置项是 `enable_tool_complexity_routing=True`，默认开的。

它解决的问题很具体：查天气和转账是两种完全不同量级的工具调用，不该用同一个模型来决定。查天气让便宜的模型决定就行，转账得出错就是要赔钱的，必须让强的模型来判断参数对不对。

---

## Q27. `force_direct` 该用在哪？

跳过级联，直接走最强模型。三个用途。

调试的时候：你怀疑级联逻辑有问题，先 `force_direct=True` 确认直连的结果是对的，把变量隔离开。

兜底的时候：你检测到某类请求总在升级，与其每次都白试一次，不如直接上。

回归测试的时候：给质量一个上限基准，你后面调阈值调的到底掉了多少质量，跟这个基准比就知道。

```python
result = await agent.run(q, force_direct=True)
```

---

## Q28. `cost` 字段到底填什么？

每 1,000 token 的美元价格。注释里写的是 blended 价，也就是输入输出混在一起估算的一个值。

```python
ModelConfig(name="gpt-4o-mini", provider="openai", cost=0.000375)  # $0.375 / 1M
ModelConfig(name="gpt-4o",      provider="openai", cost=0.00625)   # $6.25 / 1M
```

前面说过它有三重作用——决定排序、参与成本计算、参与 savings 计算。这里再补一句：如果你的 provider 输入输出价差很大（有些模型输入 1 块输出 15 块），用 blended 值会有系统性偏差。按你自己的实际输入输出比例加权算一个，比直接用厂商首页那个数字准。

---

## Q29. 成本是怎么加起来的？

```
total_cost = draft_cost + verifier_cost
```

看起来简单，但这里曾经出过 bug：早期版本在走级联的时候只记了 draft 的成本，把 verifier 漏了。所以你看到的成本比实际低了一大截，账全是错的。

v2.5 的修法值得记一下：把所有计算收进 `telemetry/cost_calculator.py`，让 agent 只负责编排、不自己算钱。这是正确的约束。

所以你要改成本逻辑，改 `CostCalculator`，千万别在 `agent.py` 里加算术。那正是上一轮 bug 的来源。

---

## Q30. `cost_saved` 是怎么算的？

参照系是"全程都用最强模型"。所以：

```
cost_saved = 全程用 verifier 的成本 - 实际成本
```

含义是"因为用了级联，省下了多少"。draft 被接受的时候这个数最大；draft 被拒的时候它可能变成负数，因为你在原本的成本上多付了一次 draft 的钱。

变负数是正常的，不是 bug。它只是如实告诉你这次级联做了一笔亏本买卖。

---

## Q31. 为什么 `total_cost` 和我云厂商账单对不上？

四个原因，我按影响大小排。

最大的是 token 数本身就是估的。`_estimate_tokens_from_text` 用 tiktoken 在本地数，跟 provider 实际计费的口径有出入——它可能算上了 system prompt、可能没算缓存命中的折扣、可能有特殊 token 的处理差异。

第二，`cost` 是 blended 价，不是精确的输入输出分段价。第三，没算 prompt caching 的折扣，Anthropic 和 OpenAI 的缓存命中都是打折的，这里没体现。第四，重试和失败的请求不一定进统计。

所以正确的用法是：把它当相对指标用，比较不同策略谁更省；别当绝对账目用，别拿去对账。这两件事它只能干前一件。

---

## Q32. 批处理是不是能更省？

`core/batch.py` 提供 `BatchProcessor`，配 `BatchConfig` 和 `BatchStrategy`：

```python
from flowgate.core.batch import BatchProcessor, BatchConfig, BatchStrategy
```

有两种策略。`LITELLM_NATIVE` 需要你装了 `litellm`，走 `batch_completion`，是真正的批量提交，能拿到厂商的批处理折扣。`SEQUENTIAL` 不需要任何依赖，就是逐条跑，只是串行封装了一下。

关键的地方在这：没装 litellm 的时候，它会自动退化成 `SEQUENTIAL`（`_resolve_strategy` 里判断 `HAS_LITELLM_BATCH`），不报错。所以你不会发现自己其实没拿到批处理的任何好处，只是觉得"怎么没变快"。这个静默降级挺容易骗人的。

离线任务适合走这条路——数据标注、批量摘要、历史回填。在线请求别用，它换的是吞吐不是延迟。

---

## Q33. 成本预测和异常检测是什么？

`telemetry/` 下有三个进阶文件。`forecasting.py` 基于历史消耗预测未来成本，`anomaly.py` 检测异常消耗（某个 agent 突然开始烧钱），`degradation.py` 检测质量退化。

这三个是给"已经跑在生产上、有人盯着看板"的场景用的。个人项目或者还没上线的阶段，可以先完全忽略它们，不影响你用。

---

## Q34. 流式输出还能级联吗？

能，而且这是它比网关明显强的一点。

网关的流一旦发出去就回不了头了，你没法把已经推给用户的半截内容收回来。进程内不一样，它可以中途切换。

机制是这样的：drafter 边生成边打分，分数不够就在流的中途切到 verifier。代价很真实——用户可能已经看到半截被丢弃的内容，然后突然文字变了。

---

## Q35. `stream()` 会发哪几类事件？

`streaming/base.py` 定义了六种。

`ROUTING` 表示路由决策已经定了，走 direct 还是 cascade。`CHUNK` 是一个文本片段。`DRAFT_DECISION` 告诉你 draft 是否被接受。`SWITCH` 表示正在切换到 verifier。`COMPLETE` 是结束，带最终汇总。`ERROR` 是出错。

用法长这样：

```python
from flowgate.streaming import StreamEventType

async for event in agent.stream("解释一下 Python 的 GIL", max_tokens=300):
    if event.type == StreamEventType.CHUNK:
        print(event.content, end="", flush=True)
    elif event.type == StreamEventType.SWITCH:
        print("\n[模型升级中]", flush=True)
```

---

## Q36. 怎么在界面上提示"正在升级到更强的模型"？

监听 `SWITCH` 事件就行。

这可能是整套流式协议里最有产品价值的一个事件。用户在等的时候，如果知道"要等一下但结果会更好"，体验完全不同于莫名其妙卡住。同样一段等待时间，一个是有解释的，一个是没解释的，感受差很远。

---

## Q37. 流式的情况下还能拿到成本吗？

能。`COMPLETE` 事件里带着汇总信息。你也可以在流结束后直接读 agent 的累计统计：

```python
print(agent.get_stats())
```

---

## Q38. `tools` 参数长什么样？

`run()` 要的是一个普通 dict 列表，每项含 `name`、`description`、`parameters`（JSON Schema）。

`ToolConfig` 是用来定义工具、绑定函数的，`from_function` 能直接从类型注解推导出 schema：

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

如果你要对 schema 完全控制——加枚举值、写默认值、给每个字段写描述——那就手写 `ToolConfig(name=..., description=..., parameters={...}, function=...)`。

有个坑要提醒：`parameters` 必须是合法的 JSON Schema，模型侧不做容错。写错了是静默失效，不报错。你会看到模型根本不调这个工具，然后以为自己哪里逻辑有问题。

---

## Q39. 一次 `run()` 会自动执行工具吗？

默认不会。

`run()` 返回的 `result.tool_calls` 是模型"想调用什么"，执行权在你手里。

```python
result = await agent.run(query, tools=tools)
if result.has_tool_calls:
    for call in result.tool_calls:
        print(call["name"], call["arguments"])   # 只是意图
```

这个设计是刻意的，不是偷懒。工具执行涉及权限，删数据库、发邮件、转账这些操作，一个库不该替你做决定。要自动执行的话，构造函数里传 `tool_executor`。

---

## Q40. 多轮工具循环怎么写？

就是标准 agent 循环：把工具结果塞回 messages，再跑一次。

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

两个细节值得单独说。

第一，`result.tool_calls` 的字段形状随 provider 变。OpenAI 风格是 `{"id","function":{"name","arguments"}}`，有的 provider 拍平成 `{"name","arguments"}`，`arguments` 还可能是 JSON 字符串而不是 dict。官方示例里专门写了 30 多行 `normalize_tool_call()` 来抹平这些差异（在 `examples/tool_execution.py` 第 281 行左右），生产代码建议照抄，别自己猜——这些差异是实际踩出来的坑。

第二，`max_steps`（默认 5）限制单次 `run()` 内部的步数，`max_turns` 是你外层循环的上限。两个都要设。只设一个的话，一个特别爱推理的工具型模型能把你的预算跑穿——它会一直觉得还需要再查一次。

想用库自带的执行器，`ToolExecutor.execute(tool_call)` 接收的是 `ToolCall` 对象（含 `id`、`name`、`arguments`、`provider_format`），比手写 dict 处理省事，但前面那个格式转换的步骤还是得做。

---

## Q41. 工具调用会影响选模型吗？

会。

`ToolRouter` 会先按 `supports_tools` 把不支持工具调用的模型过滤掉，再按复杂度决定谁来处理。

所以如果你的便宜模型不支持 function calling，一定要设 `supports_tools=False`。不设的话它会被选中，然后调用失败——而且失败信息通常不太友好，你得自己往回追。

---

## Q42. harness 是什么？跟 `CascadeAgent` 什么关系？

harness 是一层旁挂在外的约束层。它不改变 `CascadeAgent` 的行为，只是在外围加了预算、追踪、合规的账本。

```python
from flowgate import init, run

init(mode="observe", budget=1.0, max_tool_calls=6)

with run(budget=0.5, max_tool_calls=4) as session:
    result = await agent.run("...")
    print(session.cost, session.budget_remaining)
```

一句话概括分工：`CascadeAgent` 决定"用哪个模型"，harness 决定"还能不能继续花"。

这个分层挺干净的，你加预算控制不需要动 agent 的任何代码。

---

## Q43. `init()` 有哪些参数？

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

传非法值会直接抛 `ValueError`，不会静默忽略。`mode` 必须是那三个值之一，`budget` 不能是负数。

---

## Q44. `mode` 三个值有什么区别？

`off` 是完全关闭，零开销，连记账都不做。这是默认值，所以你不主动初始化的话它什么也不干。

`observe` 只记录成本和决策，不拦截。用来先看真实消耗是多少。

`enforce` 超限就动手，拦下调用，抛 `BudgetExceededError`。

上线顺序我建议这样走：先 `off` 跑通，再 `observe` 跑一周看真实分布，然后把预算设成 p95 消耗的 1.2 倍，最后才切 `enforce`。

直接从 `off` 跳到 `enforce` 特别容易出事——流量尖峰的时候你会把正常用户请求全打死，而且是在你没预料到的时候。先 observe 一周的成本，比省这一周的时间重要得多。

---

## Q45. `with run(...)` 这个作用域是管什么的？

它创建一个作用域账本，里面的参数覆盖 `init()` 的全局值，出了 `with` 块就失效。

典型用法是按请求开作用域：

```python
init(mode="enforce", budget=100.0)         # 全天总额

async def handle(request):
    with run(budget=request.user_daily_remaining) as session:
        ...
```

这就是"全局预算 + 单请求预算"的标准写法。外层管总的，内层管每个用户自己的余额。

---

## Q46. `session` 上能读到什么？

能读的东西不少：

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

最有价值的是 `trace()`。它是审计和调参的依据——每次"为什么走了这条路"都有记录，你不靠猜。

`save()` 也很有用，理由后面 Q50 会说。

---

## Q47. 超预算会怎么样？

`enforce` 模式下抛 `BudgetExceededError`，定义在 `schema/exceptions.py`，从包根可以直接 import。

```python
from flowgate import BudgetExceededError

try:
    with run(budget=0.01) as session:
        await agent.run("很长的任务...")
except BudgetExceededError as e:
    log.warning(f"预算耗尽: {e}")
    return fallback_response()
```

实践上有一条硬要求：一定要在处理函数的最外层捕获，并且准备好降级响应。这是"能不能上生产"的门槛之一，不是可选项。用户不该因为你预算超了就看到一个 500。

---

## Q48. `compliance` 支持哪些值？

`gdpr`、`hipaa`、`pci`、`strict` 四个。设置之后会影响 `guardrails/` 的检查强度，比如 PII 检测（`pii_detector.py`）、内容审核（`content_moderator.py`）。

但边界得说清楚：这层是代码级规则，不是法律合规认证。别把它当成"我们符合 GDPR 了"的证据。它做的是帮你少犯技术性的错，不是替你承担法律责任。

---

## Q49. 没有 key 的情况下怎么预测成本？

用 `simulate()`。它复用确定性的复杂度检测和领域路由，逐条投影每条查询"会落到哪个模型"，然后按 `cost` 算总账。

```python
report = simulate(queries, models=[drafter, verifier], quality_threshold=0.7)
print(f"预估成本 ${report.projected_cost:.4f}")
print(f"预估升级率 {report.escalation_rate:.1%}")
print(f"模型分布 {report.model_distribution}")
```

返回 `SimulationResult`，含 `total_queries`、`projected_cost`、`escalation_rate`、`model_distribution`、`complexity_distribution`、`domain_distribution`。

我再强调一次这是选型阶段最该先跑的 API。把你的真实查询样本丢进去，先看升级率。如果升级率是 80%，说明你的流量本来就难，级联省不了钱，那就别浪费两周去调阈值——方向错了，调参救不回来。

---

## Q50. 怎么用真实流量做回放？

`simulate()` 的 `queries` 参数除了接受字符串列表，还接受 JSONL 文件路径。文件里每行一个带 `query` 字段的对象——正好就是会话导出（`session.save()`）的格式。

所以整套流程是闭环的：生产上跑一段 `observe` 模式，导出会话，回放模拟，按报告调阈值，再发布。不用花钱，也不用造数据，用的就是真实分布。

---

## Q51. LangChain 怎么接？

先装可选依赖：

```bash
pip install -e ".[langchain]"
```

然后：

```python
from flowgate.integrations.langchain import FlowGate

llm = FlowGate(...)
```

实现住在 `flowgate/integrations/langchain/`，11 个文件，其中 `wrapper.py` 有 2,046 行。

顺便澄清一个容易误判的地方：`flowgate/langchain/` 那个单文件目录看着像重复，其实是向后兼容的转发 shim，实现并不在那儿。别删它，删了老代码的 import 会断。

另外注意，这个模块 import 的时候就要求 `langchain_core`，没装的话直接 `ModuleNotFoundError`。那不是代码坏了，是依赖没装。

---

## Q52. OpenAI Agents SDK 呢？

```python
from flowgate.integrations.openai_agents import ...
```

对应文件是 `integrations/openai_agents.py`。这个集成有个特点：它会主动调用预算检查并抛 `BudgetExceededError`（在第 206 行附近），是少数几个默认就会拦截的集成。

---

## Q53. CrewAI、PydanticAI、Google ADK 呢？

这三个都有独立的 harness 适配，模式完全一致：先 `init()`，再 `enable()`，然后在 `with run(...)` 里跑原生代码。

```python
from flowgate.integrations.crewai import CrewAIHarnessConfig, enable

init(mode="observe", budget=1.0, max_tool_calls=6)
enable(config=CrewAIHarnessConfig(fail_open=True, enable_budget_gate=True))

with run(budget=0.5, max_tool_calls=4) as session:
    result = crew.kickoff()
    print(session.cost, session.trace())
```

`fail_open=True` 的意思是：集成钩子不可用的时候放行，而不是报错。生产上建议设 True，本地调试时用 False 好发现问题——这个取舍跟熔断器的思路是一样的。

---

## Q54. Vercel AI SDK 和 n8n 呢？

这两个是 TypeScript 侧的事。

`packages/integrations/vercel-ai/` 是 Vercel AI SDK 的适配。`packages/integrations/n8n/` 是 n8n 节点，包名 `@flowgate/n8n-nodes-flowgate`，含 `FlowGateAgent` 和 `LmChatFlowGate` 两个节点。

n8n 那条路适合不写代码的团队：拖节点、填 key、配好模型对，就能跑级联。这是它相对 SDK 集成的唯一优势——门槛低。

---

## Q55. HTTP 网关模式适合什么场景？

`proxy/server.py`，1,605 行，启动命令是 `flowgate-gateway`。

它适合一种情况：改不了代码的系统。老应用、第三方 SaaS、写死了 endpoint 的客户端。它们只认 HTTP，那你就把 flowgate 伪装成一个 OpenAI 兼容端点，让它们连上来。

代价是丢掉所有进程内的能力——拿不到 agent 状态、看不到工具调用、不知道这是第几步，退化成普通网关。所以优先选 SDK 集成，网关当兜底方案，别当主方案。

---

## Q56. 配置的优先级是什么？

三层，从高到低：代码参数（`init()` 或 `CascadeAgent(...)` 里传的）、配置文件 `.flowgate.json`、环境变量 `FLOWGATE_*`。

解析逻辑在 `harness/api.py` 的 `_read_file_config()` 和 `_read_env_config()`。

这里有个必须记住的点：这个顺序跟常见约定是反的。多数框架是"环境变量覆盖配置文件"，这里是代码 > 文件 > 环境变量。部署的时候特别容易踩——你在 K8s 里改了环境变量，发现没生效，然后怀疑镜像没更新，其实是被配置文件压住了。

---

## Q57. 有哪些环境变量？

前缀统一是 `FLOWGATE_`（从上游的 `CASCADEFLOW_` 改过来的，所以网上搜到的老资料前缀不一样）。

harness 相关的有 `FLOWGATE_MODE` 和 `FLOWGATE_HARNESS_MODE` 两个模式变量（后者是显式版），`FLOWGATE_BUDGET` 和 `FLOWGATE_HARNESS_BUDGET` 两个预算变量，`FLOWGATE_HARNESS_MAX_TOOL_CALLS` 管工具调用上限，`FLOWGATE_HARNESS_MAX_LATENCY_MS` 管延迟上限，`FLOWGATE_HARNESS_KPI_TARGETS` 和 `FLOWGATE_HARNESS_KPI_WEIGHTS` 收 JSON，`FLOWGATE_HARNESS_COMPLIANCE` 是合规档位。

另外 `FLOWGATE_CONFIG` 指定配置文件路径，`FLOWGATE_DECISION_LOG` 指定决策日志路径，`FLOWGATE_GATEWAY_URL` 是网关地址。

完整清单在 `.env.example` 里，那个文件比这里全。

---

## Q58. 多租户、多渠道怎么配？

`CascadeAgent` 的构造参数里有四个相关的：

```python
CascadeAgent(
    models=[...],
    tenant_rules={"tenant_a": {...}},        # 按租户覆写路由
    channel_models={"web": ["gpt-4o-mini"]}, # 按渠道限制可用模型
    channel_failover={"web": "backup"},      # 渠道故障转移
    channel_strategies={"web": "cheap_first"},
)
```

调用时传 `tenant_id=` 和 `channel=` 激活。

这套东西是给"一个服务多个客户"或者"一个后端多个前端渠道"的场景准备的。个人项目大概率用不到，先跳过没关系。

---

## Q59. 怎么部署？

三种形态，按侵入性从小到大排。

最推荐的是同进程库：`pip install` 进你的服务，跟业务代码一起跑。延迟最低，能力最全，所有进程内的信息都拿得到。

其次是网关服务：`flowgate-gateway` 独立跑起来，业务方当它是 OpenAI endpoint。适合改不了代码的系统。

最后是 MCP server：`flowgate-mcp`，给 MCP 客户端用。

不管选哪种，生产环境记得配 `FLOWGATE_MODE=enforce` 加一个合理的 `budget`，并在最外层捕获 `BudgetExceededError`。这三件事缺一个都不算能上生产。

---

## Q60. 想加一个新 provider 怎么做？

继承 `BaseProvider`（`providers/base.py`，1,695 行），实现核心方法，然后注册进 `PROVIDER_REGISTRY`。

```python
from flowgate.providers.base import BaseProvider, ModelResponse

class MyProvider(BaseProvider):
    async def complete(self, model: str, messages, **kwargs) -> ModelResponse:
        ...

PROVIDER_REGISTRY["myprovider"] = MyProvider
```

关键在 `ModelResponse`——它是统一返回结构，级联层只认这个，不认各家 SDK 自己的对象。这正是它能同时支持 9 个 provider 的原因，也是你接新 provider 时唯一必须严格对齐的东西。

---

## Q61. 想换掉质量校验逻辑怎么办？

两种做法，先试轻的。

轻的是改配置：调 `QualityConfig` 的阈值、长度要求、具体性要求。坦白说 80% 的需求在这一层就能解决，不用写代码。

重的是换校验器：`QualityValidator` 本身是可替换的，`ComparativeValidator` 是另一种实现——用两个模型对比答案，更准但更慢，所以默认关着。可以看 `examples/custom_validation.py`。

如果你要接自己的评估模型（比如用另一个 LLM 打分），从 `ComparativeValidator` 抄结构最快，它已经把"两个模型怎么对比"这件事的骨架搭好了。

---

## Q62. 自定义路由怎么写？

继承 `Router`（`routing/base.py`）实现 `route()`，然后塞进 `RouterChain`：

```python
from flowgate.routing.base import Router, RouterChain

class MyRouter(Router):
    def route(self, query, context):
        ...

agent = CascadeAgent(models=[...], rule_engine=RuleEngine(...))
```

不过更轻量的做法是往 `rules/engine.py` 里加规则，`rules/decision.py` 定义了决策结构。加规则不用改代码结构，也不用理解 Router 链的调度顺序，对我来说这是默认选项。

---

## Q63. 钱没省下来，从哪开始查？

按顺序看四个数，基本能定位到原因。

先看升级率——离线的 `report.escalation_rate`，或者线上统计 `result.draft_accepted` 的比例。超过 60% 就别指望省钱了，接受率太低，级联只是在给每次请求加一道手续费。

再看 `result.complexity` 的分布。如果大量是 hard 和 expert，说明你的流量本身就不适合级联，这不是配置问题。

然后看 `result.routing_strategy`。如果大量是 direct，说明根本没试小模型，你调阈值也没用。

最后看 `result.rejection_reason`。如果大量是"太短"或"太含糊"，那不是模型能力问题，是提示词问题。

第四条最常被忽略，但往往最容易修。小模型其实答对了，只是答得太短被长度阈值拒掉了。加一句"请详细解释"就能把接受率拉上去一截。这种情况在线上非常常见。

---

## Q64. 一直报 `BudgetExceededError` 是怎么回事？

三个原因，一个一个排。

最常见的是单位搞错了。`budget` 的单位是美元，你是不是填了 0.001 这种量级？那个额度只够跑几个 token。

第二个是作用域嵌套了，内层被外层的残值限制住了。外层已经花掉 90%，内层给 0.5 实际只剩 0.05 可用。

第三个是前面有失败的请求也计了费——provider 那边 token 已经消耗了，钱是要付的。

排查方法很简单：先用 `mode="observe"` 跑一遍，看 `session.cost` 实际到多少，再定预算。别拍脑袋给数字。

---

## Q65. 延迟变高了？

先看 `result.cascade_overhead_ms`，这个数直接告诉你级联是不是元凶。

如果是 0，那级联没问题，去查 provider 本身——换个快的（比如 Groq）试试。

如果它接近 draft 的耗时，说明 draft 经常被拒，测试成本直接变成了延迟成本。这种情况下你等于给每个请求都加了一次白等的往返。

两种缓解：对已知的难查询用 `force_direct` 跳过试错，或者换一个更快、接受率更高的 drafter。前者治标，后者治本。

---

## Q66. 结果质量下降了怎么办？

这是级联的固有代价，不可能完全消除。三个补偿手段。

提高对应难度档的阈值，直接改 `confidence_thresholds`。这是最直接的。

关掉 `enable_adaptive`，避免阈值漂移。自适应在长期看是好事，但在你还没摸清分布的时候，它会让你没法复现问题。

用严格预设，比如 `QualityConfig.for_production()`，如果这是面向客户的质量敏感场景。

最后记住设计文档里的那个取舍：默认配置是"用 3% 质量换 28% 接受率和 2 倍速度"。这个交换在客服场景是划算的，在合同条款场景是不划算的。配置没有绝对的好坏，只有配错场景。

---

## 关于这个仓库，得说实话

因为你在读的是一个改名后的衍生仓库，这一节不能省。

技术来源上，代码基于 [cascadeflow](https://github.com/lemony-ai/cascadeflow)（MIT License，Copyright 2025 Lemony Inc.）。这个仓库做的是包名、命名空间、CLI、npm scope、环境变量前缀的重命名，以及文档重写。LICENSE 保留原版权声明，衍生关系记录在 `NOTICE.md`。

已验证的部分：Python 侧 1,008 个测试通过。另有 12 个失败是因为环境缺 `sentence-transformers`，2 个模块因缺 `numpy` 和 `google-adk` 无法收集——都跟改名无关。核心链路的 `import`、`CascadeAgent.run`、`server`、`mcp_server` 都正常。

还没验证的部分也得列清楚。TypeScript 侧没跑过 `tsc` 和 `pnpm test`，因为当前环境没装 node_modules。n8n 节点的产品截图还是上游界面，跟改名后的节点名不一致。README 里那些成本节省数字（69%、93%）是上游的基准数据，在本仓库没有复现过。

所以怎么引用它：说"基于 cascadeflow 的二次开发与改造"是准确的。说"自研的级联框架"不准确——源码结构、算法、测试都是上游的，面试时被问一句源码就露。

要让它真正变成自己的东西，两个最有价值的切入点：一是做一份 Python 和 TypeScript 的能力对照表，把漂移点标出来；二是拆掉 `agent.py` 那个 3,346 行的上帝对象，它是现在所有改动的瓶颈。

---

## 附录：模块地图

`flowgate/agent.py` 是唯一编排入口，3,346 行，`run`、`run_streaming`、`stream_events`、`run_batch` 都在这里。

`flowgate/core/cascade.py` 1,855 行，装着三种级联策略和执行计划。

质量这层有两个大文件：`quality/alignment_scorer.py` 2,281 行做对齐打分，`quality/complexity.py` 1,883 行做复杂度检测。

`flowgate/routing/` 13 个文件，管预路由、领域、复杂度、工具路由。

`flowgate/providers/` 11 个文件，是 9 个 provider 的适配。

`flowgate/telemetry/` 9 个文件，管成本、指标、异常、预测。

`flowgate/harness/` 5 个文件，是预算与追踪的旁挂层。

`flowgate/guardrails/` 4 个文件，做 PII 和内容审核。

`flowgate/proxy/server.py` 1,605 行，是 HTTP 网关。

`flowgate/integrations/` 9 个单文件加 4 个子包，是各家框架的适配。

`packages/core/` 是 40 多个 TS 模块，Python 的平行实现。

Python 侧合计大概 70,500 行，167 个文件，31 个子包。

## 附录：几个术语

drafter 是先试的那个便宜模型，就是按 `cost` 排序后的第一个。verifier 是兜底的强模型。

接受率是 draft 通过质量判定的比例，它决定省钱效果，是整个系统的核心指标。

direct 是跳过试错直接调强模型，cascade 是先 draft 后 verifier 的常规路径。

质量分是对 draft 答案的 0 到 1 打分，阈值是这个分必须达到的门槛，按复杂度分档。

升级是 draft 被拒后调用 verifier 这个动作。

`cascade_overhead_ms` 是级联决策造成的净浪费延迟。

harness 是预算和 trace 的旁挂约束层，不改变主流程。

`cost_saved` 是相对"全程用最强模型"省下的钱。

---

写到这里，从"跑通第一个例子"到"上线并排查成本异常"的链路基本覆盖了。

真到要动手改代码的时候，从两处切入就够了：`agent.py` 的 `run()`，和 `core/cascade.py` 的 `SpeculativeCascade`。其余模块都是被这两个调用的，你把这两个的主流程读通了，剩下的都是按需翻。
