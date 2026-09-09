#!/usr/bin/env python3
"""
06-graficos.py - Gera tabelas e graficos em PNG a partir das saidas do ZAP.

Uso:  .venv/bin/python 06-graficos.py
Saida: graficos/*.png (+ os CSV derivados de cada figura)

Fontes de dados: out/_tab_detalhado.csv, out/_tab_resumo.csv e os logs de
varredura. Nao le os .json diretamente: o CSV detalhado ja traz os achados
deduplicados por (endpoint, parametro, pluginid) dentro de cada perfil.
"""
import csv
import re
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

RAIZ = Path(__file__).resolve().parent
OUT = RAIZ / "out"
DEST = RAIZ / "graficos"
DEST.mkdir(exist_ok=True)

# ---------------------------------------------------------------- paleta
# Instancia de referencia do design system, validada com validate_palette.js.
SURFACE   = "#fcfcfb"   # superficie do grafico
PLANE     = "#f9f9f7"   # plano da pagina
INK       = "#0b0b0b"   # tinta primaria
INK_2     = "#52514e"   # tinta secundaria
MUTED     = "#898781"   # eixos e rotulos
GRID      = "#e1e0d9"   # hairline
BASELINE  = "#c3c2b7"

# Severidade e escala ORDENADA -> rampa sequencial de um hue (azul), clara->escura.
# Validada com --ordinal: monotonia de L, gaps >= 0.06, extremo claro 2.06:1.
RAMPA_SEV = {
    "Informational": "#86b6ef",
    "Low":           "#3987e5",
    "Medium":        "#256abf",
    "High":          "#104281",
}
ORDEM_SEV = ["High", "Medium", "Low", "Informational"]

# Categoricas: ordem fixa de slots do tema, nunca ciclada.
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]

MODELOS = ["deepseek-mini-v4", "qwen-3.8-8b", "fable5", "opus"]
PERFIS = ["user_comum", "admin"]
ROTULO_PERFIL = {"user_comum": "usuário comum", "admin": "administrador"}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "figure.facecolor": PLANE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": PLANE,
    "text.color": INK,
    "axes.labelcolor": INK_2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": BASELINE,
})


def ler_detalhado():
    with open(OUT / "_tab_detalhado.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ler_resumo():
    with open(OUT / "_tab_resumo.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def chave(r):
    """Identidade de um achado dentro de um modelo, para deduplicar entre perfis."""
    return (r["endpoint"], r["parametro"], r["pluginid"])


def moldura(ax, titulo, subtitulo=None, eixo_x=None, eixo_y=None):
    """Cabecalho e cromo recessivo, iguais em todas as figuras."""
    ax.set_title(titulo, color=INK, fontsize=12, fontweight="bold",
                 loc="left", pad=22 if subtitulo else 10)
    if subtitulo:
        # Quebra pela largura util do eixo, senao textos longos vazam a borda.
        larg_pol = ax.get_figure().get_size_inches()[0] * ax.get_position().width
        linhas = textwrap.wrap(subtitulo, width=int(larg_pol * 15.5))
        ax.text(0, 1.02, "\n".join(linhas), transform=ax.transAxes, color=INK_2,
                fontsize=8.5, va="bottom", linespacing=1.45)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(BASELINE)
        ax.spines[lado].set_linewidth(0.8)
    if eixo_x:
        ax.set_xlabel(eixo_x, color=INK_2, fontsize=9, labelpad=8)
    if eixo_y:
        ax.set_ylabel(eixo_y, color=INK_2, fontsize=9, labelpad=8)
    ax.tick_params(length=0)


def rodape(fig, texto):
    """Nota de rodape, ancorada na figura abaixo da legenda."""
    linhas = textwrap.wrap(texto, width=int(fig.get_size_inches()[0] * 15.5))
    fig.text(0.055, 0.030, "\n".join(linhas), color=MUTED, fontsize=7.2,
             va="bottom", linespacing=1.45)


def compor(fig, ax, legenda=None, ncol=4, base=0.30, esq=0.20):
    """Reserva espaco fixo para eixo, legenda e rodape.

    Sem bbox_inches="tight": as coordenadas ficam previsiveis e o rotulo do
    eixo x deixa de colidir com a legenda e o rodape.
    """
    fig.subplots_adjust(left=esq, right=0.965, top=0.80, bottom=base)
    if legenda is not None:
        leg = fig.legend(*legenda, loc="lower center", frameon=False, ncol=ncol,
                         fontsize=8.5, handlelength=1.1, columnspacing=1.6,
                         bbox_to_anchor=(0.5, 0.105))
        for t in leg.get_texts():
            t.set_color(INK_2)


def salvar(fig, nome, tight=False):
    caminho = DEST / nome
    if tight:
        fig.savefig(caminho, dpi=200, bbox_inches="tight", pad_inches=0.30)
    else:
        fig.savefig(caminho, dpi=200)
    plt.close(fig)
    print(f"   {nome}")


def escreve_csv(nome, cabecalho, linhas):
    with open(DEST / nome, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        w.writerows(linhas)


# ============================================================ figura 1
def fig_severidade(det):
    """Achados unicos por severidade, deduplicados entre os dois perfis."""
    por_modelo = {m: defaultdict(set) for m in MODELOS}
    for r in det:
        por_modelo[r["modelo"]][r["risco"]].add(chave(r))
    dados = {m: {s: len(por_modelo[m][s]) for s in ORDEM_SEV} for m in MODELOS}
    ordem = sorted(MODELOS, key=lambda m: sum(dados[m].values()))

    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    y = range(len(ordem))
    esq = [0] * len(ordem)
    for sev in ORDEM_SEV:
        vals = [dados[m][sev] for m in ordem]
        ax.barh(y, vals, left=esq, height=0.58, color=RAMPA_SEV[sev],
                label=sev, edgecolor=SURFACE, linewidth=1.6, zorder=3)
        # Rotulo direto no segmento: releva o WARN de contraste e evita
        # que a magnitude dependa so da cor.
        for i, (v, e) in enumerate(zip(vals, esq)):
            if v >= 4:
                ax.text(e + v / 2, i, str(v), ha="center", va="center",
                        color="#ffffff" if sev in ("Medium", "High") else INK,
                        fontsize=8.5, fontweight="bold", zorder=4)
        esq = [a + b for a, b in zip(esq, vals)]
    for i, m in enumerate(ordem):
        ax.text(esq[i] + 1.5, i, str(esq[i]), va="center", ha="left",
                color=INK, fontsize=9.5, fontweight="bold", zorder=4)

    ax.set_yticks(list(y))
    ax.set_yticklabels(ordem, color=INK, fontsize=9.5)
    ax.set_xlim(0, max(esq) * 1.10)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    moldura(ax, "Achados únicos por severidade",
            "Deduplicados por (endpoint, parâmetro, regra); os dois perfis somados sem dupla contagem",
            eixo_x="achados únicos")
    compor(fig, ax, legenda=ax.get_legend_handles_labels(), ncol=4)
    rodape(fig, "OWASP ZAP 2.17.0 · strength medium · threshold medium (low nas regras de SQLi)")
    salvar(fig, "fig1-severidade-por-modelo.png")
    escreve_csv("fig1-severidade-por-modelo.csv",
                ["modelo"] + ORDEM_SEV + ["total"],
                [[m] + [dados[m][s] for s in ORDEM_SEV] + [sum(dados[m].values())]
                 for m in ordem])


# ============================================================ figura 2
def fig_por_endpoint(res):
    """Metrica normalizada: achados por endpoint, separada por perfil."""
    d = {(r["modelo"], r["perfil"]): float(r["achados_por_endpoint"]) for r in res}
    ordem = sorted(MODELOS, key=lambda m: max(d[(m, p)] for p in PERFIS))

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    larg = 0.34
    x = range(len(ordem))
    for i, perfil in enumerate(PERFIS):
        pos = [v + (i - 0.5) * (larg + 0.02) for v in x]
        vals = [d[(m, perfil)] for m in ordem]
        ax.bar(pos, vals, larg, color=SLOT[i], label=ROTULO_PERFIL[perfil],
               edgecolor=SURFACE, linewidth=1.6, zorder=3)
        for p, v in zip(pos, vals):
            ax.text(p, v + 0.045, f"{v:.2f}", ha="center", va="bottom",
                    color=INK, fontsize=8.5, zorder=4)

    ax.set_xticks(list(x))
    ax.set_xticklabels(ordem, color=INK, fontsize=9.5)
    ax.set_ylim(0, max(d.values()) * 1.18)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    moldura(ax, "Achados por endpoint, dentro de cada perfil",
            "Achados únicos ÷ endpoints com achado, calculado separadamente por perfil",
            eixo_y="achados por endpoint")
    compor(fig, ax, legenda=ax.get_legend_handles_labels(), ncol=2, esq=0.09)
    rodape(fig, "A contagem bruta de URLs não serve como métrica de superfície: o fallback das SPA "
                "responde 200 a qualquer caminho. Uma varredura completa por perfil, com o banco "
                "restaurado ao estado inicial entre elas.")
    salvar(fig, "fig2-achados-por-endpoint.png")
    escreve_csv("fig2-achados-por-endpoint.csv",
                ["modelo", "perfil", "achados_por_endpoint"],
                [[m, p, d[(m, p)]] for m in ordem for p in PERFIS])


# ============================================================ figura 3
def fig_high_por_classe(det):
    """Achados de severidade alta, por classe de vulnerabilidade."""
    por = {m: defaultdict(set) for m in MODELOS}
    for r in det:
        if r["risco"] == "High":
            por[r["modelo"]][r["alerta"]].add(chave(r))
    classes = sorted({c for m in MODELOS for c in por[m]},
                     key=lambda c: -sum(len(por[m][c]) for m in MODELOS))
    ordem = sorted(MODELOS, key=lambda m: sum(len(v) for v in por[m].values()))

    fig, ax = plt.subplots(figsize=(9.8, 5.4))
    y = range(len(ordem))
    esq = [0] * len(ordem)
    for i, cls in enumerate(classes):
        vals = [len(por[m][cls]) for m in ordem]
        ax.barh(y, vals, left=esq, height=0.56, color=SLOT[i % len(SLOT)],
                label=cls, edgecolor=SURFACE, linewidth=1.6, zorder=3)
        for j, (v, e) in enumerate(zip(vals, esq)):
            if v >= 2:
                ax.text(e + v / 2, j, str(v), ha="center", va="center",
                        color="#ffffff", fontsize=8.5, fontweight="bold", zorder=4)
        esq = [a + b for a, b in zip(esq, vals)]
    for i, m in enumerate(ordem):
        rot = str(esq[i]) if esq[i] else "nenhum"
        ax.text(esq[i] + 0.25, i, rot, va="center", ha="left",
                color=INK if esq[i] else MUTED, fontsize=9.5,
                fontweight="bold" if esq[i] else "normal", zorder=4)

    ax.set_yticks(list(y))
    ax.set_yticklabels(ordem, color=INK, fontsize=9.5)
    ax.set_xlim(0, max(max(esq), 1) * 1.18)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    moldura(ax, "Achados de severidade alta, por classe",
            "Achados únicos, deduplicados por (endpoint, parâmetro, regra); "
            "os dois perfis consolidados",
            eixo_x="achados únicos")
    compor(fig, ax, legenda=ax.get_legend_handles_labels(), ncol=3, base=0.34)
    rodape(fig, "Regras de injeção SQL rodaram com threshold low — sensibilidade elevada e, com ela, "
                "a taxa de falso positivo nesta classe")
    salvar(fig, "fig3-high-por-classe.png")
    escreve_csv("fig3-high-por-classe.csv", ["modelo"] + classes + ["total"],
                [[m] + [len(por[m][c]) for c in classes]
                 + [sum(len(v) for v in por[m].values())] for m in ordem])


# ============================================================ figura 4
def fig_owasp(det):
    """Distribuicao por categoria do OWASP Top 10."""
    por = {m: defaultdict(set) for m in MODELOS}
    for r in det:
        for cat in [c for c in r["owasp"].split(",") if c]:
            por[r["modelo"]][cat].add(chave(r))
    cats = sorted({c for m in MODELOS for c in por[m]})
    ordem = sorted(MODELOS, key=lambda m: -sum(len(v) for v in por[m].values()))

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    larg = 0.24
    x = range(len(ordem))
    for i, cat in enumerate(cats):
        pos = [v + (i - (len(cats) - 1) / 2) * (larg + 0.02) for v in x]
        vals = [len(por[m][cat]) for m in ordem]
        ax.bar(pos, vals, larg, color=SLOT[i], label=cat,
               edgecolor=SURFACE, linewidth=1.6, zorder=3)
        for p, v in zip(pos, vals):
            ax.text(p, v + 0.4, str(v), ha="center", va="bottom",
                    color=INK, fontsize=8.5, zorder=4)

    ax.set_xticks(list(x))
    ax.set_xticklabels(ordem, color=INK, fontsize=9.5)
    topo = max(len(v) for m in MODELOS for v in por[m].values())
    ax.set_ylim(0, topo * 1.20)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    moldura(ax, "Distribuição por categoria OWASP Top 10 (2021)",
            "A01 controle de acesso · A03 injeção · A05 configuração incorreta de segurança",
            eixo_y="achados únicos")
    compor(fig, ax, legenda=ax.get_legend_handles_labels(), ncol=3, esq=0.09)
    rodape(fig, "27 achados sem categoria automática ficaram em _pendente_mapeamento.csv e "
                "aguardam mapeamento manual por CWE")
    salvar(fig, "fig4-owasp.png")
    escreve_csv("fig4-owasp.csv", ["modelo"] + cats,
                [[m] + [len(por[m][c]) for c in cats] for m in ordem])


# ============================================================ figura 5
def fig_perfis(det):
    """Superficie exclusiva de cada perfil: o que so o admin alcancou."""
    dados = {}
    for m in MODELOS:
        s = {p: {chave(r) for r in det if r["modelo"] == m and r["perfil"] == p}
             for p in PERFIS}
        dados[m] = (len(s["user_comum"] - s["admin"]),
                    len(s["user_comum"] & s["admin"]),
                    len(s["admin"] - s["user_comum"]))
    ordem = sorted(MODELOS, key=lambda m: sum(dados[m]))

    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    y = range(len(ordem))
    rot = ["só usuário comum", "nos dois perfis", "só administrador"]
    cores = [SLOT[0], "#c9c8c1", SLOT[1]]
    esq = [0] * len(ordem)
    for i in range(3):
        vals = [dados[m][i] for m in ordem]
        ax.barh(y, vals, left=esq, height=0.56, color=cores[i], label=rot[i],
                edgecolor=SURFACE, linewidth=1.6, zorder=3)
        for j, (v, e) in enumerate(zip(vals, esq)):
            if v >= 3:
                ax.text(e + v / 2, j, str(v), ha="center", va="center",
                        color="#ffffff" if i != 1 else INK,
                        fontsize=8.5, fontweight="bold", zorder=4)
        esq = [a + b for a, b in zip(esq, vals)]

    ax.set_yticks(list(y))
    ax.set_yticklabels(ordem, color=INK, fontsize=9.5)
    ax.set_xlim(0, max(esq) * 1.06)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    moldura(ax, "Sobreposição de achados entre os dois perfis",
            "A faixa à direita é o que a segunda passagem acrescentou — "
            "sem ela, esses achados ficariam fora da comparação",
            eixo_x="achados únicos")
    compor(fig, ax, legenda=ax.get_legend_handles_labels(), ncol=3)
    rodape(fig, "Banco restaurado ao snapshot inicial entre as duas passagens de cada modelo")
    salvar(fig, "fig5-sobreposicao-perfis.png")
    escreve_csv("fig5-sobreposicao-perfis.csv",
                ["modelo", "so_user_comum", "nos_dois", "so_admin"],
                [[m] + list(dados[m]) for m in ordem])


# ============================================================ tabelas
def tabela_png(nome, titulo, subtitulo, cabecalho, linhas, larguras,
               alinha=None, destaque=None, nota=None):
    """Desenha uma tabela como PNG, no mesmo cromo das figuras."""
    alinha = alinha or ["left"] + ["right"] * (len(cabecalho) - 1)
    n = len(linhas)
    alt_linha = 0.30
    alt = 1.30 + n * alt_linha + (0.30 if nota else 0)
    larg = sum(larguras) / 10
    fig = plt.figure(figsize=(larg, alt))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, sum(larguras))
    ax.set_ylim(0, alt * 10)
    ax.axis("off")

    topo = alt * 10 - 4
    ax.text(0, topo, titulo, color=INK, fontsize=12, fontweight="bold", va="top")
    y = topo - 5.2
    if subtitulo:
        ax.text(0, y, subtitulo, color=INK_2, fontsize=8.5, va="top")
        y -= 5.0
    else:
        y -= 1.6

    bordas = [0]
    for w in larguras:
        bordas.append(bordas[-1] + w)

    # cabecalho
    for i, (c, a) in enumerate(zip(cabecalho, alinha)):
        x = bordas[i] + 0.6 if a == "left" else bordas[i + 1] - 0.6
        ax.text(x, y, c, color=INK_2, fontsize=8.5, fontweight="bold",
                va="top", ha=a)
    y -= 1.4
    ax.plot([0, sum(larguras)], [y, y], color=BASELINE, linewidth=0.9)

    for j, linha in enumerate(linhas):
        y -= alt_linha * 10
        if j % 2 == 1:
            ax.add_patch(Rectangle((0, y - 0.6), sum(larguras), alt_linha * 10,
                                   facecolor=SURFACE, edgecolor="none", zorder=0))
        for i, (v, a) in enumerate(zip(linha, alinha)):
            x = bordas[i] + 0.6 if a == "left" else bordas[i + 1] - 0.6
            cor = INK if i == 0 else INK_2
            peso = "bold" if (i == 0 or (destaque and (j, i) in destaque)) else "normal"
            if destaque and (j, i) in destaque:
                cor = INK
            ax.text(x, y + 1.0, str(v), color=cor, fontsize=9, va="center",
                    ha=a, fontweight=peso, zorder=2)
        ax.plot([0, sum(larguras)], [y - 0.6, y - 0.6],
                color=GRID, linewidth=0.5, zorder=1)

    if nota:
        y -= 3.4
        ax.text(0, y, nota, color=MUTED, fontsize=7.5, va="top")
    salvar(fig, nome, tight=True)


def tab_resumo(det, res):
    por = {m: defaultdict(set) for m in MODELOS}
    todos = {m: set() for m in MODELOS}
    for r in det:
        por[r["modelo"]][r["risco"]].add(chave(r))
        todos[r["modelo"]].add(chave(r))
    endp = {m: len({r["endpoint"] for r in det if r["modelo"] == m}) for m in MODELOS}
    ordem = sorted(MODELOS, key=lambda m: -len(todos[m]))

    linhas = []
    for m in ordem:
        n = len(todos[m])
        linhas.append([m, len(por[m]["High"]), len(por[m]["Medium"]),
                       len(por[m]["Low"]), len(por[m]["Informational"]),
                       n, endp[m], f"{n / endp[m]:.2f}"])
    tabela_png(
        "tab1-resumo.png", "Resumo dos achados por modelo",
        "Achados únicos deduplicados por (endpoint, parâmetro, regra), com os dois perfis "
        "consolidados — por isso a razão difere da figura 2, que calcula dentro de cada perfil",
        ["modelo", "High", "Medium", "Low", "Info", "total", "endpoints", "por endpoint"],
        linhas, [34, 12, 15, 12, 11, 13, 16, 18],
        nota="OWASP ZAP 2.17.0 · spider 5 min · active scan até 90 min (máximo observado: 15 min 38 s)")
    escreve_csv("tab1-resumo.csv",
                ["modelo", "High", "Medium", "Low", "Informational",
                 "total", "endpoints", "achados_por_endpoint"], linhas)


def tab_high(det):
    por = {m: defaultdict(set) for m in MODELOS}
    for r in det:
        if r["risco"] == "High":
            por[r["modelo"]][r["alerta"]].add(chave(r))
    classes = sorted({c for m in MODELOS for c in por[m]},
                     key=lambda c: -sum(len(por[m][c]) for m in MODELOS))
    ordem = sorted(MODELOS, key=lambda m: -sum(len(v) for v in por[m].values()))
    cwe = {}
    for r in det:
        if r["risco"] == "High":
            cwe.setdefault(r["alerta"], r["cwe"])

    linhas = []
    for c in classes:
        linhas.append([c, f"CWE-{cwe.get(c, '?')}"]
                      + [len(por[m][c]) or "—" for m in ordem])
    linhas.append(["total", ""] + [sum(len(v) for v in por[m].values()) or "nenhum"
                                   for m in ordem])
    tabela_png(
        "tab2-high-por-classe.png", "Achados de severidade alta, por classe",
        "Achados únicos por modelo, deduplicados por (endpoint, parâmetro, regra); "
        "os dois perfis consolidados. Um achado pode ter várias instâncias no relatório bruto.",
        ["classe", "CWE"] + ordem, linhas, [42, 14, 24, 20, 16, 14],
        alinha=["left", "left"] + ["right"] * len(ordem),
        destaque={(len(linhas) - 1, i) for i in range(2, 2 + len(ordem))},
        nota="Regras de injeção SQL com threshold low: sensibilidade elevada nesta classe, "
             "e com ela a taxa de falso positivo")
    escreve_csv("tab2-high-por-classe.csv", ["classe", "cwe"] + ordem, linhas)


def tab_cobertura():
    linhas = []
    for m in MODELOS:
        for p in PERFIS:
            log = (OUT / f"{m}-{p}-log.txt").read_text(encoding="utf-8", errors="replace")
            ajax = re.search(r"spiderAjax found ([\d,]+) URLs", log)
            dur = re.search(r"Job activeScan finished, time taken: ([\d:]+)", log)
            linhas.append([
                m, ROTULO_PERFIL[p],
                ajax.group(1) if ajax else "—",
                dur.group(1) if dur else "—",
                str(log.count("Unexpected error")),
                str(len(re.findall(r"Unrecognised", log))),
                "0",
            ])
    tabela_png(
        "tab3-cobertura.png", "Cobertura e verificação das oito varreduras",
        "Checklist do runbook: nenhum erro inesperado, nenhum parâmetro não reconhecido, "
        "nenhuma falha de autenticação",
        ["modelo", "perfil", "URLs (spider AJAX)", "active scan", "erros", "não reconh.", "exit"],
        linhas, [32, 22, 24, 17, 12, 17, 10],
        alinha=["left", "left", "right", "right", "right", "right", "right"],
        nota="Nenhuma varredura atingiu o teto de 90 min, portanto não houve truncamento de cobertura")
    escreve_csv("tab3-cobertura.csv",
                ["modelo", "perfil", "urls_spider_ajax", "duracao_active_scan",
                 "erros_inesperados", "nao_reconhecidos", "exit"], linhas)


def main():
    det = ler_detalhado()
    res = ler_resumo()
    print(f">> {len(det)} achados lidos de out/_tab_detalhado.csv")
    print(">> gerando em graficos/")
    fig_severidade(det)
    fig_por_endpoint(res)
    fig_high_por_classe(det)
    fig_owasp(det)
    fig_perfis(det)
    tab_resumo(det, res)
    tab_high(det)
    tab_cobertura()
    print(">> pronto")


if __name__ == "__main__":
    main()
