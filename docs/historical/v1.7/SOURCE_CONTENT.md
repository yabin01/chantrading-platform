# ChanLun 1M Trading Agent 技术规格 v1.7

## ChanLunStateEngine：完整缠论结构状态引擎与实时事件架构

> 版本：v1.7  
> 固定操作级别：1分钟  
> 本版本目标：把“分型 → 笔 → 线段 → 中枢 → 1分钟走势Ai → 同级别分解 → 盘整背驰 → 交易分型 → 持仓/止损”统一为一个可实时运行、可回放、可审计、无未来函数的确定性状态引擎。

---

## 1. v1.7定位

前面的v1.x解决“缠论规则如何形式化”，v1.7开始解决“这些规则如何成为真正的软件系统”。

核心组件：

```text
ChanLunStateEngine
```

它是Trading Agent的结构大脑。

---

## 2. 总体架构

```text
1分钟OHLCV
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
1分钟走势 Ai
    ↓
同级别分解 A0...An
    ↓
合法比较 Ai / Ai+2
    ↓
价格 + MACD面积
    ↓
盘整背驰
    ↓
有效交易分型
    ↓
BUY / SELL / HOLD
    ↓
最近有效分型极值止损
    ↓
Hummingbot执行
```

---

## 3. 分层原则

严格禁止：

```text
MACD决定笔
MACD决定线段
EMA决定中枢
K线直接决定Ai
Ai直接绕过交易分型下单
```

正确关系：

```text
K线
→ 结构
→ 结构确认
→ Ai
→ 力度
→ 盘整背驰
→ 交易分型
→ 交易
```

---

## 4. 数据源最小化

本项目只使用：

```text
OHLCV
MACD
EMA5
EMA10
```

MACD：

```text
DIF
DEA
HIST
```

并计算：

```text
positive_area
negative_area
total_abs_area
```

EMA5/EMA10只用于：

```text
辅助精确确认分型
过滤中继分型
```

不能成为独立交易系统。

---

## 5. 核心数据模型

### MarketBar

```python
@dataclass
class MarketBar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    dif: float
    dea: float
    hist: float

    ema5: float
    ema10: float
```

### StructureEvent

```python
@dataclass
class StructureEvent:
    event_id: str
    event_type: str
    timestamp: int
    source_id: str
    parent_id: str | None
    structure_version: int
    payload: dict
```

所有结构必须可以追溯到具体K线时间。

---

## 6. 唯一ID

```text
F = Fractal
B = Bi
S = Segment
C = Center
A = Ai
D = Divergence
T = Trade
```

例如：

```text
F000123
B000082
S000031
C000014
A000007
D000003
T000005
```

这样任何交易都可以追溯：

```text
交易
→ 分型
→ 笔
→ 线段
→ 中枢
→ Ai
→ 同级别比较
→ 盘整背驰
```

---

## 7. Event Bus

核心事件：

```text
BAR_CLOSED

FRACTAL_CANDIDATE
FRACTAL_CONFIRMED

BI_CANDIDATE
BI_CONFIRMED

SEGMENT_CANDIDATE
SEGMENT_CONFIRMED

CENTER_CANDIDATE
CENTER_CONFIRMED
CENTER_EXTENDED
CENTER_EXPANDED
CENTER_TERMINATED

AI_UPDATED
AI_CONFIRMED
AI_SPLIT

DIVERGENCE_CANDIDATE
DIVERGENCE_CONFIRMED

TRADE_FRACTAL_CONFIRMED
TRADE_SIGNAL

ORDER_SUBMITTED
ORDER_FILLED
ORDER_REJECTED

STOP_UPDATED
POSITION_CLOSED
```

---

## 8. 为什么采用事件驱动

缠论结构不是“一根K线就产生最终答案”。

真实过程：

```text
市场新K线
↓
候选结构
↓
结构发展
↓
结构确认
↓
新结构产生
```

所以程序应该记录：

```text
发生了什么
何时发生
哪个结构发生
为什么发生
```

而不是只保留最后一张DataFrame。

---

## 9. State Snapshot

每根1分钟K线结束保存一个快照：

```python
@dataclass
class EngineSnapshot:
    timestamp
    latest_bar

    current_fractal
    confirmed_fractals

    current_bi
    confirmed_bis

    current_segment
    confirmed_segments

    current_center
    confirmed_centers

    current_ai
    confirmed_ais

    same_level_state
    divergence_state

    position_state
    risk_state
```

---

## 10. Agent看到的是State

Agent不需要重新扫描几千根K线，而应该看到：

```json
{
  "timeframe": "1m",
  "current_ai": "A6",
  "ai_state": "BUILDING",
  "ai_direction": "UP",

  "current_center": {
    "zg": 2150.2,
    "zd": 2137.8,
    "state": "EXTENDING"
  },

  "last_confirmed_fractal": {
    "type": "TOP",
    "price": 2164.7
  },

  "position": "LONG",
  "decision": "HOLD"
}
```

---

## 11. 算法与Agent职责分离

### Deterministic Structure Engine负责

```text
分型
笔
线段
中枢
Ai
MACD面积
同级别比较条件
```

### Agent负责

```text
读取结构
理解当前状态
解释规则
输出BUY / SELL / HOLD
```

LLM不应该直接负责底层分型、笔、线段识别。

---

## 12. 为什么不让LLM直接识别结构

例如：

```text
“看看这几十根K线是不是顶分型。”
```

作为核心交易算法是不合适的，因为：

```text
不可完全重复
边界条件容易漂移
难以证明无未来函数
难以进行严格回测
```

因此：

```text
LLM ≠ Structure Parser
```

而是：

```text
Structure Engine → Agent
```

---

## 13. Future Leak Detector

每个结构必须保存：

```text
detected_at
confirmed_at
```

交易信号保存：

```text
signal_at
```

如果：

```text
signal_at < confirmed_at
```

则：

```text
FUTURE_LEAK
```

回测直接判定无效。

---

## 14. 典型未来函数错误

错误：

```text
10:01 疑似顶分型
10:05 才确认
10:01 开仓
```

正确：

```text
10:01 candidate
10:02 candidate
10:03 candidate
10:04 candidate
10:05 confirmed
10:05以后才允许产生信号
```

---

## 15. 结构版本

未确认结构可以：

```text
A0.v1
A0.v2
A0.v3
```

随着新K线不断更新。

一旦：

```text
A0 = CONFIRMED
```

则：

```text
A0 immutable
```

后续只能产生：

```text
A1
A2
...
```

而不能偷偷重写A0。

---

## 16. 状态枚举

```python
class StructureState(Enum):
    UNKNOWN = 0
    CANDIDATE = 1
    FORMING = 2
    CONFIRMED = 3
    EXTENDING = 4
    INVALIDATED = 5
    TERMINATED = 6
    SPLIT = 7
```

---

## 17. 分型状态

```text
UNKNOWN
↓
CANDIDATE
↓
CONFIRMED
```

如果后续出现更强端点：

```text
CANDIDATE
↓
SUPERSEDED
```

这里的含义不是“这根K线不存在”，而是：

```text
它不再作为当前有效端点。
```

这正是处理你前面强调的：

```text
顶分型
↓
底分型
↓
没有独立K线
↓
不能成笔
↓
后面出现更高顶
↓
前面的底/顶成为中继结构
```

所需要的状态基础。

---

## 18. 笔状态

```text
BI_CANDIDATE
BI_CONFIRMED
BI_SUPERSEDED
```

笔端点只能来自：

```text
有效分型
```

不能直接来自任意K线最高/最低点。

---

## 19. 线段状态

```text
SEGMENT_CANDIDATE
SEGMENT_FORMING
SEGMENT_CONFIRMED
SEGMENT_TERMINATED
```

线段必须经过：

```text
笔
+
特征序列
+
线段成立/破坏条件
```

不能简单：

```text
3笔 = 自动线段
```

---

## 20. 中枢状态

```text
CANDIDATE
↓
CONFIRMED
↓
EXTENDING
↓
TERMINATED
```

发生扩张：

```text
EXTENDING
↓
EXPANDED
↓
SPLIT
```

---

## 21. Ai状态

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

扩张：

```text
CENTER_CONFIRMED
↓
EXPANSION
↓
SPLIT
↓
A0 + A1
```

---

## 22. 最小中枢模型

对已经确认的线段：

```text
S0
S1
S2
```

计算：

```python
zg = min(high(S0), high(S1), high(S2))
zd = max(low(S0), low(S1), low(S2))
```

如果：

```python
zd < zg
```

才存在共同重叠区间。

因此：

```text
3线段 ≠ 自动中枢
```

而是：

```text
3线段 + 共同重叠 = 中枢
```

---

## 23. 最小Ai

本项目把一个完整1分钟走势Ai工程化为：

```text
进入段
+
至少一个有效1分钟中枢
+
离开段
```

最小模板：

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

形成最小中枢。

于是：

```text
S0 + Center(S1,S2,S3) + S4
=
最小完整Ai
```

注意：

> 5线段是最小模板，不意味着任何连续5线段都自动构成Ai。

---

## 24. Entry与Exit不能写死成一根线段

最小模板是：

```text
1 + 3 + 1
```

但实际市场可能更复杂。

因此对象设计：

```python
entry_segments = [...]
center_segments = [...]
exit_segments = [...]
```

而不是：

```python
entry_segment_count = 1
exit_segment_count = 1
```

---

## 25. Ai对象

```python
@dataclass
class Ai:
    id
    direction

    entry_segments
    center_id
    exit_segments

    start_index
    end_index

    start_price
    end_price

    center_high
    center_low

    state
    structure_version

    detected_at
    confirmed_at
```

---

## 26. Ai方向

不能只用：

```python
end_price > start_price
```

判断方向。

应根据：

```text
结构方向
+
进入段
+
离开段
```

确定。

例如：

```text
Entry ↑
Center
Exit ↑
```

得到：

```text
Ai = UP
```

镜像为：

```text
Ai = DOWN
```

---

## 27. 中枢延伸

中枢确认后，如果后续线段继续属于原中枢内部：

```text
Center = EXTENDING
```

此时：

```text
Ai继续BUILDING
```

不能提前结束Ai。

---

## 28. 中枢扩张

本项目明确：

```text
扩张 ≠ 升级
```

固定：

```text
1分钟
```

所以：

```text
1分钟中枢扩张
↓
重新分解
↓
A0 + A1
```

禁止：

```text
1分钟
↓
5分钟
```

---

## 29. ExpansionEvent

```python
@dataclass
class ExpansionEvent:
    source_ai_id
    old_center_id
    expansion_segment_id

    new_center_id

    split_index
    split_price

    new_ai_id
    structure_version
```

`split_index`非常重要，因为它决定：

```text
旧A0在哪里结束
新A1从哪里开始
```

从而保证A序列没有错误重叠。

---

## 30. SameLevelDecomposition

```python
class SameLevelDecomposition:

    confirmed_ai = []
    current_ai = None

    expansion_events = []

    def on_segment_confirmed(self, segment):
        self.current_ai.update(segment)

        if self.current_ai.detect_expansion():
            self.split_current_ai()

        if self.current_ai.is_complete():
            self.confirm_ai()
            self.start_new_ai()
```

---

## 31. Ai唯一分解原则

一旦：

```text
Ai CONFIRMED
```

就：

```text
append(Ai)
```

并：

```text
current_ai = new Ai
```

已确认Ai不能因为后面走势更复杂而随意重写。

未确认Ai允许：

```text
structure_version++
```

---

## 32. AiSeries

```python
@dataclass
class AiSeries:
    confirmed: list[Ai]
    current: Ai | None
```

例如：

```text
confirmed:
A0 A1 A2 A3

current:
A4
```

不存在：

```text
future A5
```

---

## 33. 第39课递推规则的工程化原则

例如：

```text
A0 ↑
A1 ↓
A2 ↑
```
