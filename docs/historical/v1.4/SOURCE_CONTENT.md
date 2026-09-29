# ChanLun 1M Trading Agent 技术规格 v1.4

## 同级别分解盘整背驰 → A0...An 持仓/平仓状态机

> 版本：v1.4\
> 上级：v1.3\
> 固定操作级别：1分钟\
> 核心任务：把第39课的"同级别分解 + Ai与Ai+2比较力度 +
> 无背驰继续持有/继续观察"转化为严格可编码的状态机。\
> 本项目只做1分钟级别，不执行高级别自动换档。

------------------------------------------------------------------------

## 1. 理论边界

第38课明确提出，同级别分解可以把所有走势按一个固定级别的走势类型进行分解；在这种分解中，该级别不需要使用中枢延伸/扩展概念，允许"盘整+盘整"连接。citeturn0search1turn0search8

第39课进一步提出，把 `a` 定义为 `A0` 后，可以不断比较 `Ai` 与 `Ai+2`
的力度，用盘整背驰决定买卖；如果没有盘背，则进入"反向段是否突破前一同向段关键高/低点"的继续持有逻辑。citeturn0search2turn0search5

第40课讨论了小级别操作向高级别自动换档的可能性，但**本项目明确不采用这一机制**：始终锁定1分钟。citeturn0search0turn0search10

因此：

``` text
1分钟扩张
    ↓
不升级5分钟
    ↓
继续采用1分钟同级别分解
    ↓
A0 → A1 → A2 → … → An
```

------------------------------------------------------------------------

# 2. v1.4真正解决的问题

v1.3已经产生：

``` text
A0
A1
A2
A3
...
An
```

v1.4开始解决：

``` text
BUY
SELL
HOLD
```

核心判断：

``` text
Ai
↕
Ai+2
```

比较：

``` text
价格关系
+
MACD力度
```

判断：

``` text
盘整背驰
```

但必须再结合：

``` text
持仓状态
+
保护高/低点
+
后续反向Ai
```

不能简单理解为：

``` text
每出现Ai
→ 和Ai-2比较
→ 有背驰卖
→ 没背驰继续
```

------------------------------------------------------------------------

# 3. 两类核心状态

第39课的机械化规则可以抽象成两大类：

### 类型A：Ai与Ai+2盘整背驰

上涨：

``` text
A0 ↑
A1 ↓
A2 ↑

A2价格创新高
+
A2力度弱于A0
=
盘整顶背驰
```

下跌：

``` text
A0 ↓
A1 ↑
A2 ↓

A2价格创新低
+
A2力度弱于A0
=
盘整底背驰
```

### 类型B：没有盘整背驰

例如：

``` text
A0 ↑
A1 ↓
A2 ↑

A2没有盘背
```

则：

``` text
HOLD
```

继续：

``` text
A3 ↓
```

若：

``` text
A3没有跌破A0高点
```

则：

``` text
继续HOLD
```

第39课明确把这两类情况作为机械操作的核心分类。citeturn0search2turn0search5

------------------------------------------------------------------------

# 4. 关键纠正：A3不破A0时，不比较A4与A2来直接平仓

这是本项目必须固化的规则。

假设：

``` text
A0 ↑
A1 ↓
A2 ↑
A3 ↓
A4 ↑
```

且：

``` text
A2与A0没有盘整背驰
A3没有跌破A0高点
```

那么：

``` text
不能因为A4出现
就简单执行：

A4 vs A2
→ 盘背？
→ 卖出
```

正确状态是：

``` text
LONG
 ↓
A2无盘背
 ↓
A3未破保护高点
 ↓
PROTECTION_ACTIVE
 ↓
继续观察后续结构
```

第39课的原文规则是：若 `i` 为偶数且 `Ai+3` 不跌破 `Ai`
高点，则继续持有，直到后续相应结构突破后，再在下一同向段出现"不创新高"或盘整顶背驰时退出；反向情况对称。citeturn0search2turn0search5

------------------------------------------------------------------------

# 5. PositionState

``` python
class PositionState:

    FLAT
    LONG
    SHORT

    entry_ai_id
    entry_fractal_id

    stop_price

    protected_ai_id
    protected_extreme

    exit_candidate
```

进一步细分：

``` text
LONG
LONG_WAIT_BREAK
LONG_WAIT_EXIT_CONFIRM
SHORT
SHORT_WAIT_BREAK
SHORT_WAIT_EXIT_CONFIRM
```

------------------------------------------------------------------------

# 6. ProtectionState

上涨持仓：

``` text
protected_ai = A0
protected_extreme = A0.high
```

空头持仓：

``` text
protected_ai = A0
protected_extreme = A0.low
```

对象：

``` python
class ProtectionState:

    active: bool

    anchor_ai_id: int

    anchor_extreme: float

    invalidation_direction:
        BREAK_BELOW
        BREAK_ABOVE

    invalidation_index: int | None
```

必须显式保存Anchor，不能依赖：

``` python
current_ai - 3
```

这种脆弱索引。

------------------------------------------------------------------------

# 7. 盘整顶背驰数学条件

对于两个同方向上涨走势：

``` text
Ai ↑
Ai+2 ↑
```

定义：

``` text
P1 = price_extreme(Ai)
P2 = price_extreme(Ai+2)

S1 = strength(Ai)
S2 = strength(Ai+2)
```

第一版严格定义：

``` text
P2 > P1
AND
S2 < S1
```

则：

``` text
TOP_DIVERGENCE = TRUE
```

注意：

``` text
MACD力度减弱
```

本身不能构成盘整顶背驰。

还必须：

``` text
价格创新高
```

------------------------------------------------------------------------

# 8. 盘整底背驰

对于：

``` text
Ai ↓
Ai+2 ↓
```

定义：

``` text
P1 = price_extreme(Ai)
P2 = price_extreme(Ai+2)

S1 = strength(Ai)
S2 = strength(Ai+2)
```

第一版：

``` text
P2 < P1
AND
S2 < S1
```

则：

``` text
BOTTOM_DIVERGENCE = TRUE
```

------------------------------------------------------------------------

# 9. "不创新高/不创新低"与"盘背"必须分开

以下两种情况不能混为一谈：

``` text
A2没有创新高
```

与：

``` text
A2创新高但力度减弱
```

前者：

``` text
NO_NEW_HIGH
```

后者：

``` text
TOP_DIVERGENCE
```

因此：

``` python
Event =
    DIVERGENCE
    |
    NO_NEW_HIGH
    |
    NO_NEW_LOW
```

这是v1.4状态机的基础。

------------------------------------------------------------------------

# 10. MACD力度定义

本项目只使用：

``` text
MACD Histogram
```

作为主要力度数据。

不使用：

``` text
金叉/死叉
```

作为盘背判断。

主要指标：

``` python
macd_area = Σ abs(hist[k])
```

其中 `k` 只属于该Ai的有效结构区间。

同时保存：

``` python
macd_area
macd_average
macd_peak
duration
```

但v1.4主指标固定：

``` text
MACD Total Area
```

------------------------------------------------------------------------

# 11. MACD面积边界

不能：

``` python
sum(all_hist_since_last_cross)
```

而必须：

``` python
sum(
    abs(hist[k])
    for k in Ai.price_range
)
```

并严格区分：

``` text
Ai真正结构结束时间
```

与：

``` text
Ai被确认时间
```

例如：

``` text
结构终点 = K1000
确认 = K1010
```

Ai本身的力度不能偷偷把：

``` text
K1001~K1010
```

算进去。

因此：

``` python
ai.end_index
ai.confirmation_index
```

必须分别保存。

------------------------------------------------------------------------

# 12. StrengthVector

预留：

``` python
class StrengthVector:

    macd_area
    macd_peak
    macd_duration

    price_amplitude
```

但决策优先级：

``` text
PRIMARY:
MACD area

SECONDARY:
Price amplitude

OPTIONAL:
MACD peak
```

EMA5/10继续只承担：

``` text
分型辅助
中继分型过滤
```

不替代MACD力度。

------------------------------------------------------------------------

# 13. 盘背判断函数

``` python
def is_top_divergence(ai_prev, ai_curr):

    assert ai_prev.direction == UP
    assert ai_curr.direction == UP

    price_ok = (
        ai_curr.price_extreme
        > ai_prev.price_extreme
    )

    strength_ok = (
        ai_curr.macd_area
        < ai_prev.macd_area
    )

    return price_ok and strength_ok
```

底背驰：

``` python
def is_bottom_divergence(ai_prev, ai_curr):

    assert ai_prev.direction == DOWN
    assert ai_curr.direction == DOWN

    price_ok = (
        ai_curr.price_extreme
        < ai_prev.price_extreme
    )

    strength_ok = (
        ai_curr.macd_area
        < ai_prev.macd_area
    )

    return price_ok and strength_ok
```

------------------------------------------------------------------------

# 14. 第一版不加入经验阈值

理论版本：

``` text
S2 < S1
```

即可。

工程上可以计算：

``` python
ratio = S2 / S1
```

以后再测试：

``` text
ratio < 0.95
ratio < 0.90
```

等经验过滤。

但v1.4不提前加入人为阈值。

原因：

> 先验证缠论原始结构规则，再通过历史回测决定是否需要噪声容差。

------------------------------------------------------------------------

# 15. Long主状态机

``` text
LONG
  ↓
新同向Ai
  ↓
Ai vs Ai-2
  ↓
┌───────────────┬────────────────┐
│ 盘整顶背驰     │ 无盘整顶背驰     │
↓               ↓
WAIT_TRIGGER    HOLD
FRACTAL          ↓
                Ai+3
                 ↓
        是否跌破保护高点？
          │              │
         YES             NO
          ↓              ↓
 WAIT_EXIT_CONFIRM   PROTECTION_ACTIVE
          ↓              ↓
        Ai+4          继续观察
          ↓
 不创新高/盘整顶背驰
          ↓
        SELL
```

------------------------------------------------------------------------

# 16. Short完全镜像

``` text
SHORT
  ↓
同方向Ai
  ↓
Ai vs Ai-2
  ↓
盘整底背驰
  ↓
WAIT_TRIGGER_FRACTAL
  ↓
底分型确认
  ↓
BUY / COVER
```

如果没有：

``` text
Ai+3升破保护低点
```

则：

``` text
继续持有空头
```

直到：

``` text
Ai+k+3升破Ai+k低点
```

再进入：

``` text
Ai+k+4
```

的：

``` text
不创新低
或
盘整底背驰
```

判断。citeturn0search2turn0search5

------------------------------------------------------------------------

# 17. A0→A6正式机械化

典型上涨持仓：

``` text
A0 ↑
A1 ↓
A2 ↑
A3 ↓
A4 ↑
A5 ↓
A6 ↑
```

首先：

``` text
A2 vs A0
```

如果：

``` text
无盘整顶背驰
```

则：

``` text
HOLD
```

随后：

``` text
A3
```

如果：

``` text
A3没有跌破A0.high
```

则：

``` text
PROTECTION_ACTIVE
```

继续：

``` text
A4
A5
A6
```

直到后续结构满足第39课对应的：

``` text
保护点被突破
```

然后：

``` text
下一同向Ai
```

出现：

``` text
不创新高
```

或：

``` text
盘整顶背驰
```

才进入：

``` text
SELL
```

这一逻辑直接对应第39课给出的机械规则。citeturn0search2turn0search6

------------------------------------------------------------------------

# 18. 为什么Agent不能预测A6

错误：

``` python
predict_A6()
```

正确：

``` python
on_confirmed_ai(ai):
    state_machine.update(ai)
```

每次只处理：

``` text
当前已经确认的Ai
```

因此Agent永远不会知道：

``` text
未来A6是什么
```

这与缠论的"当下性"完全一致。

------------------------------------------------------------------------

# 19. 交易信号不能直接落在Ai上

即使：

``` text
A2 vs A0
```

已经确认：

``` text
TOP_DIVERGENCE
```

也不能直接：

``` text
SELL
```

必须：

``` text
Ai盘整背驰
 ↓
找到对应最终转折结构
 ↓
找到有效顶分型
 ↓
顶分型确认
 ↓
SELL_EVENT
```

所以：

``` text
Ai = 结构级信号
Fractal = 交易级触发
```

------------------------------------------------------------------------

# 20. TradeSignal

``` python
class TradeSignal:

    side:
        BUY
        SELL

    ai_id

    comparison_ai_id

    divergence_type

    trigger_fractal_id

    trigger_index

    trigger_price

    reason_codes
```

例如：

``` json
{
  "side": "SELL",
  "ai_id": "A6",
  "comparison_ai_id": "A4",
  "divergence_type": "TOP_DIVERGENCE",
  "trigger_fractal_id": 1288,
  "trigger_index": 18342,
  "trigger_price": 2048.5,
  "reason_codes": [
    "AI_DIVERGENCE",
    "PRICE_NEW_HIGH",
    "MACD_AREA_WEAKER",
    "TOP_FRACTAL_CONFIRMED"
  ]
}
```

------------------------------------------------------------------------

# 21. HOLD必须是一等状态

不能：

``` text
没有BUY/SELL
→ 什么都不输出
```

必须明确：

``` json
{
  "action": "HOLD",
  "reason_codes": [
    "A2_NO_DIVERGENCE",
    "A3_DID_NOT_BREAK_PROTECTED_HIGH"
  ]
}
```

这会成为Agent每分钟的核心状态输出。

------------------------------------------------------------------------

# 22. 每分钟Agent必须能够回答

``` text
1. 当前Ai是谁？
2. 当前Ai方向？
3. 最近一个同方向Ai是谁？
4. 是否创新高/新低？
5. MACD面积是多少？
6. 与比较Ai相比力度是否减弱？
7. 是否盘整背驰？
8. 当前保护Anchor是什么？
9. Anchor是否被突破？
10. 当前BUY/SELL/HOLD？
11. 如果交易，哪个分型触发？
12. 止损在哪里？
```

------------------------------------------------------------------------

# 23. 止损机制

按照项目已经确定的规则：

### Long

``` text
BUY
 ↓
最近确认底分型
 ↓
stop = bottom_fractal.low
```

### Short

``` text
SELL
 ↓