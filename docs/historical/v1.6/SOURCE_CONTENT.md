# ChanLun 1M Trading Agent 技术规格 v1.6

## 笔 → 线段 → 最小中枢 → 1分钟走势Ai → 同级别分解单元

> 版本：v1.6  
> 上级：v1.5  
> 固定操作级别：1分钟  
> 核心目标：把已经确认的笔和线段，严格递归成“完整的1分钟走势Ai”，并让Agent能够在实时状态下处理“一个Ai尚未完成 / Ai完成 / 扩张后拆成A0+A1”的问题。  
> 本版本不升级到5分钟，不使用高级别自动换档。

---

# 1. v1.6要解决什么

v1.5已经解决：

```text
分型
 ↓
笔
 ↓
有效转折分型
 ↓
交易触发
```

但是同级别分解策略真正需要的是：

```text
笔
 ↓
线段
 ↓
中枢
 ↓
1分钟走势类型
 ↓
A0
A1
A2
...
```

因此v1.6的核心任务是：

> **定义什么东西才有资格成为一个完整的1分钟走势Ai。**

只有这个问题解决：

```text
Ai vs Ai+2
```

才具有严格的算法意义。

---

# 2. 原文依据

第65课明确说明：

```text
线段至少三笔
```

并且线段前三笔必须存在重叠部分；连续三笔并不天然构成线段。citeturn0search2

第67课进一步使用：

```text
特征序列
标准特征序列
特征序列分型
```

来严格判断线段划分与破坏。citeturn0search5

第71课继续细化了特征序列包含关系、缺口封闭以及线段被笔破坏的判断逻辑。citeturn0search8

第39课则要求在同级别分解中，把已经完成的同级别走势定义成：

```text
A0
A1
A2
...
```

然后比较：

```text
Ai 与 Ai+2
```

并按照盘整背驰及后续突破条件机械操作。citeturn0search0turn0search3

---

# 3. 本项目对“1分钟走势Ai”的工程定义

本项目固定：

```text
操作级别 = 1分钟
```

因此：

```text
Ai
```

不是：

```text
任意一段价格波动
```

而必须是：

```text
一个完成的1分钟级别走势类型
```

工程上必须满足：

```text
至少一个1分钟级别中枢
```

然后根据：

```text
进入段
+
中枢
+
离开段
```

确定其完整结构。

---

# 4. 最小中枢

对于已经完成的线段序列：

```text
S0
S1
S2
```

如果三段的价格区间存在共同重叠：

```text
max(low(S0), low(S1), low(S2))
<
min(high(S0), high(S1), high(S2))
```

则：

```text
MIN_CENTER = TRUE
```

定义：

```python
center_high = min(
    high(S0),
    high(S1),
    high(S2)
)

center_low = max(
    low(S0),
    low(S1),
    low(S2)
)
```

当：

```python
center_low < center_high
```

则存在最小中枢。

---

# 5. 为什么不是“3线段=中枢”

这是一个必须严格区分的地方：

```text
3线段
```

只是：

```text
候选中枢结构
```

只有：

```text
三线段存在共同价格重叠
```

才可以确认：

```text
中枢
```

因此：

```python
if len(segments) >= 3:
    candidate_center()

if overlap_exists:
    confirmed_center()
```

---

# 6. 中枢对象

```python
class Center:

    id

    first_segment_id
    second_segment_id
    third_segment_id

    start_index
    end_index

    zg
    zd

    width

    state
```

其中：

```text
ZG = 中枢上沿
ZD = 中枢下沿
```

状态：

```text
CANDIDATE
CONFIRMED
EXTENDING
EXPANDING
TERMINATED
```

---

# 7. 中枢不是静态对象

中枢形成后：

```text
后续线段
```

可能继续进入：

```text
[ZD, ZG]
```

则：

```text
中枢延伸
```

所以：

```python
center.state = EXTENDING
```

而不是立即：

```text
TERMINATED
```

---

# 8. 中枢延伸

例如：

```text
S0
S1
S2
```

形成：

```text
ZD < ZG
```

之后：

```text
S3
```

仍然与：

```text
[ZD,ZG]
```

发生有效重叠。

则：

```text
CENTER_EXTENDING
```

中枢的有效时间范围继续延长。

---

# 9. 中枢扩张

本项目严格遵循你的策略选择：

> **1分钟级别出现扩张，不升级到5分钟，而是把走势重新拆成两个或多个1分钟走势Ai。**

因此：

```text
扩张
≠
升级
```

而是：

```text
扩张
 ↓
重新划分
 ↓
A0 + A1
```

---

# 10. 扩张与升级的工程区别

传统递归分析可以：

```text
1分钟
 ↓
5分钟
```

但本Agent：

```text
1分钟
 ↓
仍然1分钟
```

因此：

```python
if center_expands:
    split_same_level()
```

禁止：

```python
if center_expands:
    upgrade_to_5m()
```

---

# 11. 1分钟走势Ai的基本结构

一个完整Ai：

```text
进入段
   ↓
┌───────────┐
│ 1分钟中枢 │
└───────────┘
   ↓
离开段
```

即：

```text
Entry
+
Center
+
Exit
=
Ai
```

---

# 12. 最小Ai

工程上：

```text
至少：
1个进入段
+
1个最小中枢
+
1个离开段
```

因此最小结构可以抽象成：

```text
S0
S1
S2
S3
S4
```

其中：

```text
S0 = Entry
S1,S2,S3 = Center构成基础
S4 = Exit
```

这就是本项目默认的：

```text
5线段最小Ai模板
```

但必须注意：

> **“5线段”是最小完整结构模板，不代表任何连续5线段都自动成为一个Ai。**

必须先满足：

```text
中枢成立
+
进入关系
+
离开关系
+
走势结束条件
```

---

# 13. Ai对象

```python
class Ai:

    id

    direction:
        UP
        DOWN

    entry_segment_id

    center_id

    exit_segment_id

    start_index
    end_index

    start_price
    end_price

    center_high
    center_low

    state

    structure_version
```

状态：

```text
BUILDING
CENTER_FORMING
CENTER_CONFIRMED
EXIT_FORMING
CONFIRMED
INVALIDATED
SPLIT
```

---

# 14. Ai状态机

```text
BUILDING
   ↓
CENTER_FORMING
   ↓
CENTER_CONFIRMED
   ↓
EXIT_FORMING
   ↓
CONFIRMED
```

如果中枢扩张：

```text
CENTER_CONFIRMED
        ↓
     EXPANSION
        ↓
      SPLIT
```

然后：

```text
A0
+
A1
```

重新进入同级别分解。

---

# 15. Entry段

定义：

```text
Entry = Ai开始前进入中枢的同方向线段/走势结构
```

例如上涨Ai：

```text
S0 ↑
 ↓
进入中枢
```

则：

```text
Entry.direction = UP
```

下跌Ai：

```text
S0 ↓
 ↓
进入中枢
```

则：

```text
Entry.direction = DOWN
```

---

# 16. Exit段

离开中枢的线段必须能够区分：

```text
继续中枢内部震荡
```

与：

```text
真正离开中枢
```

定义：

```python
if exit_segment.price_range
    completely_outside(center_range):
        EXIT_CONFIRMED
```

这里的具体价格边界必须使用：

```text
ZG
ZD
```

而不是：

```text
上一根K线
```

---

# 17. 中枢内部震荡不能提前结束Ai

例如：

```text
       S4
      /  \
     /    \
---- ZG ----------
     \    /
      \  /
---- ZD ----------
```

如果：

```text
S4
```

仍然在：

```text
[ZD,ZG]
```

内部：

```text
Ai继续BUILDING
```

不能：

```text
Ai结束
```

---

# 18. 真正离开中枢

例如上涨：

```text
          S_exit
            /
----------- ZG
          /
--------- ZD
```

当：

```text
exit.low > ZG
```

则：

```text
向上离开中枢
```

对于下跌：

```text
exit.high < ZD
```

则：

```text
向下离开中枢
```

---

# 19. 为什么不能只看“突破ZG”

因为：

```text
单根K线突破
```

不等于：

```text
线段/走势离开
```

本Agent的级别原则：

```text
K线
→
分型
→
笔
→
线段
→
中枢
→
Ai
```

因此：

```text
离开中枢
```

至少应该由：

```text
已确认的线段结构
```

来确认。

---

# 20. Ai结束的核心条件

一个Ai只有在：

```text
中枢已经确认
+
出现有效离开段
+
离开后不再属于原Ai的内部延伸
```

时：

```text
Ai = CONFIRMED
```

否则：

```text
Ai = BUILDING
```

---

# 21. Ai不能使用未来函数

错误：

```python
# 看到未来走势后
Ai.end = future_segment
```

正确：

```python
on_segment_confirmed(segment):
    update_current_ai(segment)
```

只有当前线段已经确认：

```text
才允许改变Ai状态。
```

---

# 22. 实时Ai与事后Ai

系统必须同时保存：

```python
ai.current_state
ai.confirmed_at
ai.end_index
```

例如：

```text
10:30
A0:
BUILDING

10:35
出现最小中枢

A0:
CENTER_CONFIRMED

10:42
出现有效离开段

A0:
EXIT_FORMING

10:45
离开结构确认

A0:
CONFIRMED
```

回测必须以：

```text
10:45
```

作为：

```text
A0正式完成时间
```

不能提前使用10:45之后的信息。

---

# 23. Ai与线段的关系

必须严格：

```text
Ai
↓
由多个Segment组成
```

而不是：

```text
Ai
=
一根线段
```

本项目固定：

```text
Segment是Ai的基本结构单位
```

---

# 24. Ai的最小结构模板

上涨：

```text
S0 ↑ 进入
S1 ↓
S2 ↑
S3 ↓
S4 ↑ 离开
```

其中：

```text
S1/S2/S3
```

构成最小中枢。

整体：

```text
S0
 ↓
┌─────────┐
│ S1      │
│   S2    │
│     S3  │
└─────────┘
 ↓
S4
```

得到：

```text
Ai = UP
```

下跌完全镜像。

---

# 25. 注意：S0/S4不一定只有一个线段

实际市场中：

```text
进入段
```

可能本身包含更复杂的同级结构。

因此数据模型不要写死：

```python
entry_segment_count = 1
exit_segment_count = 1
```

应该写：

```python
entry_segments = [...]
exit_segments = [...]
```

而：

```text
最小Ai
```

才使用：

```text
1 + 3 + 1
```

作为模板。

---

# 26. Ai扩张

这是整个v1.6最重要的地方。

假设：

```text
A0
```

原本正在形成：

```text
Entry
+
Center
+
Exit