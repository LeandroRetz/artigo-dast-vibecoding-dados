#!/usr/bin/env python3
"""
07-fase4.py — Fase 4 do runbook: achados complementares fora do escopo DAST.

Roda contra a aplicacao ATUALMENTE de pe em localhost:5173, com o banco
restaurado ao snapshot da varredura (04-preparar.sh <modelo> restaurar).

  ./07-fase4.py <modelo>

Produz/apende:
  out/_idor.csv    modelo,endpoint,id_alvo,dono_do_recurso,usuario_requisitante,status,violacao
  out/_sessao.csv  atributos de cookie, algoritmo, expiracao, invalidacao no logout

O cookie de sessao e capturado do cabecalho Set-Cookie e reenviado CRU em
cada requisicao. Nao se usa cookiejar: tres das quatro aplicacoes marcam o
cookie como Secure sob NODE_ENV=production, e um cookie Secure nao e
retransmitido sobre HTTP — o mesmo obstaculo descrito na Secao 4.2 da
metodologia. Sem isso, toda requisicao sairia anonima e devolveria 401,
o que se confundiria com controle de acesso correto.

Nao altera nenhuma aplicacao. So le e requisita.
"""
import base64, csv, json, os, re, sys, urllib.request, urllib.error

BASE = "http://localhost:5173"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
USER = ("user@test.com", "Test1234!")
ADMIN = ("admin@test.com", "Test1234!")
NOMES_COOKIE = ("auth_token", "token", "access_token")


def req(metodo, caminho, corpo=None, cookie=None):
    """Requisicao crua. Devolve (status, texto, headers)."""
    dados = json.dumps(corpo).encode() if corpo is not None else None
    r = urllib.request.Request(BASE + caminho, data=dados, method=metodo)
    if dados:
        r.add_header("Content-Type", "application/json")
    if cookie:
        r.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(r, timeout=25) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), e.headers
    except Exception as e:
        return -1, str(e), None


def autenticar(cred):
    """Login. Devolve (cookie_cru, atributos_do_set_cookie)."""
    st, _, hdrs = req("POST", "/api/auth/login",
                      {"email": cred[0], "password": cred[1]})
    if st != 200 or hdrs is None:
        raise SystemExit(f"!! login {cred[0]} devolveu {st}")
    for bruto in hdrs.get_all("Set-Cookie") or []:
        par = bruto.split(";")[0].strip()
        nome = par.split("=", 1)[0]
        if nome in NOMES_COOKIE:
            atributos = {}
            for pedaco in bruto.split(";")[1:]:
                pedaco = pedaco.strip()
                if "=" in pedaco:
                    k, v = pedaco.split("=", 1)
                    atributos[k.strip().lower()] = v.strip()
                else:
                    atributos[pedaco.lower()] = True
            return par, nome, par.split("=", 1)[1], atributos
    raise SystemExit(f"!! nenhum cookie de sessao no login de {cred[0]}")


def json_ou_none(txt):
    try:
        return json.loads(txt)
    except Exception:
        return None


def primeiro_id(payload):
    if isinstance(payload, dict):
        # o "id" do proprio objeto vem ANTES de descer para colecoes aninhadas:
        # um pedido traz "items", e descer primeiro devolveria o id do item de
        # pedido em vez do id do pedido.
        if "id" in payload:
            return payload["id"]
        for k in ("data", "orders", "items", "results", "products", "reviews"):
            if k in payload:
                achado = primeiro_id(payload[k])
                if achado is not None:
                    return achado
    if isinstance(payload, list):
        for it in payload:
            achado = primeiro_id(it)
            if achado is not None:
                return achado
    return None


def busca_id_carrinho(payload):
    if isinstance(payload, dict):
        if "id" in payload and any(k in payload for k in
                                   ("quantity", "product", "product_id", "productId")):
            return payload["id"]
        for v in payload.values():
            achado = busca_id_carrinho(v)
            if achado is not None:
                return achado
    if isinstance(payload, list):
        for it in payload:
            achado = busca_id_carrinho(it)
            if achado is not None:
                return achado
    return None


def busca_review_do_admin(payload):
    if isinstance(payload, dict):
        if "rating" in payload and "id" in payload and \
           "Admin" in json.dumps(payload, ensure_ascii=False):
            return payload["id"]
        for v in payload.values():
            achado = busca_review_do_admin(v)
            if achado is not None:
                return achado
    if isinstance(payload, list):
        for it in payload:
            achado = busca_review_do_admin(it)
            if achado is not None:
                return achado
    return None


def id_do_seed(modelo, recurso):
    caminho = os.path.join(OUT, f"seed-{modelo}.md")
    if not os.path.exists(caminho):
        return None
    m = re.search(r"```json\s*(\{.*?\})\s*```",
                  open(caminho, encoding="utf-8").read(), re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))["admin@test.com"].get(recurso)
    except Exception:
        return None


def decodifica_jwt(token):
    try:
        h, p, _ = token.split(".")
        pad = lambda s: s + "=" * (-len(s) % 4)
        return (json.loads(base64.urlsafe_b64decode(pad(h))),
                json.loads(base64.urlsafe_b64decode(pad(p))))
    except Exception:
        return {}, {}


def appende(nome, cabecalho, linhas):
    caminho = os.path.join(OUT, nome)
    novo = not os.path.exists(caminho)
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(cabecalho)
        w.writerows(linhas)
    print(f"   -> {len(linhas)} linha(s) em out/{nome}")


def main():
    modelo = sys.argv[1]
    ck_u, nome_ck, valor_ck, attrs = autenticar(USER)
    ck_a, _, _, _ = autenticar(ADMIN)

    # GUARDA: sem sessao viva, todo 401 abaixo seria lido como autorizacao
    # correta quando na verdade e requisicao anonima. Aborta antes disso.
    for rotulo, ck in (("user", ck_u), ("admin", ck_a)):
        st, _, _ = req("GET", "/api/users/me", cookie=ck)
        if st != 200:
            raise SystemExit(f"!! sessao de {rotulo} nao vale: /api/users/me -> {st}")
    st_adm, _, _ = req("GET", "/api/admin/orders", cookie=ck_a)
    if st_adm != 200:
        raise SystemExit(f"!! admin nao alcanca /api/admin/orders -> {st_adm}")
    print(f">> [{modelo}] sessoes validas nos dois perfis (cookie {nome_ck})")

    # ---- alvos: recursos pertencentes ao ADMIN ----
    _, txt, _ = req("GET", "/api/orders", cookie=ck_a)
    pedido_admin = primeiro_id(json_ou_none(txt)) or id_do_seed(modelo, "pedido")

    _, txt, _ = req("GET", "/api/products")
    prod = primeiro_id(json_ou_none(txt))
    for campo in ("product_id", "productId"):
        st, _, _ = req("POST", "/api/cart/items",
                       {campo: prod, "quantity": 1}, cookie=ck_a)
        if st in (200, 201):
            break
    _, txt, _ = req("GET", "/api/cart", cookie=ck_a)
    item_admin = busca_id_carrinho(json_ou_none(txt))

    aval_admin = None
    for pid in (prod, 1, 9, 10):
        if pid is None:
            continue
        st, txt, _ = req("GET", f"/api/products/{pid}", cookie=ck_u)
        if st == 200:
            aval_admin = busca_review_do_admin(json_ou_none(txt))
            if aval_admin is not None:
                break
    if aval_admin is None:
        aval_admin = id_do_seed(modelo, "avaliacao")
    print(f"   alvos do admin: pedido={pedido_admin} "
          f"carrinho={item_admin} avaliacao={aval_admin}")

    # ---- IDOR: usuario comum requisitando recurso do admin ----
    testes = []
    if pedido_admin is not None:
        testes.append(("GET /api/orders/{id}", pedido_admin, "GET",
                       f"/api/orders/{pedido_admin}", None))
    if aval_admin is not None:
        testes.append(("PUT /api/reviews/{id}", aval_admin, "PUT",
                       f"/api/reviews/{aval_admin}",
                       {"rating": 1, "comment": "idor probe"}))
    if item_admin is not None:
        testes.append(("DELETE /api/cart/items/{id}", item_admin, "DELETE",
                       f"/api/cart/items/{item_admin}", None))
    testes.append(("GET /api/admin/orders", "-", "GET", "/api/admin/orders", None))
    if aval_admin is not None:
        testes.append(("DELETE /api/reviews/{id}", aval_admin, "DELETE",
                       f"/api/reviews/{aval_admin}", None))

    linhas = []
    for rotulo, alvo, metodo, caminho, corpo in testes:
        st, _, _ = req(metodo, caminho, corpo, cookie=ck_u)
        violacao = "sim" if st in (200, 201, 204) else "nao"
        print(f"   {rotulo:30s} alvo={str(alvo)[:14]:14s} -> {st}  violacao={violacao}")
        linhas.append([modelo, rotulo, alvo, "admin@test.com",
                       "user@test.com", st, violacao])
    appende("_idor.csv",
            ["modelo", "endpoint", "id_alvo", "dono_do_recurso",
             "usuario_requisitante", "status", "violacao"], linhas)

    # ---- gerenciamento de sessao ----
    cab, car = decodifica_jwt(valor_ck)
    exp, iat = car.get("exp"), car.get("iat")
    if exp and iat:
        dur = exp - iat
        expiracao = f"{dur // 86400} d" if dur >= 86400 else f"{dur // 3600} h"
    else:
        expiracao = "ausente" if not exp else str(exp)

    ck_novo, _, _, _ = autenticar(USER)
    req("POST", "/api/auth/logout", cookie=ck_novo)
    st_reuso, _, _ = req("GET", "/api/users/me", cookie=ck_novo)
    invalidado = "nao" if st_reuso == 200 else "sim"

    linha = [modelo, nome_ck,
             "cookie httpOnly (sem localStorage/sessionStorage no front)",
             "sim" if "httponly" in attrs else "nao",
             "sim" if "secure" in attrs else "nao",
             attrs.get("samesite", "-"),
             cab.get("alg", "-"), expiracao, invalidado, st_reuso]
    print("   cookie=%s httponly=%s secure=%s samesite=%s alg=%s exp=%s "
          "reuso_pos_logout=%s (invalidado=%s)"
          % (nome_ck, linha[3], linha[4], linha[5], linha[6], expiracao,
             st_reuso, invalidado))
    appende("_sessao.csv",
            ["modelo", "cookie", "armazenamento", "httponly", "secure",
             "samesite", "algoritmo", "expiracao_token",
             "invalidado_no_logout", "status_reuso_pos_logout"], [linha])


if __name__ == "__main__":
    main()
