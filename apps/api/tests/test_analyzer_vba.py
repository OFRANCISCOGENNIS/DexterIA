from __future__ import annotations

from pathlib import Path

from genisia.analysis.analyzer import RepositoryAnalyzer, render_markdown

MODULE = """Attribute VB_Name = "Tripe"
' Análise de obras: Projeto x Baixa SAP x Serviço
Option Explicit

Public Sub GerarTripe()
    Dim x As Long
    On Error Resume Next
    x = 1
End Sub

Private Sub Interna()
    x = 2
End Sub

Public Function Soma(a As Long, b As Long) As Long
    Soma = a + b
End Function

Public Sub ComParametro(ByVal n As Long)
    Shell("cmd /c dir")
End Sub
"""

LEGACY = """Attribute VB_Name = "Legado"
Sub Longa()
""" + "    i = i + 1\n" * 90 + """End Sub
"""


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "vba").mkdir(parents=True)
    # Exportação real do Excel: cp1252, sem UTF-8.
    (root / "vba" / "Tripe.bas").write_bytes(MODULE.replace("\n", "\r\n").encode("cp1252"))
    (root / "vba" / "Legado.bas").write_bytes(LEGACY.encode("cp1252"))
    return root


def test_vba_language_and_structure(tmp_path):
    report = RepositoryAnalyzer(_repo(tmp_path), "tripe").analyze()

    langs = {l["language"]: l for l in report["inventory"]["languages"]}
    assert langs["VBA"]["files"] == 2
    assert report["inventory"]["code_lines"] > 100

    vba = report["code"]["vba"]
    assert vba["modules"] == 2
    assert vba["procedures"] == 5
    # Só Subs públicas sem parâmetros são macros executáveis (Sub sem escopo é pública no VBA).
    assert {m["name"] for m in vba["public_macros"]} == {"GerarTripe", "Longa"}
    assert vba["without_option_explicit"] == ["vba/Legado.bas"]
    assert vba["on_error_resume_next"] == 1

    assert {"path": "vba/Legado.bas", "name": "Longa", "lines": 92} in report["code"]["long_functions"]
    assert any(r["rule"] == "vba_shell" and r["file"] == "vba/Tripe.bas" for r in report["code"]["risky_calls"])

    titles = [f["title"] for f in report["findings"]]
    assert "2 macro(s) VBA pública(s)" in titles
    assert "1 módulo(s) VBA sem Option Explicit" in titles


def test_vba_cp1252_is_decoded_and_rendered(tmp_path):
    report = RepositoryAnalyzer(_repo(tmp_path), "tripe").analyze()
    md = render_markdown(report)
    assert "## VBA" in md
    assert "`GerarTripe`" in md


def test_large_vba_module_is_still_analyzed(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    body = "Option Explicit\nPublic Sub Grande()\n" + ("    ' linha de comentario para ocupar espaco\n" * 12_000) + "End Sub\n"
    assert len(body) > 400_000
    (root / "Grande.bas").write_text(body, encoding="cp1252")
    report = RepositoryAnalyzer(root, "grande").analyze()
    assert report["code"]["vba"]["public_macros"][0]["name"] == "Grande"
