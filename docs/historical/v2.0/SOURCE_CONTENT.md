# ChanLun 1M Trading Agent 技术规格 v2.0

## BiEngine：笔的动态状态机与数学规格

> 版本：v2.0  
> 固定周期：1分钟  
> 上级版本：v1.9  
> 本版本性质：核心结构引擎

---

## 1. 目标

v1.9完成：

```text
Raw K → 包含关系 → Standard K → Fractal Candidate → Fractal Confirmed
```

v2.0继续：

```text
Confirmed Fractal
→ Bi Candidate
→ Bi State
→ Bi Extension
→ Bi Termination
→ Bi Confirmed
```

核心目标是把“分型→笔”做成严格的、逐K、可回放、无未来函数的状态机。

---

## 2. 四种笔的当下状态

原典严格使用两个变量：

```text
第一变量：
  1  = 向上笔
 -1  = 向下笔

第二变量：
  0  = 分型构造中
  1  = 分型确认后延伸中
```

因此四种状态是：

```text
(1,1)
(1,0)
(-1,1)
(-1,0)
```

而不是把两个变量都编码成0/1。

第91课对这一“笔定理”及四状态有明确说明。citeturn0search4turn0search7

程序内部：

```python
class BiDirection(Enum):
    UP = 1
    DOWN = -1

class BiPhase(Enum):
    BUILDING = 0
    EXTENDING = 1

@dataclass(frozen=True)
class BiState:
    direction: BiDirection
    phase: BiPhase
```

---

## 3. 四状态含义

### (1,1)

```text
向上笔
+
分型已经确认
+
当前仍在向上延伸
```

### (1,0)

```text
向上笔
+
正在构造顶分型
```

### (-1,1)

```text
向下笔
+
分型已经确认
+
当前仍在向下延伸
```

### (-1,0)

```text
向下笔
+
正在构造底分型
```

---

## 4. 合法状态转换

允许：

```text
(1,1) → (1,0)

(1,0) → (1,1)
(1,0) → (-1,1)

(-1,1) → (-1,0)

(-1,0) → (-1,1)
(-1,0) → (1,1)
```

禁止：

```text
(1,1) → (-1,1)
(1,1) → (-1,0)

(-1,1) → (1,1)
(-1,1) → (1,0)
```

原典明确强调四种状态不能任意连接。citeturn0search4turn0search7

---

## 5. 为什么(1,0)不是“已经完成向上笔”

```text
(1,0)
```

只表示：

```text
当前向上笔出现了顶分型构造
```

它仍可能：

```text
(1,0) → (1,1)
```

即顶分型构造被破坏，原向上笔继续延伸。

只有满足完整笔规则后，才：

```text
(1,0) → (-1,1)
```

---

## 6. Bi对象

```python
@dataclass
class Bi:

    id: str

    direction: BiDirection
    state: BiState

    start_fractal_id: str

    current_end_fractal_id: str | None
    confirmed_end_fractal_id: str | None

    start_price: float
    current_extreme_price: float
    end_price: float | None

    start_standard_index: int
    current_standard_index: int

    confirmed_at: int | None

    is_confirmed: bool
    is_extended: bool

    absorbed_fractal_ids: list[str]

    superseded_by: str | None
```

关键设计：

```text
current_end_fractal
≠
confirmed_end_fractal
```

因为实时笔端点可能继续演化。

---

## 7. 笔不是两个分型的静态连线

错误：

```text
Bi = FractalA + FractalB
```

正确：

```text
Bi =
    起点分型
    +
    实时演化
    +
    候选终点
    +
    成笔条件
    +
    确认终点
```

所以Bi必须是动态对象。

---

## 8. BiCandidate

```python
@dataclass
class BiCandidate:

    id: str

    direction: BiDirection

    start_fractal_id: str
    candidate_end_fractal_id: str | None

    start_price: float
    candidate_price: float | None

    min_standard_bars: int
    current_standard_index: int

    state: BiState
```

---

## 9. 成笔的两个层次

必须严格分开：

```text
A. 反向分型出现
B. 笔定义真正满足
```

因此：

```text
反向分型出现
≠
新笔立即Confirmed
```

这也是为什么BiEngine不能简单地：

```python
if opposite_fractal:
    close_bi()
```

---

## 10. 最小K线规则必须参数化

工程配置：

```yaml
bi:
  minimum_standard_bars: 5
  require_alternating_fractal: true
  allow_equal_extreme: false
  confirm_only_on_closed_bar: true
```

这里的`5`是项目工程参数，不应该散落硬编码在算法中。

原因是缠论资料在新笔的K线数量口径上存在传播差异；因此规则必须配置化，而不是把某个口径永久写死。

---

## 11. 起笔

向上：

```text
底分型
↓
向上延伸
```

状态：

```text
(-1,0) → (1,1)
```

向下：

```text
顶分型
↓
向下延伸
```

状态：

```text
(1,0) → (-1,1)
```

---

## 12. BiStartEvent

```python
@dataclass
class BiStartEvent:

    bi_id: str
    direction: BiDirection

    start_fractal_id: str
    start_price: float

    timestamp: int
```

---

## 13. 笔延伸

向上笔：

```text
不断创新高
```

保持：

```text
(1,1)
```

向下笔：

```text
不断创新低
```

保持：

```text
(-1,1)
```

这属于：

```text
BiExtension
```

不是：

```text
NewBi
```

---

## 14. BiExtensionEvent

```python
@dataclass
class BiExtensionEvent:

    bi_id: str

    old_extreme: float
    new_extreme: float

    new_candidate_fractal_id: str | None

    timestamp: int
```

---

## 15. 顶分型开始构造

当前：

```text
Bi = UP
```

出现顶分型候选：

```text
(1,1) → (1,0)
```

此时Agent只能知道：

```text
向上笔正在构造顶端
```

不能直接：

```text
SELL
```

---

## 16. 顶分型构造失败

如果后续走势使原顶分型候选失效：

```text
(1,0) → (1,1)
```

表示：

```text
原向上笔继续延伸
```

而不是产生一条新的向下笔。

底分型对应：

```text
(-1,0) → (-1,1)
```

---

## 17. 顶分型最终确认

当：

```text
顶分型确认
+
笔规则满足
```

则：

```text
旧向上笔终结
+
新向下笔开始
```

状态：

```text
(1,0) → (-1,1)
```

同理：

```text
(-1,0) → (1,1)
```

---

## 18. BiCloseEvent

```python
@dataclass
class BiCloseEvent:

    bi_id: str
    direction: BiDirection

    start_fractal_id: str
    end_fractal_id: str

    start_price: float
    end_price: float

    confirmation_time: int
    standard_bar_count: int
```

---

## 19. 一个反转的完整事件序列

```text
BAR_CLOSED
↓
FRACTAL_CANDIDATE
↓
FRACTAL_CONFIRMED
↓
BI_CLOSE
↓
BI_CREATED
↓
BI_STATE = (-1,1)
```

EventLog中：

```text
BI_CLOSE
```

与：

```text
BI_CREATED
```

必须是两个独立事件。

---

## 20. 中继分型

典型情况：

```text
TOP1
↓
BOTTOM1
↓
TOP2
```

但：

```text
TOP1 → BOTTOM1
```

不足以形成有效笔。

随后：

```text
TOP3 > TOP1
```

那么中间结构可能最终全部被吸收到一条更完整的笔内部。

因此Bi必须保存：

```python
absorbed_fractal_ids
```

例如：

```json
{
  "bi_id": "BI042",
  "start_fractal": "F100",
  "end_fractal": "F105",
  "absorbed_fractals": [
    "F101",
    "F102",
    "F103",
    "F104"
  ]
}
```

---

## 21. 中继分型的职责边界

v1.9：

```text
POSSIBLE_MIDDLE
```

只是候选角色。

v2.0：

```text
BiEngine确认它被吸收到某条已确认笔内部
```

之后才能：

```text
FractalRole.MIDDLE
```

因此：

```text
FractalEngine
```

负责识别分型。

```text
BiEngine
```

负责确定它是否最终成为笔端，或者被吸收为笔内部结构。

---

## 22. PendingBiStructure

```python
@dataclass
class PendingBiStructure:

    base_bi_id: str

    candidate_fractals: list[str]

    candidate_direction: BiDirection

    waiting_for_confirmation: bool

    minimum_requirement_met: bool
```

它解决：

> “现在看起来可能成笔，但当下还不能100%确定”的问题。

这就是缠论当下性的程序化实现。

---

## 23. Bi确认时间

必须严格保存：

```python
confirmed_at
```

例如：

```text
顶点实际发生：12:31
顶分型确认：12:33
```

那么：

```text
end_time = 12:31
confirmed_at = 12:33
```

交易系统只能在：

```text
12:33以后
```

认为这条笔已经完成。

---

## 24. Future Leak禁止项

禁止：

```python
future_min()
future_max()
future_fractal()
future_bi()
```

尤其禁止：

```text
未来10根K线最低点
```

反推：

```text
当前向下笔已经结束
```

---

## 25. EMA和MACD的职责

EMA5/EMA10：

```text
不参与Bi数学定义
```

MACD：

```text
不参与Bi数学定义
```

二者属于：

```text
Context / Momentum
```

而不是：

```text
Structure
```

所以：

```text
BiEngine
```

即使没有MACD和EMA，也必须能够独立产生完全相同的笔结构。

---

## 26. BiContext

```python
@dataclass
class BiContext:

    direction: BiDirection

    amplitude: float
    duration_bars: int

    ema5: float | None
    ema10: float | None

    macd_hist: float | None
```

---

## 27. BiEngine主接口

```python
class BiEngine:

    def on_bar(self, bar: StandardBar):
        ...

    def on_fractal_candidate(self, fractal):
        ...

    def on_fractal_confirmed(self, fractal):
        ...

    def get_current(self) -> Bi | None:
        ...

    def get_confirmed(self) -> list[Bi]:
        ...

    def snapshot(self):
        ...

    def events(self):
        ...
```

---

## 28. BiEngine状态机

```text
(1,1)
  |
  | 顶分型开始构造
  v
(1,0)
  |
  +---- 顶分型失效 ----> (1,1)
  |
  +---- 顶分型确认 ----> (-1,1)
```

向下：

```text
(-1,1)
  |
  | 底分型开始构造
  v
(-1,0)
  |
  +---- 底分型失效 ----> (-1,1)
  |
  +---- 底分型确认 ----> (1,1)
```

---

## 29. Transition函数

```python
ALLOWED_TRANSITIONS = {
    (UP, EXTENDING): {
        (UP, BUILDING),
    },

    (UP, BUILDING): {
        (UP, EXTENDING),
        (DOWN, EXTENDING),
    },

    (DOWN, EXTENDING): {
        (DOWN, BUILDING),
    },

    (DOWN, BUILDING): {
        (DOWN, EXTENDING),
        (UP, EXTENDING),
    },
}
```

任何其他转换：

```python
raise InvalidBiTransition
```

---

## 30. 不能把Candidate直接提交成Confirmed

正确：

```text
Candidate
↓
Rule Check
↓
Confirmation
↓
Confirmed
```

而不是：

```text
Candidate
↓
Bi
```

这样才能保证回测中的每一个结构都有证据链。

---

## 31. 结构引用链

每条确认笔必须能够完整反向追踪：

```text
Bi
↓
Start Fractal / End Fractal
↓
StandardBar
↓
RawBar
```

因此：

```text
任何一条笔
```

都可以追溯到：

```text
具体哪几根1分钟K线
```

---

## 32. 交易层关系

Bi状态本身不是交易信号。

例如：

```text
(1,0)
```

不能直接：

```text
SELL
```

它只表示：

```text
向上笔正在构造顶端。
```

真正交易：

```text
Bi
↓
Segment
↓
Center
↓
Ai
↓
SameLevel
↓
Divergence
↓
TradeFractal
↓
BUY/SELL
```

---

## 33. 最终交易分型

BUY最终必须落到：

```text
确认的、结构有效的底分型
```

SELL最终必须落到：

```text
确认的、结构有效的顶分型
```

并且：

```text
该分型已经通过BiEngine验证其结构角色。
```

---
