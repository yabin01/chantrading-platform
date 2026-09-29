# Engine Pattern Fusion Requirements

Source-derived requirements preserved from the ChanLun 1M Trading Agent extension guide.

1. Keep trading decisions and risk inside deterministic state machines.
2. Expose SCAN → EVAL → RISK → EXEC → FILL → EXIT.
3. Use structured ReasonCodes for explanations.
4. Keep LLM outside geometric recognition and direct exchange order submission.
5. Use minimum-permission typed signing for execution.
6. Separate custody from the trading agent.
7. Make order submission idempotent with client_order_id.
8. Record fills, VWAP, fees and slippage.
9. Support deterministic replay and counterfactual analysis.
10. Provide an emergency kill switch with explicit recovery behavior.

Note: these are requirements extracted from the project source material; they are not a claim about the current implementation of any external service.