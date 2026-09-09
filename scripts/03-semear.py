#!/usr/bin/env python3
"""
03-semear.py - Cria os usuarios de teste e os dados por usuario exigidos
pela Fase 2.2 do runbook, usando SOMENTE a API publica da aplicacao.

Nao altera codigo da aplicacao. As variantes de nome de campo existem
porque as quatro implementacoes divergem no contrato (product_id vs
productId etc.); o script tenta cada variante e registra a que funcionou.

Uso: python3 03-semear.py <modelo> [--base http://localhost:5173]
Saida: out/seed-<modelo>.md
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request, urllib.error, http.cookiejar, datetime

SENHA = "Test1234!"
CONTAS = [("user@test.com", "Usuario Comum"), ("admin@test.com", "Admin Teste")]


class PoliticaLocal(http.cookiejar.DefaultCookiePolicy):
    """Aceita e devolve cookies marcados Secure sobre HTTP em localhost.

    Tres das quatro aplicacoes marcam o cookie de sessao como Secure quando
    NODE_ENV=production. O http.cookiejar padrao se recusa a envia-lo sobre
    http://, entao todo request autenticado voltaria 401 e o seed criaria
    nada -- sem erro visivel, so 401 silencioso.

    Navegadores e o proprio ZAP tratam localhost como origem confiavel e
    enviam o cookie. Esta politica reproduz esse comportamento. Nao altera
    nada na aplicacao: o atributo Secure continua sendo emitido por ela e
    continua sendo medido pelo ZAP.
    """

    def return_ok_secure(self, cookie, request):
        if not cookie.secure:
            return True
        maquina = urllib.parse.urlparse(request.get_full_url()).hostname or ""
        return maquina in ("localhost", "127.0.0.1", "::1") or super().return_ok_secure(cookie, request)


class Cliente:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar(policy=PoliticaLocal())
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def req(self, metodo, caminho, corpo=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        r = urllib.request.Request(self.base + caminho, data=dados, method=metodo)
        if dados:
            r.add_header("Content-Type", "application/json")
        try:
            with self.op.open(r, timeout=30) as resp:
                txt = resp.read().decode("utf8", "replace")
                try:
                    return resp.status, json.loads(txt)
                except json.JSONDecodeError:
                    return resp.status, txt
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf8", "replace")
            try:
                return e.code, json.loads(txt)
            except json.JSONDecodeError:
                return e.code, txt
        except Exception as e:
            return 0, str(e)


def chave_stripe():
    """Le a STRIPE_SECRET_KEY do .env da aplicacao sob teste."""
    caminho = os.environ.get("STRIPE_ENV_FILE", "")
    if caminho and os.path.exists(caminho):
        for linha in open(caminho):
            if linha.startswith("STRIPE_SECRET_KEY="):
                return linha.split("=", 1)[1].strip()
    return os.environ.get("STRIPE_SECRET_KEY", "")


def pagar_stripe(pi_id):
    """Confirma o PaymentIntent no Stripe em modo TESTE com o cartao pm_card_visa.

    Isso deixa o pedido em estado `paid` pela via normal da aplicacao, que e o
    que libera a criacao de avaliacoes (varias implementacoes exigem compra
    paga). Nenhuma cobranca real acontece: a chave e sk_test_.
    """
    sk = chave_stripe()
    if not sk.startswith("sk_test_"):
        return 0, "sem chave de teste do Stripe; pedido fica pendente"
    dados = urllib.parse.urlencode({"payment_method": "pm_card_visa",
                                    "return_url": "http://localhost:5173/"}).encode()
    r = urllib.request.Request(f"https://api.stripe.com/v1/payment_intents/{pi_id}/confirm",
                               data=dados, method="POST")
    import base64
    r.add_header("Authorization", "Basic " + base64.b64encode((sk + ":").encode()).decode())
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body.get("status", "?")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf8", "replace")[:200]
    except Exception as e:
        return 0, str(e)


def cava(obj, *chaves):
    """Procura a primeira chave presente, recursivamente, e devolve o valor."""
    if isinstance(obj, dict):
        for k in chaves:
            if k in obj and obj[k] is not None:
                return obj[k]
        for v in obj.values():
            achado = cava(v, *chaves)
            if achado is not None:
                return achado
    elif isinstance(obj, list):
        for v in obj:
            achado = cava(v, *chaves)
            if achado is not None:
                return achado
    return None


def tentar(cli, metodo, caminhos, corpos, rotulo, log):
    """Tenta combinacoes de rota x corpo ate uma dar 2xx."""
    for caminho in caminhos:
        for corpo in corpos:
            st, body = cli.req(metodo, caminho, corpo)
            if 200 <= st < 300:
                log.append(f"  OK   {metodo} {caminho} {json.dumps(corpo, ensure_ascii=False) if corpo else ''} -> {st}")
                return st, body, caminho, corpo
            log.append(f"  --   {metodo} {caminho} {json.dumps(corpo, ensure_ascii=False) if corpo else ''} -> {st}")
    log.append(f"  FALHA: {rotulo} nao criado")
    return None, None, None, None


def semear_usuario(base, email, nome, log):
    cli = Cliente(base)
    ids = {}

    st, body = cli.req("POST", "/api/auth/register",
                       {"email": email, "password": SENHA, "name": nome})
    log.append(f"  register {email} -> {st}")
    st, body = cli.req("POST", "/api/auth/login", {"email": email, "password": SENHA})
    log.append(f"  login {email} -> {st}")
    if not (200 <= st < 300):
        log.append(f"  FALHA: login de {email} nao funcionou; abortando seed deste usuario")
        return ids

    st, prods = cli.req("GET", "/api/products")
    pid = cava(prods, "id")
    if pid is None:
        log.append("  FALHA: nenhum produto listado em /api/products")
        return ids
    ids["produto_usado"] = pid
    log.append(f"  produto alvo: {pid}")

    # --- carrinho ---
    _, body, *_ = tentar(cli, "POST",
        ["/api/cart/items", "/api/cart"],
        [{"product_id": pid, "quantity": 2}, {"productId": pid, "quantity": 2}],
        "item de carrinho", log)
    if body is not None:
        ids["carrinho"] = "criado"

    # --- pedido (checkout -> pagamento real em modo teste -> confirmacao) ---
    # Ambas as grafias de CEP vao juntas: as quatro implementacoes divergem
    # entre postal_code e postalCode, e as chaves extras sao ignoradas.
    # Todas as grafias vao juntas: as quatro implementacoes divergem no nome
    # dos campos de endereco (line1 vs street, postal_code vs postalCode vs zip)
    # e cada uma ignora as chaves que nao conhece.
    endereco = {"name": nome, "phone": "51999990000",
                "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100",
                "city": "Porto Alegre", "state": "RS", "postal_code": "90000000",
                "postalCode": "90000000", "zip": "90000000", "country": "BR"}
    _, chk, *_ = tentar(cli, "POST", ["/api/checkout"],
        [{"address": endereco}, {"shipping": endereco},
         {"shipping_address": endereco}, {"shippingAddress": endereco}, {}],
        "checkout", log)

    pi_id = None
    if chk:
        segredo = cava(chk, "clientSecret", "client_secret")
        if isinstance(segredo, str) and "_secret_" in segredo:
            pi_id = segredo.split("_secret_")[0]
        if not pi_id:
            cand = cava(chk, "paymentIntentId", "payment_intent_id")
            if isinstance(cand, str) and cand.startswith("pi_"):
                pi_id = cand
    oid = cava(chk, "orderId", "order_id", "id") if chk else None
    if isinstance(oid, str) and oid.startswith("pi_"):
        oid = None
    if pi_id:
        log.append(f"  payment_intent={pi_id}  order={oid}")
        st_pg, msg = pagar_stripe(pi_id)
        log.append(f"  stripe confirm -> {st_pg} {msg}")

    _, ped, *_ = tentar(cli, "POST", ["/api/orders"],
        [{"orderId": oid, "paymentIntentId": pi_id},
         {"order_id": oid, "payment_intent_id": pi_id},
         {"payment_intent_id": pi_id, "address": endereco},
         {"paymentIntentId": pi_id, "address": endereco},
         {"payment_intent_id": pi_id, "orderId": oid, "address": endereco},
         {"orderId": oid}, {"order_id": oid},
         {"paymentIntentId": pi_id}, {"address": endereco}, {}],
        "pedido", log)
    oid = cava(ped, "id") if ped else oid
    if oid:
        ids["pedido"] = oid
        log.append(f"  pedido id={oid}")

    # --- avaliacao ---
    _, av, *_ = tentar(cli, "POST",
        [f"/api/products/{pid}/reviews", "/api/reviews"],
        [{"rating": 5, "comment": f"seed dast {nome}"},
         {"rating": 5, "comment": f"seed dast {nome}", "product_id": pid},
         {"rating": 5, "comment": f"seed dast {nome}", "productId": pid}],
        "avaliacao", log)
    rid = cava(av, "id") if av else None
    if rid:
        ids["avaliacao"] = rid
        log.append(f"  avaliacao id={rid}")

    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modelo")
    ap.add_argument("--base", default="http://localhost:5173")
    a = ap.parse_args()

    linhas = [f"# Seed DAST - {a.modelo}", "",
              f"Gerado em: {datetime.datetime.now().isoformat(timespec='seconds')}",
              f"Base: {a.base}", "",
              "Usuarios criados via `POST /api/auth/register` (senha `Test1234!`).",
              "A promocao de `admin@test.com` para role admin e feita por SQL,",
              "fora deste script, porque nenhuma das aplicacoes expoe rota para isso.",
              ""]
    todos = {}
    for email, nome in CONTAS:
        log = [f"## {email}", ""]
        ids = semear_usuario(a.base, email, nome, log)
        todos[email] = ids
        linhas += log + [""]

    linhas += ["## IDs consolidados (usar na Fase 4 - IDOR)", "", "```json",
               json.dumps(todos, indent=2, ensure_ascii=False), "```", ""]

    destino = f"out/seed-{a.modelo}.md"
    with open(destino, "w") as f:
        f.write("\n".join(linhas))
    print("\n".join(linhas))
    print(f"\n>> escrito em {destino}")


if __name__ == "__main__":
    main()
