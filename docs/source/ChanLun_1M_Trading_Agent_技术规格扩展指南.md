# ChanLun 1M Trading Agent 技术规格扩展指南

> Source transcription from the project reference PDF. This document preserves the source terminology and design constraints; it is not a silently reconciled rewrite.

## Hyperliquid 基础设施与可观测性融合规格

适用标的：ETH-USD 永续合约  
运行周期：1分钟（固定操作级别）  
上级规格：v2.8 ExecutionEngine / v3.0 Agent Core / v3.1 Live State Engine

核心目标：在坚守缠论 100% 确定性拓扑计算与分型硬止损的前提下，融合 Engine（withengine.ai）的链上非托管安全授权、流式决策管道、反事实归因分析以及外挂 LLM 交互机制。

## 1. 架构定位与职责边界划分

融合遵循“核心硬隔离”原则：交易决策与风控完全闭锁在确定性状态机内，外部框架仅作为非托管执行、审计追踪与交互的宿主扩展。

### 架构

- 流式可观测与交互层
  - 终端流式事件：SCAN → EVAL → RISK → EXEC → FILL → EXIT
  - 交易副驾（LLM）：仅读 Canonical State，解析 ReasonCodes，输出解释与复盘
  - 交互干预：一键 Kill-Switch 熔断 / 提升止损级别
- 缠论 1M 确定性核心引擎
  - 1m K线处理 → 分型 → 严格笔 → 特征序列线段 → 1m中枢 → Ai (A0~An)
  - 同级别比较资格断言 → MACD 面积背驰 → 六重门禁仲裁（BUY/HOLD/SELL）
  - 确认底/顶分型极值硬止损
  - 单笔 0.5% 仓位预算（拒用 ATR 移动止损）
- 确定性 OrderIntent（包含分型止损价）
- 链上非托管执行层
  - 专属 Hyperliquid USDC 智能金库（用户自主掌管私钥）
  - Agent 仅获 EIP-712 最小交易权限（禁止提现与跨地址转账）
  - 幂等 OrderClient → 撮合成交回报 → 真实滑点基点级归因

## 2. 链上非托管与 EIP-712 最小授权模块

为避免传统 API Key 暴露导致的提现风险，执行层接入 Hyperliquid 智能金库机制与 EIP-712 类型化签名协议。

### 2.1 权限最小化数据结构

Agent 仅持有用于交易签名的独立代理密钥（Agent Key）。资金存放在金库地址，该私钥在智能合约层被剥离一切非交易权限。

### 2.2 签名与广播流程

1. 意图转化：DecisionAgent 产生的 OrderIntent 经 RiskEngine 审查放行后，传入 ExecutionEngine。
2. 离线组包：按 Hyperliquid 规范组装 EIP-712 载荷（Asset, isBuy, limitPx, sz, reduceOnly, cloid）。
3. 隔离签名：由专职代理签名器签名，广播至验证节点。
4. 权限防护：任何伪造的转账或提款调用将在节点层面直接验证失败并报错，杜绝盗币可能。

示例类型：

```python
from dataclasses import dataclass
from enum import Enum

class EIP712ActionType(Enum):
    ORDER = "Order"
    CANCEL = "Cancel"
    SET_TRIGGER = "SetTrigger"

@dataclass(frozen=True)
class EIP712AuthContext:
    vault_address: str
    agent_address: str
    chain_id: int
    verifying_contract: str
    nonce: int
```

## 3. 六阶段流式决策可观测管道

复刻 Engine 的六阶段事件追踪体系，将缠论复杂的逐 K 线推导与执行过程按纳秒/毫秒时间戳暴露给用户前端，消除量化系统黑盒。

### 3.1 阶段规范

| 阶段 | 驱动时钟 | 核心捕获要素 | 缠论映射上下文 |
|---|---|---|---|
| SCAN | 1m 收盘时钟 | bar_id, OHLCV, 顶底分型候选与确认状态 | K线包含关系处理、确认笔端点更新 |
| EVAL | 1m 收盘时钟 | 当前走势 Ai 拓扑、比较资格状态、MACD 面积衰减比率 | 同级别分解断言（A4 vs A6）、盘整背驰确认 |
| RISK | 事件驱动 | 账户权益、单笔风险预算金额（Account × 0.5%）、仓位头寸核算 | 最近确认底/顶分型极值点锁定、0.05% Buffer 校验 |
| EXEC | 事件驱动 | EIP-712 签名哈希、Hyperliquid 网关通信延迟、幂等校验 | client_order_id 注册、reduce_only 标记 |
| FILL | 撮合回调 | 实际成交价格、VWAP、手续费资产、基点滑点（bps） | 真实滑点损耗核算（FillPrice − RefPrice） |
| EXIT | 实时风控时钟 | 标记价格波动、保护止损单存续监测、次级别分型抬升触发 | 结构止损单向保护、策略正常背驰平仓 |

### 3.2 管道事件格式示例

```json
{
  "timestamp": 1773449642340,
  "stage": "EVAL",
  "data": {
    "active_ai": "A6_UP",
    "comparison_anchor": "A4_UP",
    "eligibility": "ELIGIBLE",
    "price_extended": true,
    "area_decay_ratio": 0.72,
    "divergence_status": "DIVERGENCE_CONFIRMED",
    "trigger_fractal_id": "F_20260913_00142",
    "reason_codes": [
      "SAME_LEVEL_LONG_EXIT",
      "CONSOLIDATION_DIVERGENCE_CONFIRMED",
      "FRACTAL_CONFIRMED"
    ]
  }
}
```

## 4. 交易副驾驶（Copilot）与自然语言交互层

在保证交易核心零污染的前提下，引入外挂大语言模型作为交易员的助理界面，负责解释与应急介入。

### 4.1 职责限定

允许：
- 读取只读状态快照（Canonical State），将抽象 ReasonCodes 转化为严谨的人类复盘报告。
- 解读当前 A 序列走向与为何持续 HOLD 的数学依据。
- 接收用户的自然语言风控指令（如强制平仓、收紧止损），经结构化编译后发送至风控队列。

绝对禁止：
- 参与分型、笔、线段或走势的几何形态识别。
- 绕过结构计算引擎自行给出买卖建议。
- 直接调用底层交易所报单函数。

示例：用户问“为什么刚才创新高时没有获利平仓？”

Copilot 提取已落盘的 EVAL 日志切片：
- 状态：HOLD_CANNOT_COMPARE
- 结构事实：A3 回调段未有效跌破 A0 关键高点，A4 与 A2 比较资格阻断
- MACD 事实：A4 红柱面积尚未达到法定比较窗口

格式化报告：当前价格虽创新高，但由于回调段 A3 尚未有效跌破 A0 关键位，根据缠论同级别分解协议第 38 课机制，A4 与 A2 的比较资格处于阻断状态（HOLD_CANNOT_COMPARE）。系统判定为走势未完美，因此拒绝主观猜顶，继续持有。

### 4.3 自然语言干预编译

例如：
“立刻平掉所有仓位，市场不对劲”
→ EmergencyExitIntent(reason="MANUAL_COMMAND", symbol="ETH-USD")
→ 经 RiskEngine 签名
→ 广播至 Hyperliquid 撮合层执行。

## 5. 反事实推演与策略参数离线归因

吸收 Engine 的归因评估机理，在 v2.9 Backtest & Replay Engine 基础上构建影子推演沙箱。

每完成一笔真实交易（或回测交易），系统自动截取入场时刻的完整结构快照（Snapshot），并在内存沙箱中并发执行变异分支模拟。

示例变异：
- 分支 A：实盘对照组（0.05% Buffer，MACD 衰减阈值 10%）
- 分支 B：零 Buffer 挂单
- 分支 C：衰减阈值提高至 20%

归因指标：
- 结构稳健度（Alpha Robustness）
- 参数敏感性（Parameter Drag）
- 滑点侵蚀度（Slippage Impact）

## 6. 一键单向熔断保护机制（Kill-Switch Protocol）

触发源：

### 自动
- 本地仓位与交易所真实持仓对账不一致（RECONCILIATION_REQUIRED）
- 交易所保护止损单丢失且在 3 秒内重建失败（PROTECTION_LOST）
- K线数据连续缺失超过 2 根（DATA_GAP）

### 人工
- Web 终端或 Telegram 一键触发 EMERGENCY_KILL_SWITCH

熔断执行：
- 系统状态立即变更为 FROZEN
- 决策引擎完全拒绝产生 BUY 指令
- 不得撤销已在 Hyperliquid 撮合引擎端挂载的原生分型止损单（Stop-Market）

可选平仓模式：
1. 默认：保持现有止损有效，阻断所有新开仓，等待走势自行决出胜负。
2. 硬清算：立即以市价（IOC + reduce_only）全额平仓，取消所有挂单，全面归还现金至金库。

## 7. 融合后核心模块集成清单

建议结构：

```text
chanlun_agent/
├── live/
│   ├── bar_aggregator.py
│   ├── canonical_state.py
│   └── streaming_pipeline.py
├── copilot/
│   ├── reason_translator.py
│   ├── assistant_interface.py
│   └── manual_interceptor.py
├── execution/
│   ├── eip712_signer.py
│   ├── vault_adapter.py
│   └── order_state_machine.py
└── replay/
    ├── deterministic_replay.py
    └── counterfactual_sandbox.py
```

## 8. 验收标准

- 私钥无提现权：Agent 密钥丢失测试中，转账/提款调用必须被拒绝。
- 端到端流式可追溯：从K线收盘到成交回报，输出符合 SCAN → EXIT 格式的带时间戳结构化 JSON 日志；源指南给出的目标为 500ms 内。
- 零幻觉保证：Copilot 自然语言复盘必须映射到对应 ReasonCodes，严禁出现未经几何引擎确认的主观走势推论。
