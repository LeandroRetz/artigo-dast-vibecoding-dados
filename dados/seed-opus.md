# Seed DAST - opus

Gerado em: 2026-09-07T23:01:00
Base: http://localhost:5173

Usuarios criados via `POST /api/auth/register` (senha `Test1234!`).
A promocao de `admin@test.com` para role admin e feita por SQL,
fora deste script, porque nenhuma das aplicacoes expoe rota para isso.

## user@test.com

  register user@test.com -> 201
  login user@test.com -> 200
  produto alvo: 962889b8-7f1b-46d9-a75d-aa2ac46c294c
  --   POST /api/cart/items {"product_id": "962889b8-7f1b-46d9-a75d-aa2ac46c294c", "quantity": 2} -> 400
  OK   POST /api/cart/items {"productId": "962889b8-7f1b-46d9-a75d-aa2ac46c294c", "quantity": 2} -> 201
  --   POST /api/checkout {"address": {"name": "Usuario Comum", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 400
  OK   POST /api/checkout {"shipping": {"name": "Usuario Comum", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 201
  payment_intent=pi_3UDELJRG5ULykWvo1m4R2TYO  order=f47d8757-826c-408a-8ad1-188931452b49
  stripe confirm -> 200 succeeded
  OK   POST /api/orders {"orderId": "f47d8757-826c-408a-8ad1-188931452b49", "paymentIntentId": "pi_3UDELJRG5ULykWvo1m4R2TYO"} -> 200
  pedido id=f47d8757-826c-408a-8ad1-188931452b49
  OK   POST /api/products/962889b8-7f1b-46d9-a75d-aa2ac46c294c/reviews {"rating": 5, "comment": "seed dast Usuario Comum"} -> 201
  avaliacao id=61f7117a-2a95-40ec-a206-9e442c76a720

## admin@test.com

  register admin@test.com -> 201
  login admin@test.com -> 200
  produto alvo: 962889b8-7f1b-46d9-a75d-aa2ac46c294c
  --   POST /api/cart/items {"product_id": "962889b8-7f1b-46d9-a75d-aa2ac46c294c", "quantity": 2} -> 400
  OK   POST /api/cart/items {"productId": "962889b8-7f1b-46d9-a75d-aa2ac46c294c", "quantity": 2} -> 201
  --   POST /api/checkout {"address": {"name": "Admin Teste", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 400
  OK   POST /api/checkout {"shipping": {"name": "Admin Teste", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 201
  payment_intent=pi_3UDELLRG5ULykWvo0YVNRAqB  order=c940cfc7-52ec-48be-a2e3-401ec5b4630d
  stripe confirm -> 200 succeeded
  OK   POST /api/orders {"orderId": "c940cfc7-52ec-48be-a2e3-401ec5b4630d", "paymentIntentId": "pi_3UDELLRG5ULykWvo0YVNRAqB"} -> 200
  pedido id=c940cfc7-52ec-48be-a2e3-401ec5b4630d
  OK   POST /api/products/962889b8-7f1b-46d9-a75d-aa2ac46c294c/reviews {"rating": 5, "comment": "seed dast Admin Teste"} -> 201
  avaliacao id=fe77dd4c-d427-44bd-aa67-9a90a39d2428

## IDs consolidados (usar na Fase 4 - IDOR)

```json
{
  "user@test.com": {
    "produto_usado": "962889b8-7f1b-46d9-a75d-aa2ac46c294c",
    "carrinho": "criado",
    "pedido": "f47d8757-826c-408a-8ad1-188931452b49",
    "avaliacao": "61f7117a-2a95-40ec-a206-9e442c76a720"
  },
  "admin@test.com": {
    "produto_usado": "962889b8-7f1b-46d9-a75d-aa2ac46c294c",
    "carrinho": "criado",
    "pedido": "c940cfc7-52ec-48be-a2e3-401ec5b4630d",
    "avaliacao": "fe77dd4c-d427-44bd-aa67-9a90a39d2428"
  }
}
```
