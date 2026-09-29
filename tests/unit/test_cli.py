from chantrading.runtime.cli import main


def test_cli_emits_json(capsys):
    assert main(["--duration-ms","1000","--start-ms","100","--end-ms","1100"])==0
    out=capsys.readouterr().out
    assert '"duration_ms": 1000' in out
