# ChanLun 1M Trading Agent 技术规格 v1.8

## Python Core Data Model & State Machine Specification

> 版本：v1.8  
> 固定操作级别：1分钟  
> 上级版本：v1.7  
> 本版本性质：工程核心层规格  
> 目标：把缠论结构对象、状态机、事件系统、时间边界和全局State定义成可以直接进入Python实现的标准。

---

# 1. v1.8核心目标

v1.7已经确定系统总体架构：

```text
K线
→ 包含关系
→ 分型
→ 笔
→ 线段
→ 中枢
→ 1分钟走势Ai
→ 同级别分解
→ 盘整背驰
→ 交易分型
→ BUY / SELL / HOLD
→ 风险
→ Hummingbot
```

v1.8进一步解决：

```text
每一种对象到底是什么？
对象什么时候产生？
什么时候只是候选？
什么时候正式确认？
什么时候被替代？
什么时候终结？
什么时候因为扩张被拆分？
```

核心原则：

> **任何结构对象都必须拥有明确的生命周期。**

---

# 2. 最重要的工程原则：Confirmed才是事实

系统中必须严格区分：

```text
Candidate
Forming
Confirmed
```

其中：

```text
Candidate = 当前数据支持的候选结构
Forming    = 已进入结构形成过程
Confirmed  = 按规则已经完成确认
```

只有：

```text
Confirmed
```

才能：

```text
进入下一级结构
参与正式同级别比较
产生交易依据
```

---

# 3. Future Leak原则

任何时刻：

```text
t
```

系统只能读取：

```text
timestamp <= t
```

的数据。

禁止：

```text
读取t之后的K线
读取未来分型
读取未来线段
读取未来中枢
读取未来Ai
```

因此：

```text
结构确认时间
=
系统第一次拥有足够信息确认结构的时间
```

而不是：

```text
结构的几何中心时间
```

---

# 4. 时间双坐标

每个结构必须至少保存两个时间概念：

```text
structure_start_time
confirmation_time
```

例如：

```text
顶分型发生在：

10:01

但10:03才确认。

那么：

structure_time = 10:01
confirmation_time = 10:03
```

交易系统只能：

```text
10:03之后
```

使用这个分型作为已确认结构。

---

# 5. BaseStructure

所有结构对象继承：

```python
@dataclass
class BaseStructure:

    id: str

    state: StructureState

    start_index: int
    end_index: int

    start_time: int
    end_time: int

    detected_at: int | None
    confirmed_at: int | None

    version: int

    parent_id: str | None

    source_ids: list[str]

    metadata: dict
```

---

# 6. StructureState

```python
class StructureState(Enum):

    UNKNOWN = "UNKNOWN"

    CANDIDATE = "CANDIDATE"

    FORMING = "FORMING"

    CONFIRMED = "CONFIRMED"

    SUPERSEDED = "SUPERSEDED"

    EXTENDING = "EXTENDING"

    TERMINATED = "TERMINATED"

    INVALIDATED = "INVALIDATED"

    SPLIT = "SPLIT"
```

注意：

```text
SUPERSEDED
```

与：

```text
INVALIDATED
```

必须区分。

---

# 7. SUPERSEDED

表示：

```text
原候选结构曾经合理
但出现了更强的结构
所以原结构不再作为当前端点。
```

典型：

```text
顶分型
↓
底分型
↓
中间没有独立K线
↓
后面出现更高顶分型
```

原先候选顶分型：

```text
SUPERSEDED
```

不是：

```text
INVALIDATED
```

---

# 8. INVALIDATED

表示：

```text
该结构原本作为候选
但新的市场信息直接否定了其成立条件。
```

例如：

```text
Candidate Segment
```

后来出现破坏条件：

```text
INVALIDATED
```

---

# 9. CONFIRMED不可回写

一旦：

```text
state == CONFIRMED
```

原则上：

```text
structure immutable
```

后续不能修改：

```text
start
end
high
low
direction
parent
```

只能产生：

```text
新的结构
```

这是整个回测可审计性的基础。

---

# 10. Fractal对象

```python
@dataclass
class Fractal(BaseStructure):

    fractal_type: FractalType

    center_bar_index: int

    high: float
    low: float

    left_high: float
    left_low: float

    center_high: float
    center_low: float

    right_high: float
    right_low: float

    ema_relation: str | None

    is_trade_valid: bool
```

---

# 11. FractalType

```python
class FractalType(Enum):

    TOP = "TOP"
    BOTTOM = "BOTTOM"
```

---

# 12. 分型确认原则

系统必须区分：

```text
Fractal Candidate
```

与：

```text
Fractal Confirmed
```

例如：

```text
K0 K1 K2
```

只能形成：

```text
candidate
```

当右侧必要K线已经出现并满足规则：

```text
confirmed
```

---

# 13. 分型不能直接成为笔

正确：

```text
Fractal CONFIRMED
↓
进入BiEngine
↓
判断是否可以与前一个有效分型构成笔
```

所以：

```text
Fractal ≠ Bi
```

---

# 14. 中继分型

系统必须允许：

```text
Fractal
```

最终被标记为：

```text
is_trade_valid = false
```

例如：

```text
顶
底
顶
```

其中前两个分型最终被后面的更强顶包含进同一笔：

```text
中继结构
```

这些分型不能直接产生交易信号。

---

# 15. Bi对象

```python
@dataclass
class Bi(BaseStructure):

    direction: Direction

    start_fractal_id: str
    end_fractal_id: str

    start_price: float
    end_price: float

    high: float
    low: float

    bar_count: int

    is_valid: bool
```

---

# 16. Direction

```python
class Direction(Enum):

    UP = "UP"
    DOWN = "DOWN"
```

---

# 17. 笔的生命周期

```text
FRACTAL CONFIRMED
        ↓
BI CANDIDATE
        ↓
条件持续满足
        ↓
BI CONFIRMED
```

如果后面出现更强端点：

```text
BI CANDIDATE
        ↓
SUPERSEDED
```

---

# 18. 笔必须引用分型ID

不能：

```python
Bi(
    start_price=...
    end_price=...
)
```

而应该：

```python
Bi(
    start_fractal_id="F0012",
    end_fractal_id="F0015"
)
```

这样整个结构可以反向追踪。

---

# 19. Segment对象

```python
@dataclass
class Segment(BaseStructure):

    direction: Direction

    bi_ids: list[str]

    start_bi_id: str
    end_bi_id: str

    high: float
    low: float

    feature_sequence: list[str]

    break_condition: str | None
```

---

# 20. 线段不能简单用“3笔”定义

系统只允许：

```text
至少3笔
+
满足缠论线段划分条件
```

才能确认。

因此：

```python
len(bi_ids) >= 3
```

只是：

```text
必要条件之一
```

不是充分条件。

---

# 21. Segment Candidate

当：

```text
3笔以上
```

出现以后：

```text
Segment Candidate
```

然后继续等待：

```text
特征序列
+
线段终结条件
```

确认。

---

# 22. Center对象

```python
@dataclass
class Center(BaseStructure):

    segment_ids: list[str]

    zg: float
    zd: float

    gg: float
    dd: float

    extension_count: int

    state_detail: str
```

---

# 23. 中枢最小结构

工程上：

```text
至少三个连续同级别线段
```

并存在共同重叠区间：

```text
ZD < ZG
```

才确认中枢。

其中：

```text
ZG = min(各相关线段高点)
ZD = max(各相关线段低点)
```

注意：

```text
3线段 ≠ 自动中枢
```

---

# 24. 中枢延伸

如果后续同级别线段继续满足原中枢的延伸条件：

```text
CENTER_EXTENDED
```

更新：

```text
extension_count += 1
```

但：

```text
center.id
```

保持不变。

---

# 25. 中枢扩张

扩张必须生成：

```text
CENTER_EXPANDED
```

事件。

之后：

```text
SameLevelEngine
```

负责决定：

```text
旧Ai
+
新Ai
```

的分解边界。

---

# 26. Ai对象

```python
@dataclass
class Ai(BaseStructure):

    direction: Direction

    entry_segment_ids: list[str]

    center_id: str

    exit_segment_ids: list[str]

    start_price: float
    end_price: float

    center_zg: float
    center_zd: float

    completed: bool

    split_from_ai_id: str | None
```

---

# 27. Ai最小结构

理论模板：

```text
进入段
+
中枢
+
离开段
```

工程最小模板：

```text
S0
S1
S2
S3
S4
```

其中：

```text
S1/S2/S3
```

形成中枢。

但程序不得简单写：

```python
if len(segments) == 5:
    Ai = True
```

必须经过：

```text
中枢确认
+
进入段确认
+
离开段确认
```

---

# 28. Ai完成条件

```python
def is_complete(self):
    return (
        self.center_confirmed
        and self.exit_confirmed
        and self.direction_confirmed
    )
```

---

# 29. Ai扩张

如果一个尚未结束的1分钟走势发生级别扩张：

```text
不升级到5分钟
```

而是：

```text
A0
 ↓
Expansion
 ↓
A0 + A1
```

因此：

```python
old_ai.state = SPLIT
```

产生：

```python
new_ai.split_from_ai_id = old_ai.id
```

---

# 30. AiSplit事件

```python
@dataclass
class AiSplitEvent:

    event_id: str

    old_ai_id: str

    new_ai_ids: list[str]

    split_segment_id: str

    split_index: int

    split_time: int

    reason: str
```

---

# 31. AiSeries

```python
@dataclass
class AiSeries:

    confirmed: list[Ai]

    current: Ai | None

    last_split_event: AiSplitEvent | None
```

---

# 32. 同级别分解永远锁定1分钟

配置：

```yaml
timeframe: 1m
allow_level_upgrade: false
```

所以：

```text
1分钟走势扩张
```

不产生：

```text
5分钟走势
```

而产生：

```text
A0
A1
```

---

# 33. SameLevelState

```python
@dataclass
class SameLevelState:

    ai_series: AiSeries

    current_comparison_left: str | None
    current_comparison_right: str | None

    comparison_allowed: bool

    comparison_reason: str

    continuation_required: bool

    pending_exit_check: bool
```

---

# 34. ComparisonPermission

```python
@dataclass
class ComparisonPermission:

    allowed: bool

    left_ai_id: str | None
    right_ai_id: str | None

    reason: str

    rule_id: str
```

---

# 35. 为什么需要ComparisonPermission

不能简单：

```python
if len(AiSeries) >= 3:
    compare(Ai[-1], Ai[-3])
```

因为第39课的递推关系具有条件。

必须：

```text
结构条件
+
前一个Ai的状态
+
突破/不突破关系
+
当前递推阶段
```

共同决定：

```text
是否允许比较
```

---

# 36. MACDArea对象

```python
@dataclass
class MACDArea:

    ai_id: str

    start_index: int
    end_index: int

    positive_area: float
    negative_area: float

    total_abs_area: float

    max_hist: float
    min_hist: float
```

---

# 37. MACD面积计算原则

对于向上Ai：
