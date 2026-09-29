# ChanLun 1M Trading Agent 技术规格 v1.5

## 分型 → 笔 → 有效转折分型 → 交易触发状态机

> 版本：v1.5  
> 上级：v1.4  
> 固定级别：1分钟  
> 本版本目标：把“盘整背驰已经成立”进一步连接到“究竟是哪一个1分钟K线上的哪个顶/底分型可以真正触发交易”。

---

# 1. v1.5为什么是关键版本

v1.4已经解决：

```text
A0
A1
A2
...
An
      ↓
Ai 与 Ai+2
      ↓
价格 + MACD力度
      ↓
盘整背驰
      ↓
BUY / SELL候选
```

但是这里还有一个最重要的问题：

> **盘整背驰成立，并不等于可以随便选择一个最近的顶/底分型下单。**

因为缠论的最底层结构不是：

```text
分型 → 直接交易
```

而是：

```text
K线
 ↓
包含关系处理
 ↓
分型
 ↓
笔
 ↓
线段
 ↓
中枢
 ↓
走势
```

第62课首先给出了顶分型、底分型的基本定义；第65课进一步明确线段至少由三笔构成，并强调前三笔必须存在重叠部分；第67课以后则通过特征序列把线段划分进一步严格化。citeturn0search5turn1search7turn1search9

因此：

```text
v1.5
=
把“候选分型”
变成“有效交易转折点”
```

---

# 2. v1.5最重要的原则

## 原则一：分型不是笔

出现：

```text
顶分型
```

只意味着：

```text
出现了一个候选顶部结构
```

并不自动意味着：

```text
一笔向下已经成立
```

同样：

```text
底分型
```

也不自动意味着：

```text
一笔向上已经成立
```

---

# 3. 原始笔的几何要求

按照缠论的基础定义：

```text
向上笔：

底分型
 +
至少一个独立K线间隔
 +
顶分型
```

向下笔：

```text
顶分型
 +
至少一个独立K线间隔
 +
底分型
```

因此：

```text
顶分型
↓
立刻底分型
```

如果两者之间没有满足笔的独立K线/结构要求：

```text
不能直接宣布：
DOWN_BI
```

这正是本Agent必须重点避免的错误。

---

# 4. 为什么“顶→底”不能机械连笔

错误算法：

```python
if fractal.type != previous_fractal.type:
    create_bi()
```

这种代码会产生大量错误笔。

正确逻辑：

```text
相邻异类分型
       ↓
检查笔成立条件
       ↓
满足
 ┌─────┴─────┐
 ↓           ↓
YES          NO
 ↓           ↓
成笔        等待
```

因此：

```text
FractalCandidate
```

和：

```text
ConfirmedBi
```

必须是两个完全不同的对象。

---

# 5. v1.5分型状态

每一个分型采用：

```python
class FractalState:

    CANDIDATE
    CONFIRMED
    MERGED
    INVALIDATED
    MIDDLE
    USED_BY_BI
```

说明：

### CANDIDATE

当前结构可能形成分型。

### CONFIRMED

已经满足当下可确认条件。

### MERGED

因为包含/同类分型处理，被另一个更极端分型替代。

### INVALIDATED

后续走势破坏原来的候选结构。

### MIDDLE

该分型存在，但被识别为：

```text
中继分型
```

不承担当前交易转折职责。

### USED_BY_BI

已经成为某一笔的端点。

---

# 6. 为什么必须保留“中继分型”

这是本项目最容易犯错的地方之一。

典型结构：

```text
底分型 B0
   ↓
顶分型 T1
   ↓
底分型 B1
   ↓
顶分型 T2
```

如果：

```text
T2 > T1
```

而：

```text
B1
```

没有形成独立的有效笔端点关系，

那么不能简单：

```text
B0 → T1
T1 → B1
B1 → T2
```

机械产生三笔。

实际结构可能是：

```text
B0
 ↓
     T1
      ↓
     B1
      ↓
     T2
```

其中：

```text
T1
B1
```

最终成为：

```text
中继结构
```

而：

```text
B0 → T2
```

才构成最终有效向上笔。

---

# 7. “中继分型”不能理解为“假分型”

必须区分：

```text
有效分型
```

与：

```text
交易转折分型
```

一个分型可以：

```text
在几何上真实存在
```

但最终：

```text
没有成为笔的端点
```

这种分型：

```text
MIDDLE
```

而不是：

```text
INVALID
```

这是非常重要的设计。

---

# 8. v1.5对象模型

```python
class Fractal:

    id

    type:
        TOP
        BOTTOM

    index

    high
    low

    state

    strength

    ema_context

    source_bars

    predecessor_id

    successor_id

    used_by_bi_id
```

---

# 9. Bi对象

```python
class Bi:

    id

    direction:
        UP
        DOWN

    start_fractal_id
    end_fractal_id

    start_index
    end_index

    start_price
    end_price

    bars_count

    confirmed

    state
```

状态：

```text
CANDIDATE
CONFIRMED
EXTENDED
INVALIDATED
```

---

# 10. 笔不能在未来信息出现前被提前锁死

Agent运行在：

```text
t
```

时，只能使用：

```text
K0...Kt
```

不能使用：

```text
Kt+1
Kt+2
...
```

因此：

```text
笔的当下状态
```

允许：

```text
CANDIDATE
```

但只有达到定义要求以后：

```text
CONFIRMED
```

---

# 11. 这是“当下性”最重要的地方

例如：

```text
K100
形成顶分型
```

Agent不能因为：

```text
“看起来这里很像顶部”
```

就立即认为：

```text
DOWN_BI
```

必须：

```text
顶分型确认
 ↓
等待底方向结构
 ↓
验证笔成立条件
 ↓
确认向下笔
```

所以：

```text
Agent不能预测笔
```

只能：

```text
确认笔
```

---

# 12. 顶分型确认

基本结构：

```text
K(i-2)
K(i-1)
K(i)
K(i+1)
K(i+2)
```

当中心K线满足：

```text
High(i) >= High(i-1)
High(i) >= High(i+1)
Low(i) >= Low(i-1)
Low(i) >= Low(i+1)
```

在包含关系已经处理的前提下：

```text
K(i)
```

形成：

```text
TOP_FRACTAL
```

具体边界和包含处理必须由v1.1的分型引擎统一执行，不允许v1.5另写一套分型定义。

---

# 13. 底分型

同理：

```text
Low(i) <= Low(i-1)
Low(i) <= Low(i+1)
High(i) <= High(i-1)
High(i) <= High(i+1)
```

则：

```text
BOTTOM_FRACTAL
```

---

# 14. EMA5/10在分型层的位置

EMA5/10：

```text
不能创造分型
```

只能：

```text
辅助判断分型质量
```

例如：

```text
价格形成顶分型
+
EMA5/10结构支持
```

可以：

```text
提高FractalScore
```

但不能：

```text
没有顶分型
+
EMA死叉
=
顶分型
```

这是禁止的。

---

# 15. FractalScore

预留：

```python
class FractalScore:

    geometry_score

    ema_score

    separation_score

    macd_context_score
```

但是：

```text
geometry_score
```

必须拥有绝对优先级。

最终：

```text
if geometry_invalid:
    fractal_invalid
```

无论：

```text
EMA
MACD
```

多么漂亮，都不能补救。

---

# 16. 同类分型的后继处理

例如连续出现：

```text
TOP1
TOP2
```

不能产生：

```text
TOP1 → TOP2
```

的一笔。

因为笔必须：

```text
TOP ↔ BOTTOM
```

交替。

因此需要：

```text
SAME_TYPE_REPLACEMENT
```

机制。

---

# 17. 顶分型替换

如果：

```text
TOP1
```

之后出现：

```text
TOP2
```

且：

```text
TOP2.high > TOP1.high
```

则当前候选顶端应更新：

```text
active_top = TOP2
```

旧：

```text
TOP1
```

状态：

```text
MIDDLE
```

或：

```text
MERGED
```

具体取决于是否已经进入一笔/线段结构。

---

# 18. 底分型替换

对称：

```text
BOTTOM1
BOTTOM2
```

如果：

```text
BOTTOM2.low < BOTTOM1.low
```

则：

```text
active_bottom = BOTTOM2
```

旧：

```text
BOTTOM1
```

转为：

```text
MIDDLE
```

---

# 19. 最重要的结构状态

分型引擎必须维护：

```python
active_extreme_fractal
```

而不是：

```python
last_fractal
```

两者不是一个概念。

例如：

```text
TOP1
BOTTOM1
TOP2
```

此时：

```text
last_fractal = TOP2
```

但真正用于笔端点判断的：

```text
active_top
```

也必须是：

```text
TOP2
```

如果后面：

```text
TOP3 > TOP2
```

则：

```text
active_top = TOP3
```

---

# 20. CandidateBi

定义：

```python
class CandidateBi:

    direction

    start_fractal

    candidate_end_fractal

    minimum_structure_ok

    separation_ok

    extreme_relation_ok

    confirmed
```

例如：

```text
BOTTOM0
     ↓
TOP1
```

先产生：

```text
CandidateBi(UP)
```

然后继续验证：

```text
TOP1是否被更高TOP替换
```

如果：

```text
TOP2 > TOP1
```

则：

```text
CandidateBi
```

延伸：

```text
BOTTOM0 → TOP2
```

而：

```text
TOP1
```

进入：

```text
MIDDLE
```

---

# 21. 这正对应你提出的核心案例

例如：

```text
B0
 ↓
T1
 ↓
B1
 ↓
T2
```

且：

```text
T2 > T1
```

程序不能立即认定：

```text
B0 → T1
T1 → B1
B1 → T2
```

而必须继续判断：

```text
T1
B1
```

是否满足独立笔的必要条件。

如果不满足：

```text
T1 = MIDDLE
B1 = MIDDLE
```

最终：

```text
B0 → T2
```

形成：

```text
UP_BI
```

---

# 22. “没有独立K线”的特殊状态

定义：

```text
TOP
↓
BOTTOM
```

如果两个分型之间：

```text
没有满足笔成立所要求的独立K线结构
```

则：

```text
NO_BI
```

而不是：

```text
DOWN_BI
```

状态：

```python
BiState.WAITING_SEPARATION
```

---