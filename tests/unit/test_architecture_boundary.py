from pathlib import Path


def test_hyperliquid_imports_are_confined_to_adapter_package():
    root = Path(__file__).resolve().parents[2]
    src = root / "src" / "chantrading"
    violations = []

    for path in src.rglob("*.py"):
        if "adapters" in path.parts and "hyperliquid" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "import hyperliquid" in text or "from hyperliquid" in text:
            violations.append(str(path))

    assert not violations, f"Hyperliquid SDK import leaked into core: {violations}"
