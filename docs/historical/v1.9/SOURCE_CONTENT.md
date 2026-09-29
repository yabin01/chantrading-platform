# ChanLun 1M Trading Agent 技术规格 v1.9

## K线包含关系 → 分型 Engine 数学与状态机规格

> 版本：v1.9  
> 固定周期：1分钟  
> 上级版本：v1.8  
> 本版本目标：建立可以直接编码、回放、单元测试的“标准化K线 → 分型”底层引擎。

---

# 1. 本版本为什么是整个系统最关键的一层

本项目所有后续结构：

```text
分型
↓
笔
↓
线段
↓
中枢
↓
Ai
↓
同级别分解
↓
盘整背驰
↓
交易
```

都建立在分型之上。

因此 v1.9 不追求“看起来像缠论”，而追求：

> **给定完全相同的K线输入，任何时间点都得到完全相同的分型状态。**

必须做到：

```text
无未来函数
无主观判断
无随机性
可逐K回放
可解释
可审计
可单元测试
```

---

# 2. 原典约束

第62课给出了分型、笔和包含关系的基础定义，并明确指出：相邻K线存在包含关系时，需要按当前方向处理为新的K线；同时，两个相邻顶、底之间才构成笔，而顶底之间至少需要保留一个独立K线作为基本要求。citeturn0search0turn0search28

因此本系统不能直接对原始K线：

```python
high[i-1], high[i], high[i+1]
```

做分型。

必须先：

```text
原始K线
↓
包含关系处理
↓
标准化K线
↓
标准化K线上的分型
```

这是 v1.9 的第一原则。

---

# 3. 数据源

本项目最低输入：

```text
timestamp
open
high
low
close
volume（可选）
```

策略辅助数据：

```text
MACD DIF
MACD DEA
MACD Histogram
EMA5
EMA10
```

但：

> **EMA和MACD不得参与分型的数学定义。**

它们只能在后续阶段：

```text
过滤
确认
力度判断
盘整背驰
```

中使用。

---

# 4. RawBar

```python
@dataclass(frozen=True)
class RawBar:

    index: int
    timestamp: int

    open: float
    high: float
    low: float
    close: float

    volume: float | None = None
```

---

# 5. StandardBar

包含关系处理以后生成：

```python
@dataclass
class StandardBar:

    id: str

    source_indices: list[int]

    timestamp_start: int
    timestamp_end: int

    open: float
    high: float
    low: float
    close: float

    direction: Direction | None

    source_count: int
```

---

# 6. StandardBar的关键原则

一个标准K线：

```text
可以对应1根原始K线
```

也可以：

```text
对应多根原始K线
```

例如：

```text
Raw #100
Raw #101
Raw #102
```

发生连续包含：

```text
→ Standard #80
```

因此：

```text
StandardBar.source_indices
```

必须保存完整映射。

---

# 7. 为什么必须保存source_indices

未来如果Agent说：

```text
12:31出现底分型
```

我们必须能够反查：

```text
该标准K线
↓
由哪些原始1分钟K线合并而来
```

否则：

```text
交易价格
止损价格
成交K线
```

都无法精确审计。

---

# 8. 包含关系定义

两根K线A、B存在包含关系：

```text
A.high >= B.high
and
A.low <= B.low
```

或：

```text
B.high >= A.high
and
B.low <= A.low
```

即：

```text
一根K线的高点不低于另一根
同时低点不高于另一根。
```

---

# 9. 包含关系不是简单删除K线

错误：

```python
if contains(a, b):
    delete(b)
```

正确：

```text
A + B
↓
判断当前处理方向
↓
按方向生成新的StandardBar
```

---

# 10. 向上处理

当当前结构方向为：

```text
UP
```

包含K线处理：

```text
new_high = max(A.high, B.high)
new_low  = max(A.low, B.low)
```

即：

> 取两者最高点作为高点，取两者较高的低点作为低点。

第62课对这一处理方式有明确说明。citeturn0search28

---

# 11. 向下处理

当当前结构方向为：

```text
DOWN
```

处理：

```text
new_high = min(A.high, B.high)
new_low  = min(A.low, B.low)
```

即：

> 取两者最低点作为低点，取两者较低的高点作为高点。

---

# 12. Direction不能随便指定

包含处理的方向不能由：

```text
当前K线涨跌
```

简单决定。

不能写：

```python
direction = UP if close > open else DOWN
```

因为：

```text
K线阳阴
```

不等于：

```text
缠论结构方向
```

---

# 13. 包含处理器需要自己的状态

```python
@dataclass
class InclusionState:

    direction: Direction | None

    bars: list[StandardBar]

    last_non_contained_relation: str | None
```

---

# 14. Direction推断

初始状态：

```text
UNKNOWN
```

当连续标准K线出现明确的高低点变化后：

```text
UP
```

或：

```text
DOWN
```

一旦确定：

```text
direction
```

用于处理之后的包含关系。

---

# 15. InclusionEngine

```python
class InclusionEngine:

    def update(self, raw_bar: RawBar) -> list[StandardBar]:

        # 1. 创建临时StandardBar
        # 2. 与最后一根标准K线判断包含关系
        # 3. 若不包含，直接加入
        # 4. 若包含，根据方向合并
        # 5. 若合并后继续与前一根包含，递归/循环处理
        # 6. 返回发生变化的标准K线
```

---

# 16. 为什么需要循环而不是一次合并

可能出现：

```text
A
B 包含A
C 又包含AB合并结果
D 又包含ABC合并结果
```

所以：

```python
while contains(last, new):
    merge(...)
```

直到：

```text
不再存在包含关系。
```

---

# 17. 标准K线必须允许“重写当前端点”

这是实时系统的关键。

例如：

```text
StandardBar #50
```

可能因为下一根原始K线：

```text
被包含合并
```

从：

```text
high=200
low=190
```

变成：

```text
high=202
low=195
```

所以：

> **未形成稳定结构前，当前标准K线不是immutable。**

只有进入已经确认的结构历史后才冻结。

---

# 18. Fractal数学定义

标准K线序列：

```text
K[i-1], K[i], K[i+1]
```

顶分型：

```text
K[i].high > K[i-1].high
K[i].high > K[i+1].high

K[i].low > K[i-1].low
K[i].low > K[i+1].low
```

底分型：

```text
K[i].low < K[i-1].low
K[i].low < K[i+1].low

K[i].high < K[i-1].high
K[i].high < K[i+1].high
```

这里的严格程度必须由项目规则固定，不能运行中改变。

---

# 19. 注意：原典定义与工程规则要分层

第62课原始定义是几何定义。

本项目工程层必须另外明确：

```text
相等高点怎么办？
相等低点怎么办？
连续多个候选顶怎么办？
连续多个候选底怎么办？
包含处理后时间映射怎么办？
```

因此：

```text
CanonicalRule
```

和：

```text
EngineeringPolicy
```

必须分开。

---

# 20. FractalCandidate

```python
@dataclass
class FractalCandidate:

    id: str

    fractal_type: FractalType

    center_bar_id: str

    center_standard_index: int

    candidate_high: float
    candidate_low: float

    detected_at: int

    confirmation_bar_id: str | None

    state: StructureState
```

---

# 21. 分型不是在中心K线出现时立即确认

例如：

```text
K1 K2 K3
```

K2看起来是顶。

但系统直到：

```text
K3完成
```

才拥有右侧信息。

所以：

```text
center_time != confirmation_time
```

这是实时Agent必须遵守的规则。

---

# 22. Fractal确认延迟

如果：

```text
中心K线 = t
```

至少需要：

```text
右侧确认K线
```

出现后才能：

```text
CONFIRMED
```

因此交易不会在：

```text
分型中心K线收盘瞬间
```

无条件执行。

而是在：

```text
分型确认事件
```

产生以后才允许进入交易决策层。

---

# 23. 分型确认后的第一道过滤：方向交替

缠论分型进入笔系统后，核心是：

```text
TOP
BOTTOM
TOP
BOTTOM
```

而不是：

```text
TOP
TOP
TOP
```

因此FractalEngine必须维护：

```python
last_valid_fractal_type
```

---

# 24. 连续同类分型

例如：

```text
TOP1
TOP2
```

不能简单地：

```text
保留两个独立顶
```

而应该进入：

```text
CandidateReplacement
```

判断：

```text
TOP2是否比TOP1更强？
```

如果：

```text
TOP2.high > TOP1.high
```

则：

```text
TOP1 → SUPERSEDED
TOP2 → CURRENT_TOP
```

---

# 25. 底分型同理

```text
BOTTOM1
BOTTOM2
```

若：

```text
BOTTOM2.low < BOTTOM1.low
```

则：

```text
BOTTOM1 → SUPERSEDED
BOTTOM2 → CURRENT_BOTTOM
```

---

# 26. 但“更高顶替代旧顶”不能直接等同于“一定成笔”

这是本项目特别重要的一条。

例如：

```text
TOP1
 ↓
BOTTOM1
 ↓
TOP2
```

如果：

```text
TOP2 > TOP1
```

不能简单说：

```text
TOP1 → TOP2 = 一笔
```

必须进入：

```text
BiEngine
```

检查：

```text
顶底相邻性
独立K线
结合律
笔的有效条件
```

因此：

```text
FractalEngine
```

只负责：

```text
“哪些分型候选是当前有效端点”
```

而：

```text
BiEngine
```

负责：

```text
“哪些有效分型能够组成笔”
```

---

# 27. 中继分型必须在Fractal层预留状态

```python
class FractalRole(Enum):

    UNKNOWN = "UNKNOWN"

    STRUCTURAL_ENDPOINT = "STRUCTURAL_ENDPOINT"

    POSSIBLE_MIDDLE = "POSSIBLE_MIDDLE"

    MIDDLE = "MIDDLE"

    TRADE_ENDPOINT = "TRADE_ENDPOINT"
```

---

# 28. 为什么不能太早判定MIDDLE

这是缠论“当下性”的核心。

例如：

```text
F1 TOP
F2 BOTTOM
```

此时不能因为：

```text
F2距离F1太近
```

就永久判定：

```text
F2 = MIDDLE
```

因为未来走势还没有发生。

正确：

```text
F2 = POSSIBLE_MIDDLE
```

等后续结构完成后再决定：

```text
MIDDLE
```

或者：

```text
STRUCTURAL_ENDPOINT
```

---

# 29. Fractal生命周期

```text
RAW
 ↓
CANDIDATE
 ↓
CONFIRMED
 ↓
 ├── CURRENT
 │
 ├── SUPERSEDED
 │
 ├── MIDDLE
 │
 └── TRADE_ENDPOINT
```

---

# 30. FractalEngine State

```python
@dataclass
class FractalEngineState:

    confirmed_fractals: list[Fractal]

    current_top: Fractal | None
    current_bottom: Fractal | None

    last_valid_fractal: Fractal | None

    pending_candidate: FractalCandidate | None

    pending_same_type_candidate: FractalCandidate | None
```

---

# 31. FractalEngine输入

只允许：

```text
StandardBar CONFIRMED / stable
```

或者：

```text
当前实时StandardBar更新事件
```

但必须区分：

```text
preview
```

与：

```text
commit
```

---

# 32. Preview模式

Agent盯盘时需要知道：

```text
当前是否正在形成顶/底？
```

所以允许：

```text
preview_fractal
```

但：

```text
preview != confirmed
```

preview：

```text
只能用于观察
```

不能：

```text
直接产生交易信号
```

---

# 33. Commit模式

只有：

```text
FractalConfirmedEvent
```

产生后：

```text
结构层
```

才可以使用。

---

# 34. FractalEvent

```python
@dataclass
class FractalEvent:

    event_type: EventType

    fractal_id: str

    fractal_type: FractalType

    center_bar_id: str

    confirmation_time: int

    price: float

    role: FractalRole
```

---

# 35. 一个极重要的时间原则