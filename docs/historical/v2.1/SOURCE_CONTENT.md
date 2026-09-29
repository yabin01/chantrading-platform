# ChanLun 1M Trading Agent 技术规格 v2.1

## SegmentEngine：线段特征序列与实时状态机

> 版本：v2.1  
> 固定交易周期：1分钟  
> 上级版本：v2.0 BiEngine  
> 本版本性质：核心结构引擎

---

## 1. v2.1目标

将已经确认的笔：

```text
Confirmed Bi
↓
特征序列
↓
标准特征序列
↓
特征序列分型
↓
线段候选
↓
线段确认
```

实现成可编码、可逐K实时运行、可回放、无未来函数的实时状态机。

核心原则：

> 线段不能简单定义成“三笔”。至少三笔是最低结构基础之一，但真正的线段确认必须依据特征序列及其分型、缺口和破坏规则。

---

## 2. 系统位置

```text
Raw K
 ↓
包含关系
 ↓
StandardBar
 ↓
Fractal
 ↓
Bi
 ↓
Feature Sequence
 ↓
Standard Feature Sequence
 ↓
Feature Fractal
 ↓
Segment
 ↓
Center
 ↓
1分钟走势 Ai
 ↓
同级别分解
 ↓
MACD力度
 ↓
盘整背驰
 ↓
Decision Agent
 ↓
BUY / HOLD / SELL
 ↓
Risk / Stop Loss
 ↓
Hummingbot Executor
```

---

## 3. 线段不是简单“三笔”

错误：

```text
Bi1 + Bi2 + Bi3 = Segment
```

正确：

```text
Bi序列
↓
确定线段方向
↓
抽取特征序列
↓
处理特征序列包含关系
↓
标准特征序列
↓
寻找特征序列分型
↓
检查缺口
↓
检查线段破坏条件
↓
确认线段
```

因此：

```text
3 Bi ≠ Automatically Confirmed Segment
```

---

## 4. 两种线段与特征序列

向上开始的线段：

```text
S1 X1 S2 X2 S3 X3 ...
```

其特征序列：

```text
X1 X2 X3 ...
```

向下开始的线段：

```text
X1 S1 X2 S2 X3 S3 ...
```

其特征序列：

```text
S1 S2 S3 ...
```

即：

```text
UP Segment
→ DOWN Feature Sequence

DOWN Segment
→ UP Feature Sequence
```

---

## 5. FeatureElement

```python
@dataclass
class FeatureElement:

    id: str
    source_bi_id: str

    direction: BiDirection

    high: float
    low: float

    start_time: int
    end_time: int

    source_start_index: int
    source_end_index: int
```

必须保留：

```text
source_bi_id
```

从而形成完整回溯链：

```text
FeatureElement
↓
Bi
↓
Fractal
↓
StandardBar
↓
RawBar
```

---

## 6. FeatureSequence

```python
@dataclass
class FeatureSequence:

    id: str

    segment_direction: SegmentDirection

    elements: list[FeatureElement]

    start_bi_id: str
    current_bi_id: str

    status: FeatureSequenceStatus
```

---

## 7. 特征序列缺口

对于同一特征序列中的相邻元素：

```text
F1 = [low1, high1]
F2 = [low2, high2]
```

如果：

```text
high1 < low2
```

或者：

```text
high2 < low1
```

则存在：

```text
Gap
```

```python
@dataclass
class FeatureGap:

    left_element_id: str
    right_element_id: str

    gap_low: float
    gap_high: float

    direction: BiDirection

    is_open: bool
    is_closed: bool
```

---

## 8. 特征序列包含关系

包含关系只能在：

```text
同一个 FeatureSequence
```

内部讨论。

若：

```text
F1.low <= F2.low
and
F1.high >= F2.high
```

或反向，则存在包含。

不同特征序列之间：

```text
禁止直接讨论包含关系
```

---

## 9. StandardFeatureSequence

原始：

```text
F1 F2 F3 F4 ...
```

处理包含：

```text
F1 + F2
↓
F12
```

形成：

```text
StandardFeatureSequence
```

```python
@dataclass
class StandardFeatureElement:

    id: str

    source_feature_ids: list[str]

    high: float
    low: float

    direction: BiDirection

    source_bi_ids: list[str]
```

---

## 10. 包含处理必须方向敏感

不能机械使用：

```python
high = max(high1, high2)
low = min(low1, low2)
```

必须依据：

```text
FeatureSequence direction
```

决定合并后的高低点。

```python
merge_feature_elements(
    left,
    right,
    trend_direction
)
```

---

## 11. 特征序列分型

标准特征序列可以形成：

```text
Feature Top
Feature Bottom
```

但在线段破坏判断中，需要依据当前线段方向选择对应的关键分型：

```text
UP Segment
→ Feature Top

DOWN Segment
→ Feature Bottom
```

---

## 12. FeatureFractal

```python
@dataclass
class FeatureFractal:

    id: str

    type: FeatureFractalType

    center_element_id: str

    left_element_id: str
    right_element_id: str

    high: float
    low: float

    confirmed: bool
    confirmation_time: int
```

必须区分：

```text
FeatureFractal
```

和：

```text
SegmentConfirmed
```

前者只是线段破坏候选结构。

---

## 13. 第一类线段破坏

若特征序列分型的关键元素之间满足原典规定的缺口条件，则进入：

```text
TYPE_1_BREAK
```

随后：

```text
SegmentBreakCandidate
↓
确认
↓
SegmentClosed
```

---

## 14. 第二类线段破坏

如果出现特征序列分型，但没有满足第一类破坏的缺口条件：

```text
不能立即结束线段
```

必须继续观察：

```text
后续特征序列
+
反向特征序列
+
后续分型
```

因此：

```text
FeatureFractal ≠ SegmentClosed
```

---

## 15. 第二类破坏实时流程

```text
FeatureFractal
↓
检查第一类条件
↓
满足？
 ├─ YES → TYPE_1
 └─ NO
      ↓
TYPE_2 Candidate
      ↓
继续观察
      ↓
满足第二类破坏条件？
 ├─ YES → SegmentConfirmed
 └─ NO → Segment继续延伸
```

具体第二类条件必须按原典规则逐项编码，不能简化成单纯的价格突破。

---

## 16. SegmentPhase

```python
class SegmentPhase(Enum):

    BUILDING = 0
    EXTENDING = 1
    BREAK_CANDIDATE = 2
    CONFIRMING = 3
    CONFIRMED = 4
```

---

## 17. Segment对象

```python
@dataclass
class Segment:

    id: str

    direction: SegmentDirection
    phase: SegmentPhase

    start_bi_id: str

    current_end_bi_id: str | None
    confirmed_end_bi_id: str | None

    feature_sequence_id: str

    start_price: float
    current_extreme_price: float
    end_price: float | None

    confirmed_at: int | None

    absorbed_bi_ids: list[str]

    feature_fractal_id: str | None
    break_type: str | None

    superseded_by: str | None
```

---

## 18. Candidate与Confirmed严格分离

必须同时维护：

```text
current_end_bi_id
```

和：

```text
confirmed_end_bi_id
```

因为：

```text
候选终点 ≠ 最终终点
```

后续走势可能使候选失效。

---

## 19. Segment状态机

正常路径：

```text
BUILDING
↓
EXTENDING
↓
BREAK_CANDIDATE
↓
CONFIRMING
↓
CONFIRMED
```

允许：

```text
CONFIRMING
↓
EXTENDING
```

表示原线段结束候选被后续结构否定，原线段继续延伸。

---

## 20. 线段不能使用未来数据确认

在时刻：

```text
t
```

只能使用：

```text
K[0 ... t]
```

禁止：

```python
future_min()
future_max()
future_fractal()
future_segment()
```

也禁止用历史回看结果提前修改当下状态。

---

## 21. 线段被笔破坏

在旧线段尚未真正被破坏之前：

```text
后续Bi
```

仍处于旧线段假设框架。

一旦某笔真正破坏旧线段：

```text
Old Segment
↓
Broken By Bi
```

后续特征序列归属必须重新判断。

因此：

```text
不能预先永久把未来Bi写入旧Segment。
```

---

## 22. 候选端点替换

例如：

```text
Segment1
candidate_end = Bi8
```

后续：

```text
Bi10
```

使Bi8对应候选失效。

则：

```text
Bi8 → superseded
Bi10 → current candidate
```

不能直接：

```text
Segment1 confirmed
Segment2 created
```

---

## 23. SegmentExtension

如果线段尚未满足终结条件：

```text
新Bi
↓
加入FeatureSequence
↓
处理包含
↓
重新生成StandardFeatureSequence
↓
重新检测FeatureFractal
↓
重新评估破坏条件
```

结果可能仍然是：

```text
Segment继续延伸
```

---

## 24. SegmentEngine接口

```python
class SegmentEngine:

    def on_bi_confirmed(self, bi):
        ...

    def on_bar_closed(self, standard_bar):
        ...

    def get_current(self):
        ...

    def get_confirmed_segments(self):
        ...

    def snapshot(self):
        ...

    def events(self):
        ...
```

---

## 25. 事件模型

### FeatureElementAdded

```python
@dataclass
class FeatureElementAdded:

    feature_sequence_id: str
    feature_element_id: str
    source_bi_id: str
    timestamp: int
```

### FeatureElementsMerged

```python
@dataclass
class FeatureElementsMerged:

    feature_sequence_id: str

    source_element_ids: list[str]
    new_element_id: str

    high: float
    low: float

    timestamp: int
```

### FeatureFractalConfirmed

```python
@dataclass
class FeatureFractalConfirmed:

    feature_sequence_id: str
    fractal_id: str
    type: FeatureFractalType
    center_element_id: str
    confirmation_time: int
```

### SegmentBreakCandidate

```python
@dataclass
class SegmentBreakCandidate:

    segment_id: str
    break_type: str

    feature_fractal_id: str
    triggering_bi_id: str

    timestamp: int
```

### SegmentClosed

```python
@dataclass
class SegmentClosed:

    segment_id: str
    direction: SegmentDirection

    start_bi_id: str
    end_bi_id: str

    break_type: str
    confirmation_time: int
```

---

## 26. EventLog

结构事件采用追加式日志：

```text
Event 1
Event 2
Event 3
...
```

不直接覆盖历史事件。

若开发/回放中发现结构实现错误，可以产生：

```text
CorrectionEvent
```

以便审计。

---

## 27. Segment完整回溯

任何确认线段必须能追溯：

```text
Segment
↓
FeatureSequence
↓
FeatureElement
↓
Bi
↓
Fractal
↓
StandardBar
↓
RawBar
```

这是：

```text
回测
审计
解释Agent决策
```

的基础。

---

## 28. MACD / EMA职责边界

SegmentEngine不允许用：

```text
MACD
EMA5
EMA10
```

定义线段。

它们属于：

```text
Momentum / Context Layer
```

结构层只负责：

```text
Fractal
Bi
FeatureSequence
Segment
```

MACD最终负责：

```text
力度
+
盘整背驰
```

EMA5/EMA10主要辅助：

```text
分型精确确认
过滤部分中继分型
```

但不能反向修改已经由结构规则确定的线段定义。

---

## 29. 插针行情

加密市场必须重点测试：

```text
1分钟瞬间插针
```

例如：

```text
快速上冲
↓
立即回落
```

结构层仍严格：

```text
OHLC
→
包含
→
分型
→
笔
→
特征序列
→
线段
```

风险层再根据：

```text
最近确认分型极值
```

设置止损。

---

## 30. SegmentEngine禁止产生交易信号

禁止：

```text
BUY
SELL
HOLD
盘整背驰
趋势背驰
MACD入场
EMA入场
```

SegmentEngine只回答：

> 截至当前，已经确认的笔组成了怎样的线段结构？

---

## 31. A0～An接口

SegmentEngine输出：

```text
S0
S1
S2
S3
...
Sn
```

CenterEngine负责：

```text
Segment
↓
Center
```

AiEngine负责：

```text
进入段
+
中枢
+
离开段
↓
A0 ... An
```
