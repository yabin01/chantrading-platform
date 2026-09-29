# ChanLun 1M Trading Agent 技术规格 v1.1

## 分型 → 笔：确定性数学 / 状态机规格

> 版本：v1.1\
> 状态：可编码规格 / 待人工图例验收\
> 上级：v1.0\
> 操作级别：1分钟

------------------------------------------------------------------------

## 1. v1.1目标与边界

本版本只解决：

``` text
1分钟Raw K线
→ 包含关系处理
→ 标准K线
→ 顶/底分型
→ 分型确认
→ 中继/替代分型
→ 有效笔端点
→ 笔
→ 笔的四种当下状态
```

暂不处理：

-   线段
-   特征序列
-   中枢
-   Ai
-   同级别分解
-   盘整背驰
-   BUY / SELL
-   MACD交易判断

原因很简单：

> 如果"分型→笔"错误，后面的线段、中枢、Ai以及交易信号都会建立在错误结构上。

------------------------------------------------------------------------

# 2. 原典定义与本项目编码

第62课给出分型、笔的基本定义：顶分型/底分型建立在三K结构上；两个相邻的顶和底之间构成一笔；顶底之间至少需要一根K线。相关整理也强调共用K线不能直接形成一笔。citeturn0search4turn0search11

第79课继续讨论分型辅助操作以及笔、线段之间的精确关系。citeturn0search0turn0search1

后续关于"笔定理"的原文整理把当下笔状态写成：

``` text
(1,1)
(-1,1)
(1,0)
(-1,0)
```

并明确给出了允许的状态转换。citeturn0search5turn0search6

为了程序二进制化，本项目固定映射：

``` text
第一位 direction：
0 = DOWN
1 = UP

第二位 phase：
0 = FRACTAL_BUILDING
1 = EXTENDING_AFTER_CONFIRMATION
```

所以：

  项目状态   原始写法   含义
  ---------- ---------- ------------------------
  `(0,0)`    `(-1,0)`   向下笔，底分型正在构造
  `(0,1)`    `(-1,1)`   向下笔，确认后继续延伸
  `(1,0)`    `(1,0)`    向上笔，顶分型正在构造
  `(1,1)`    `(1,1)`    向上笔，确认后继续延伸

这个映射以后不得修改。

------------------------------------------------------------------------

# 3. 核心原则：分型 ≠ 笔

错误：

``` text
Top
 ↓
Bottom
 ↓
Bi
```

正确：

``` text
K线
 ↓
候选分型
 ↓
确认分型
 ↓
分型结合关系
 ↓
中继分型处理
 ↓
有效端点
 ↓
笔候选
 ↓
笔确认
```

特别是：

``` text
Top → Bottom
```

不代表一定成笔。

------------------------------------------------------------------------

# 4. 数据对象

## 4.1 RawCandle

``` python
class RawCandle:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
```

原始K线永久保存。

## 4.2 ProcessedCandle

``` python
class ProcessedCandle:
    index: int
    start_timestamp: int
    end_timestamp: int
    open: float
    high: float
    low: float
    close: float
    source_raw_ids: list[int]
```

`ProcessedCandle`可能由多根RawCandle合并而来，因此必须保留：

``` text
processed_index
+
source_raw_ids
```

后续交易执行仍然要定位真实交易所K线。

------------------------------------------------------------------------

# 5. 包含关系

分型判断之前先处理包含。

### 向上

``` text
H = max(H1,H2)
L = max(L1,L2)
```

即：

``` text
高点取高
低点取高
```

### 向下

``` text
H = min(H1,H2)
L = min(L1,L2)
```

即：

``` text
高点取低
低点取低
```

必须：

``` text
left → right
```

顺序处理，不能把整个历史一次性静态压缩。

------------------------------------------------------------------------

# 6. 顶分型数学定义

对三个连续ProcessedCandle：

``` text
K[i-1], K[i], K[i+1]
```

若：

``` text
H[i] > H[i-1]
H[i] > H[i+1]

L[i] > L[i-1]
L[i] > L[i+1]
```

则：

``` text
TOP FRACTAL
```

对象：

``` python
TopFractal(
    center_index=i,
    top=H[i],
    bottom=L[i],
    confirm_index=i+1
)
```

------------------------------------------------------------------------

# 7. 底分型数学定义

若：

``` text
L[i] < L[i-1]
L[i] < L[i+1]

H[i] < H[i-1]
H[i] < H[i+1]
```

则：

``` text
BOTTOM FRACTAL
```

对象：

``` python
BottomFractal(
    center_index=i,
    top=H[i],
    bottom=L[i],
    confirm_index=i+1
)
```

------------------------------------------------------------------------

# 8. 分型确认时点

这是防止未来函数的第一道闸门。

当只有：

``` text
K[i-1], K[i]
```

时：

``` text
K[i]
```

不能被确认成分型。

只有：

``` text
K[i+1] 完成
```

才能确认：

``` text
K[i]
```

因此：

``` text
fractal.center_index = i
fractal.confirm_index = i+1
```

程序的"当下时间"永远以 `confirm_index` 为准。

------------------------------------------------------------------------

# 9. Fractal生命周期

``` python
FractalStatus:
    CANDIDATE
    CONFIRMED
    INVALIDATED
    RELAY
    SUPERSEDED
```

对象：

``` python
class Fractal:
    id
    type                 # TOP / BOTTOM
    center_index
    confirm_index
    top
    bottom
    source_processed_ids
    status
```

------------------------------------------------------------------------

# 10. 分型不能简单使用最近两个极值

例如：

``` text
Top1
Bottom
Top2
```

如果：

``` text
Top1 → Bottom
```

本身不满足有效成笔条件，不能机械产生一笔后再产生第二笔。

如果之后：

``` text
Top2 > Top1
```

Top1可能成为中继分型，最终有效向上笔可能从：

``` text
Bottom → Top2
```

形成。

因此：

> **分型是笔的原材料，不是笔端点的简单列表。**

------------------------------------------------------------------------

# 11. 最小成笔条件

假设：

``` text
F1 = Top
F2 = Bottom
```

或者：

``` text
F1 = Bottom
F2 = Top
```

必须：

### 条件1：方向不同

``` text
F1.type != F2.type
```

### 条件2：顶底之间至少有一根独立K线

使用ProcessedCandle索引：

``` python
abs(F2.center_index - F1.center_index) >= 2
```

否则：

``` text
NOT_VALID_BI
```

注意：

> 这是必要条件，不是所有复杂情况下的充分条件。

------------------------------------------------------------------------

# 12. 不能成笔的典型情况

例如：

``` text
Processed K10 = Top
Processed K11 = Bottom
```

则：

``` text
11 - 10 = 1
```

两分型中心相邻，没有独立K线。

所以：

``` text
Top → Bottom
```

不能直接形成有效笔。

这与第62课关于顶底之间至少需要一根K线、共用K线不能直接成笔的要求一致。citeturn0search4turn0search11

------------------------------------------------------------------------

# 13. 有效分型序列

有效端点必须遵守：

``` text
TOP → BOTTOM → TOP → BOTTOM
```

或者：

``` text
BOTTOM → TOP → BOTTOM → TOP
```

不能：

``` text
TOP → TOP
```

直接成笔。

但是同方向分型之间可以存在：

``` text
RELAY / SUPERSEDED
```

因此：

> "分型历史序列"和"有效笔端点序列"必须分开。

------------------------------------------------------------------------

# 14. 中继分型处理

例：

``` text
        Top2
         ▲
        /        /   Top1  /      ▲   /
 │  /
Bottom1
```

若：

``` text
Top2 > Top1
```

而中间结构不能形成独立有效笔，则：

``` text
Top1 = RELAY / SUPERSEDED
Top2 = 当前有效顶端候选
```

最终可能形成：

``` text
Bottom1 → Top2
```

中间：

``` text
Top1
```

属于内部/中继分型。

------------------------------------------------------------------------

# 15. 同方向分型不能简单删除历史

例如：

``` text
Top1
Top2
```

不能写成：

``` python
delete(Top1)
```

必须保留：

``` text
Top1.status = RELAY / SUPERSEDED
```

因为：

-   回放需要知道历史结构
-   后续线段需要完整笔历史
-   审计需要知道为什么Top1没有成为端点

------------------------------------------------------------------------

# 16. 笔对象

``` python
class Bi:

    id: int

    direction: str       # UP / DOWN

    start_fractal_id: int
    end_fractal_id: int

    start_index: int
    end_index: int

    high: float
    low: float

    status:
        CANDIDATE
        CONFIRMED
        EXTENDING
        BROKEN

    relay_fractals: list[int]
```

------------------------------------------------------------------------

# 17. 笔方向

``` text
Bottom → Top
    = UP

Top → Bottom
    = DOWN
```

------------------------------------------------------------------------

# 18. 笔的四态状态机

固定为：

``` text
(0,0) = DOWN + FRACTAL_BUILDING
(0,1) = DOWN + EXTENDING
(1,0) = UP   + FRACTAL_BUILDING
(1,1) = UP   + EXTENDING
```

第二位不是"有没有分型"。

它表示：

``` text
0 = 正在构造该方向笔终点对应的反向分型
1 = 该方向笔已经确认后继续延伸
```

因此：

``` text
(1,0)
```

表示：

> 当前市场仍处于向上运行背景，但正在构造顶分型。

而：

``` text
(0,0)
```

表示：

> 当前市场仍处于向下运行背景，但正在构造底分型。

------------------------------------------------------------------------

# 19. 四态转换

原始四态的允许转换关系明确指出：

``` text
(1,1) → (1,0)

(1,0) → (1,1)
(1,0) → (0,1)

(0,1) → (0,0)

(0,0) → (0,1)
(0,0) → (1,1)
```

citeturn0search5turn0search6

程序转移表：

  当前      下一状态   条件
  --------- ---------- ------------------------------
  `(1,1)`   `(1,0)`    开始构造顶分型
  `(1,0)`   `(1,1)`    顶分型构造失败，继续向上延伸
  `(1,0)`   `(0,1)`    顶分型确认，向下笔开始
  `(0,1)`   `(0,0)`    开始构造底分型
  `(0,0)`   `(0,1)`    底分型构造失败，继续向下延伸
  `(0,0)`   `(1,1)`    底分型确认，向上笔开始

禁止：

``` text
(1,1) → (0,1)
(1,1) → (0,0)

(0,1) → (1,1)
(0,1) → (1,0)
```

------------------------------------------------------------------------

# 20. 状态机的核心意义

不能把：

``` text
(1,1)
```

理解为：

> "已经确认向上笔，所以只等下一笔。"

它的真实意义是：

> **当前当下落在一个已经确认、正在延伸的向上笔中。**

同理：

``` text
(1,0)
```

意味着：

> **当前已经进入顶分型构造过程，但顶分型还没有确认。**

所以四态是一个**当下市场状态描述器**，不是简单的历史笔标签。

------------------------------------------------------------------------

# 21. 实时状态演化示例

假设：

``` text
Bottom confirmed
```

当前：

``` text
(1,1)
```

价格继续上涨：

``` text
(1,1)
```

开始形成顶分型：

``` text
(1,0)
```

如果下一步顶分型失败：

``` text
(1,1)
```

如果顶分型确认：

``` text
(0,1)
```

之后：

``` text
(0,0)
```

表示正在构造底分型。

如果底分型失败：

``` text
(0,1)
```

如果底分型确认：

``` text
(1,1)
```

形成新的向上笔。

------------------------------------------------------------------------

# 22. 候选分型必须允许失效

例如：

``` text
K1
K2  ← 暂时可能是Top
K3
```

之后：

``` text
K4 = 创新高
```

如果K2的顶分型条件因此不再成立：

``` text
K2 Top = INVALIDATED
```

不能保留为：

``` text
CONFIRMED
```

更不能让它提前生成向下笔。

------------------------------------------------------------------------

# 23. 分型确认与笔确认的时间差

这是程序实现最容易犯错的地方。

``` text
t0:
候选Top

t1:
Top确认

t1:
可以产生向下笔候选

t2+:
继续检查结构
```

因此：

``` text
Fractal confirmation
```

和：

``` text
Bi confirmation
```

不是一个概念。

代码中必须使用两个事件：

``` text
FRACTAL_CONFIRMED
BI_CONFIRMED
```

------------------------------------------------------------------------

# 24. 结构事件

``` python
class StructureEvent:

    timestamp: int

    type:
        FRACTAL_CANDIDATE
        FRACTAL_CONFIRMED
        FRACTAL_INVALIDATED
        FRACTAL_RELAY
        FRACTAL_SUPERSEDED

        BI_CANDIDATE
        BI_CONFIRMED
        BI_EXTENDED
        BI_BROKEN

    fractal_id: int | None
    bi_id: int | None

    direction: int | None
    processed_index: int
```

------------------------------------------------------------------------

# 25. FractalEngine接口

``` python
class FractalEngine:

    def update(
        self,
        candle: RawCandle
    ) -> list[StructureEvent]:
        ...

    def confirmed_fractals(self):
        ...

    def active_candidate(self):
        ...
```

每根1分钟K线结束时调用一次。

------------------------------------------------------------------------

# 26. BiEngine接口

``` python
class BiEngine:

    def update(
        self,
        fractal_events
    ) -> list[StructureEvent]:
        ...

    def confirmed_bis(self):
        ...

    def current_state(self):
        ...
```

------------------------------------------------------------------------

# 27. 四态状态机接口

``` python
class BiStateMachine:

    state: tuple[int, int]

    def transition(
        self,
        event
    ) -> tuple[int, int]:
        ...
```

如果非法：

``` python
raise InvalidStateTransition
```

禁止静默修正。

------------------------------------------------------------------------

# 28. 完整实时流程

``` python
for raw_candle in stream:

    processed_events = (
        include_engine.update(raw_candle)
    )

    fractal_events = (
        fractal_engine.update(processed_events)
    )

    bi_events = (
        bi_engine.update(fractal_events)
    )

    current_bi_state = (
        bi_state_machine.transition(bi_events)
    )

    log(
        raw_candle,
        processed_events,
        fractal_events,
        bi_events,
        current_bi_state
    )
```

------------------------------------------------------------------------

# 29. 严格的未来函数防护

在时间：

``` text
t
```

允许使用：

``` text
K[0] ... K[t]
```

禁止：

``` text
K[t+1] ...
```

特别是：
