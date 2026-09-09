#!/usr/bin/env python3
"""
02-agregar.py - Consolida os relatorios JSON do ZAP em tabelas CSV
prontas para as Secoes 4.2, 4.3 e 4.4 do artigo.

Deduplica por (endpoint normalizado, parametro, tipo de alerta),
conforme a Subsecao 3.3.2, e mapeia para OWASP Top 10 e CWE.

Uso:  python3 02-agregar.py [diretorio_out]
Sem dependencias externas (apenas biblioteca padrao).
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

RISCO = {"0": "Informational", "1": "Low", "2": "Medium", "3": "High"}
CONF = {"0": "False Positive", "1": "Low", "2": "Medium",
        "3": "High", "4": "Confirmed"}

# Segmentos que sao identificadores de recurso viram placeholder, senao
# /orders/1 e /orders/2 contariam como dois achados distintos.
RE_NUM = re.compile(r"^\d+$")
RE_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                     r"[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
RE_HASH = re.compile(r"^[0-9a-f]{16,}$", re.I)


def normalizar_uri(uri: str) -> str:
    """Remove query string e substitui IDs por {id}."""
    partes = urlsplit(uri)
    segs = []
    for s in partes.path.split("/"):
        if RE_NUM.match(s) or RE_UUID.match(s) or RE_HASH.match(s):
            segs.append("{id}")
        else:
            segs.append(s)
    caminho = "/".join(segs) or "/"
    return f"{partes.scheme}://{partes.netloc}{caminho}"


def nomes_das_tags(tags) -> list:
    """Normaliza o campo `tags` do relatorio para uma lista de nomes.

    O template traditional-json-plus mudou de formato: ate versoes anteriores
    emitia um objeto {nome: link}; o ZAP 2.17.0 emite uma lista de objetos
    [{"tag": nome, "link": url}]. Aceita os dois para que relatorios antigos
    e novos agreguem igual.
    """
    if not tags:
        return []
    if isinstance(tags, dict):
        return [str(k) for k in tags]
    nomes = []
    for t in tags:
        if isinstance(t, dict):
            n = t.get("tag")
            if n:
                nomes.append(str(n))
        else:
            nomes.append(str(t))
    return nomes


def tag_owasp(tags) -> str:
    """Extrai a categoria OWASP Top 10 das alert tags do ZAP."""
    if not tags:
        return ""
    cats = sorted({k for k in nomes_das_tags(tags) if k.startswith("OWASP_")
                   and "_A" in k})
    # Prefere a lista mais recente disponivel
    for prefixo in ("OWASP_2021_", "OWASP_2017_"):
        achadas = [c for c in cats if c.startswith(prefixo)]
        if achadas:
            return ",".join(a.replace(prefixo, "") for a in achadas)
    return ",".join(cats)


def carregar(caminho: Path):
    """Le um relatorio traditional-json[-plus] e devolve achados unicos."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    vistos = {}
    brutos = 0
    for site in dados.get("site", []):
        for alerta in site.get("alerts", []):
            tags = alerta.get("tags") or {}
            base = {
                "pluginid": alerta.get("pluginid", ""),
                "alerta": alerta.get("alert") or alerta.get("name", ""),
                "risco": RISCO.get(str(alerta.get("riskcode", "")), "?"),
                "confianca": CONF.get(str(alerta.get("confidence", "")), "?"),
                "cwe": alerta.get("cweid", ""),
                "wasc": alerta.get("wascid", ""),
                "owasp": tag_owasp(tags),
            }
            for inst in alerta.get("instances", []) or [{}]:
                brutos += 1
                uri = normalizar_uri(inst.get("uri", site.get("@name", "")))
                param = (inst.get("param") or "").strip()
                chave = (uri, param, base["pluginid"])
                if chave in vistos:
                    vistos[chave]["ocorrencias"] += 1
                    continue
                reg = dict(base)
                reg.update({
                    "endpoint": uri,
                    "parametro": param,
                    "metodo": inst.get("method", ""),
                    "evidencia": (inst.get("evidence") or "")[:120],
                    "ocorrencias": 1,
                })
                vistos[chave] = reg
    return list(vistos.values()), brutos


def escrever(caminho: Path, colunas, linhas):
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)
    print(f"   -> {caminho.name} ({len(linhas)} linhas)")


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    arquivos = sorted(p for p in out.glob("*.json")
                      if not p.name.startswith("_"))
    if not arquivos:
        sys.exit(f"Nenhum .json encontrado em {out}/. Rode 01-varrer.sh antes.")

    detalhado, resumo, owasp_pivot = [], [], defaultdict(Counter)
    cats_owasp = set()
    PERFIS_VALIDOS = {"user_comum", "admin"}

    for arq in arquivos:
        # Arquivos saem como "<modelo>-<perfil>.json". Como o nome do
        # modelo tem hifens (deepseek-mini-v4), corta pelo ULTIMO hifen
        # e so aceita se o sufixo for um perfil conhecido.
        base = arq.stem
        modelo, perfil = base, ""
        if "-" in base:
            cand_m, cand_p = base.rsplit("-", 1)
            if cand_p in PERFIS_VALIDOS:
                modelo, perfil = cand_m, cand_p
        achados, brutos = carregar(arq)
        rotulo = f"{modelo}/{perfil}" if perfil else modelo
        print(f">> {rotulo}: {brutos} instancias -> {len(achados)} unicos")

        endpoints = {a["endpoint"] for a in achados}
        c_risco = Counter(a["risco"] for a in achados)
        c_conf = Counter(a["confianca"] for a in achados)

        for a in achados:
            a["modelo"] = modelo
            a["perfil"] = perfil
            detalhado.append(a)
            for cat in filter(None, a["owasp"].split(",")):
                owasp_pivot[rotulo][cat] += 1
                cats_owasp.add(cat)

        n = len(achados)
        ne = len(endpoints) or 1
        resumo.append({
            "modelo": modelo,
            "perfil": perfil,
            "instancias_brutas": brutos,
            "achados_unicos": n,
            "endpoints_com_achado": len(endpoints),
            "achados_por_endpoint": round(n / ne, 2),
            "High": c_risco["High"], "Medium": c_risco["Medium"],
            "Low": c_risco["Low"], "Informational": c_risco["Informational"],
            "pct_High_Medium": round(
                100 * (c_risco["High"] + c_risco["Medium"]) / n, 1) if n else 0,
            "conf_High": c_conf["High"] + c_conf["Confirmed"],
            "conf_Medium": c_conf["Medium"],
            "conf_Low": c_conf["Low"],
        })

    print("\n>> Gerando tabelas:")
    escrever(out / "_tab_resumo.csv", list(resumo[0].keys()), resumo)

    escrever(out / "_tab_detalhado.csv",
             ["modelo", "perfil", "risco", "confianca", "alerta", "owasp", "cwe",
              "metodo", "endpoint", "parametro", "ocorrencias",
              "pluginid", "wasc", "evidencia"],
             sorted(detalhado,
                    key=lambda r: (r["modelo"], r.get("perfil", ""),
                                   -["Informational", "Low", "Medium",
                                     "High"].index(r["risco"])
                                   if r["risco"] in RISCO.values() else 0,
                                   r["alerta"])))

    cols = ["modelo_perfil"] + sorted(cats_owasp)
    escrever(out / "_tab_owasp.csv", cols,
             [{"modelo_perfil": m,
               **{c: owasp_pivot[m].get(c, 0) for c in cols[1:]}}
              for m in sorted(owasp_pivot)])

    # Achados exclusivos do perfil admin: rotas que a varredura como
    # usuario comum nunca alcancaria.
    por_modelo = defaultdict(lambda: defaultdict(set))
    for a in detalhado:
        if a.get("perfil"):
            por_modelo[a["modelo"]][a["perfil"]].add(
                (a["endpoint"], a["parametro"], a["pluginid"]))
    linhas_excl = []
    for m, perfis in sorted(por_modelo.items()):
        so_admin = perfis.get("admin", set()) - perfis.get("user_comum", set())
        so_user = perfis.get("user_comum", set()) - perfis.get("admin", set())
        linhas_excl.append({
            "modelo": m,
            "so_admin": len(so_admin),
            "so_user_comum": len(so_user),
            "em_ambos": len(perfis.get("admin", set())
                            & perfis.get("user_comum", set())),
        })
    if linhas_excl:
        escrever(out / "_tab_por_perfil.csv",
                 ["modelo", "so_admin", "so_user_comum", "em_ambos"],
                 linhas_excl)

    sem_tag = [a for a in detalhado if not a["owasp"]]
    if sem_tag:
        escrever(out / "_pendente_mapeamento.csv",
                 ["modelo", "perfil", "alerta", "cwe", "risco", "endpoint"],
                 sem_tag)
        print(f"\n!! {len(sem_tag)} achados sem tag OWASP automatica.")
        print("   Mapeie-os manualmente a partir do CWE e documente a regra")
        print("   de mapeamento no artigo (revisor vai perguntar).")

    print("\nPronto. Use _tab_resumo.csv na Secao 4.2, _tab_owasp.csv na 4.3")
    print("e _tab_detalhado.csv para escolher os achados da Secao 4.4.")


if __name__ == "__main__":
    main()
