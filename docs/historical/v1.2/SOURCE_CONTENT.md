# ChanLun 1M Trading Agent 技术规格 v1.2

## 笔 → 线段：特征序列确定性划分 / 当下状态机

> 版本：v1.2\
> 状态：可编码规格 / 待人工案例验收\
> 上级：v1.1\
> 操作级别：1分钟\
> 本版本核心：把"笔"进一步确定性地划分为"线段"。

------------------------------------------------------------------------

# 1. v1.2目标

v1.1解决：

``` text
1分钟K线
→ 包含处理
→ 分型
→ 笔
→ 笔的当下状态
```

v1.2继续向上：

``` text
笔
→ 线段候选
→ 特征序列
→ 标准特征序列
→ 特征序列分型
→ 线段结束条件
→ 线段确认
→ 线段延伸
→ 当下线段状态
```

本版本不处理：

``` text
中枢
Ai
同级别分解
盘整背驰
MACD
EMA
买卖点
```

原因：

> v1.2的唯一任务，是让Agent能够在任何时刻，把已经确认的笔确定性地分解成线段，并知道当前线段究竟是在延伸，还是已经被破坏。

------------------------------------------------------------------------

# 2. 原典依据

第65课明确给出：

-   线段至少由三笔构成；
-   线段只有两种方向：从向上一笔开始，或者从向下一笔开始；
-   第65课给出了早期的"笔破坏"描述。citeturn0search10

第67课进一步把线段划分精确化，引入"特征序列"：

``` text
向上笔开始的线段：
S1 X1 S2 X2 S3 X3 ... Sn Xn

特征序列：
X1 X2 X3 ... Xn
```

向下笔开始则反过来。

第67课明确指出：特征序列相邻元素之间如果没有重合区间，就称为一个"缺口"；特征序列还必须进行包含关系的非包含处理，并在标准特征序列上寻找分型。citeturn0search0turn0search7

第71课进一步说明：特征序列的包含关系只能在同一个特征序列内部讨论，而且线段方向与其特征序列元素方向相反。citeturn0search6

第78课强调，在线段作为基本分析单位时，可以把线段标准化为"最低点到最高点"或"最高点到最低点"，从而使线段连接形成标准化折线。citeturn0search4

因此，本项目v1.2以第67课的特征序列标准作为**最终线段算法底层规范**，而不是简单使用"连续三笔"或高低点突破算法。

------------------------------------------------------------------------

# 3. 最重要的概念纠正

必须严格区分：

``` text
至少三笔
```

与：

``` text
线段划分算法
```

"至少三笔"只是线段的必要结构基础。

不能写成：

``` python
if len(bis) >= 3:
    segment = True
```

这是错误的。

正确流程：

``` text
笔
↓
假设一个线段起点
↓
建立该线段特征序列
↓
标准化特征序列
↓
寻找特征序列分型
↓
判断第一/第二元素之间是否存在缺口
↓
按第一种/第二种情况判断
↓
确定线段终点
```

------------------------------------------------------------------------

# 4. 线段对象

``` python
class Segment:

    id: int

    direction:
        UP
        DOWN

    start_bi_id: int
    end_bi_id: int | None

    start_index: int
    end_index: int | None

    high: float
    low: float

    status:
        CANDIDATE
        EXTENDING
        CONFIRMED
        INVALIDATED

    feature_sequence_ids: list[int]

    termination_reason:
        TYPE_1
        TYPE_2
        NONE
```

------------------------------------------------------------------------

# 5. 线段方向

## 5.1 向上线段

``` text
UP BI
DOWN BI
UP BI
DOWN BI
...
```

例如：

``` text
S1 X1 S2 X2 S3 X3
```

其中：

``` text
S = UP BI
X = DOWN BI
```

则：

``` text
Segment.direction = UP
FeatureSequence = [X1, X2, X3]
```

------------------------------------------------------------------------

## 5.2 向下线段

``` text
DOWN BI
UP BI
DOWN BI
UP BI
...
```

例如：

``` text
X1 S1 X2 S2 X3 S3
```

则：

``` text
Segment.direction = DOWN
FeatureSequence = [S1, S2, S3]
```

------------------------------------------------------------------------

# 6. 一个极其重要的规则

> **线段的特征序列方向，与线段自身方向相反。**

因此：

``` text
UP Segment
→ 使用 DOWN BIs 作为特征序列

DOWN Segment
→ 使用 UP BIs 作为特征序列
```

程序绝对不能写反。

------------------------------------------------------------------------

# 7. 为什么需要特征序列

假设：

``` text
UP Segment

S1 X1 S2 X2 S3 X3 S4 X4 ...
```

S1、S2、S3之间由于它们都是向上的笔，连续向上笔之间必然存在重合关系。

真正能够描述这条线段内部结构变化的是：

``` text
X1 X2 X3 X4 ...
```

因此：

``` text
FeatureSequence(UP Segment)
=
DOWN BIs
```

同理：

``` text
FeatureSequence(DOWN Segment)
=
UP BIs
```

这也是第67课引入特征序列的核心原因。citeturn0search0turn0search7

------------------------------------------------------------------------

# 8. FeatureElement

程序中不要直接把Bi对象当成不可变的FeatureElement。

建议：

``` python
class FeatureElement:

    id: int

    source_bi_id: int

    direction: str

    high: float
    low: float

    raw_high: float
    raw_low: float

    source_start_index: int
    source_end_index: int
```

原因：

> 特征序列需要独立进行包含关系处理。

------------------------------------------------------------------------

# 9. 特征序列的构建

假设当前正在寻找一个：

``` text
UP Segment
```

已经确定：

``` text
S1 X1 S2 X2 S3 X3
```

则：

``` text
FeatureSequence =
[
    X1,
    X2,
    X3
]
```

注意：

``` text
S1/S2/S3
```

是线段骨架中的同向笔，

而：

``` text
X1/X2/X3
```

才是特征序列元素。

------------------------------------------------------------------------

# 10. 特征序列的包含处理

特征序列内部需要再次做包含关系处理。

注意：

> 这是第二层包含处理。

第一层：

``` text
Raw K
→ Processed K
```

第二层：

``` text
FeatureElement
→ Standard FeatureElement
```

两者不能混淆。

------------------------------------------------------------------------

# 11. 特征序列包含处理

对连续FeatureElement：

``` text
F1
F2
```

如果：

``` text
F1.high >= F2.high
AND
F1.low <= F2.low
```

则：

``` text
F1 包含 F2
```

反之：

``` text
F2 包含 F1
```

处理方向按照当前特征序列的方向执行。

与K线包含处理一样：

``` text
UP方向：
高高取高
低低取高

DOWN方向：
高高取低
低低取低
```

------------------------------------------------------------------------

# 12. 为什么必须重新做包含

因为：

``` text
K线包含
```

解决的是：

``` text
K → Fractal → Bi
```

而：

``` text
FeatureElement包含
```

解决的是：

``` text
Bi → FeatureSequence → Segment
```

这是两个完全不同层级。

因此程序结构必须是：

``` text
IncludeEngine
        ↓
FractalEngine
        ↓
BiEngine
        ↓
FeatureSequenceEngine
        ↓
SegmentEngine
```

------------------------------------------------------------------------

# 13. 标准特征序列

处理完包含之后：

``` text
Raw Feature Sequence
↓
Non-Inclusion Processing
↓
Standard Feature Sequence
```

后续所有线段分型判断：

``` text
ONLY USE Standard Feature Sequence
```

不能再回头直接使用Raw Feature Sequence。

第67课明确将经过非包含处理的特征序列称为标准特征序列。citeturn0search0turn0search7

------------------------------------------------------------------------

# 14. 特征序列的分型

把：

``` text
FeatureElement
```

当作K线来处理。

三个连续标准特征元素：

``` text
F[i-1]
F[i]
F[i+1]
```

可以形成：

``` text
TOP
BOTTOM
```

但存在一个非常重要的方向限制。

------------------------------------------------------------------------

# 15. UP Segment只寻找特征序列顶分型

如果：

``` text
Segment.direction = UP
```

则：

``` text
FeatureSequence.direction = DOWN
```

此时只考察：

``` text
TOP FRACTAL
```

不把底分型作为该UP Segment的终止判断。

这是第67课明确规定的。citeturn0search0turn0search7

------------------------------------------------------------------------

# 16. DOWN Segment只寻找特征序列底分型

如果：

``` text
Segment.direction = DOWN
```

则：

``` text
FeatureSequence.direction = UP
```

只考察：

``` text
BOTTOM FRACTAL
```

不使用顶分型作为该DOWN Segment的终止判断。

------------------------------------------------------------------------

# 17. Segment Fractal对象

``` python
class SegmentFractal:

    id: int

    type:
        TOP
        BOTTOM

    feature_element_ids: tuple[int, int, int]

    center_element_id: int

    first_element_id: int
    second_element_id: int
    third_element_id: int

    has_gap:
        True
        False

    center_high: float
    center_low: float
```

------------------------------------------------------------------------

# 18. "缺口"定义

两个相邻特征序列元素：

``` text
F1
F2
```

如果：

``` text
F1.high < F2.low
```

或者反向：

``` text
F2.high < F1.low
```

则两者：

``` text
NO OVERLAP
```

称：

``` text
GAP
```

即：

``` text
gap = True
```

如果：

``` text
max(F1.low,F2.low)
<=
min(F1.high,F2.high)
```

则：

``` text
gap = False
```

------------------------------------------------------------------------

# 19. 线段结束的两种情况

第67课给出的严格标准实际上只有：

``` text
TYPE 1
TYPE 2
```

这两个条件覆盖全部线段划分情况。citeturn0search8

------------------------------------------------------------------------

# 20. TYPE 1：第一、第二特征元素之间没有缺口

以：

``` text
UP Segment
```

为例。

如果标准特征序列出现：

``` text
TOP FRACTAL
```

其三个元素：

``` text
F1 F2 F3
```

且：

``` text
F1 ↔ F2
```

没有缺口：

``` text
gap(F1,F2) = False
```

那么：

``` text
UP Segment
```

在该特征序列顶分型的高点处结束。

即：

``` text
Segment.end = TopFractal.high
```

这是：

``` text
TYPE_1
```

------------------------------------------------------------------------

# 21. TYPE 1 的DOWN情况

对于：

``` text
DOWN Segment
```

如果出现：

``` text
BOTTOM FRACTAL
```

且：

``` text
gap(F1,F2) = False
```

则：

``` text
DOWN Segment
```

在该底分型的低点处结束：

``` text
Segment.end = BottomFractal.low
```

------------------------------------------------------------------------

# 22. TYPE 2：第一、第二特征元素之间存在缺口

这是程序最容易写错的部分。

仍然以：

``` text
UP Segment
```

为例。

出现：

``` text
TOP FRACTAL
```

但是：

``` text
gap(F1,F2) = True
```

此时：

> **不能立即宣布UP Segment结束。**

必须进入：

``` text
TYPE_2_PENDING
```

------------------------------------------------------------------------

# 23. TYPE 2需要观察反向特征序列

从该特征序列顶分型的最高点开始：

``` text
向下一笔
```

进入新的：

``` text
DOWN Segment Candidate
```

然后观察这个新线段的：

``` text
反向特征序列
```

如果该新的反向特征序列出现：

``` text
BOTTOM FRACTAL
```

则：

``` text
原UP Segment结束
```

结束点：

``` text
原Top Fractal的高点
```

这就是：

``` text
TYPE_2
```

------------------------------------------------------------------------

# 24. TYPE 2的关键点

后一个反向特征序列：

``` text
不要求必须封闭前一个特征序列的缺口。
```

只要：

``` text
出现符合定义的反向特征序列分型
```

即可确认原线段结束。

并且：

> 后一个特征序列中的分型，不要求再判断其属于第一种还是第二种情况。

这一点来自第67课的明确规定。citeturn0search8

------------------------------------------------------------------------

# 25. DOWN Segment的TYPE 2

对称处理：

``` text
DOWN Segment
+
BOTTOM FRACTAL
+
F1/F2存在缺口
```

不能立即结束。

必须观察：

``` text
从该底分型最低点开始的向上一笔
```

形成的新：

``` text
UP Segment Candidate
```

如果其特征序列出现：

``` text
TOP FRACTAL
```

则：

``` text
原DOWN Segment结束
```

结束点：

``` text
原Bottom Fractal的低点
```

------------------------------------------------------------------------

# 26. 线段划分的核心状态机

``` text
SEGMENT_EXTENDING
        │
        ├── 无目标特征分型
        │       ↓
        │   EXTENDING
        │
        ├── 特征分型 + 无缺口
        │       ↓
        │   CONFIRMED
        │   TYPE_1
        │
        └── 特征分型 + 有缺口
                ↓
          TYPE_2_PENDING
                │
                ├── 反向特征序列无分型
                │       ↓
                │   原线段继续延伸
                │
                └── 反向特征序列出现目标分型
                        ↓
                    CONFIRMED
                    TYPE_2
```

------------------------------------------------------------------------

# 27. Segment状态

``` python
SegmentState:

    EXTENDING

    TYPE_2_PENDING

    CONFIRMED
```

不建议加入：

``` text
UNCERTAIN
MAYBE
PROBABLY
```

因为底层结构必须确定性。

------------------------------------------------------------------------

# 28. TYPE_2_PENDING的真正含义

这是非常重要的。

``` text
TYPE_2_PENDING
```

不是：

> "线段已经结束但等待确认。"

而是：

> **"出现了可能终结当前线段的特征序列分型，但按照TYPE_2定义，当前还没有满足线段终止条件。"**

所以此时：

``` text
current_segment仍然有效
```

只是进入：

``` text
待验证状态
```

------------------------------------------------------------------------

# 29. 当下性