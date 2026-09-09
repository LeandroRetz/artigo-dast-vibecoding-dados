# Seed DAST - deepseek-mini-v4

Gerado em: 2026-09-07T21:54:31
Base: http://localhost:5173

Usuarios criados via `POST /api/auth/register` (senha `Test1234!`).
A promocao de `admin@test.com` para role admin e feita por SQL,
fora deste script, porque nenhuma das aplicacoes expoe rota para isso.

## user@test.com

  register user@test.com -> 201
  login user@test.com -> 200
  produto alvo: 1
  OK   POST /api/cart/items {"product_id": 1, "quantity": 2} -> 201
  OK   POST /api/checkout {"address": {"name": "Usuario Comum", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 201
  payment_intent=pi_3UDDIxRG5ULykWvo0AbVkpOc  order=1
  stripe confirm -> 200 succeeded
  OK   POST /api/orders {"orderId": 1, "paymentIntentId": "pi_3UDDIxRG5ULykWvo0AbVkpOc"} -> 200
  pedido id=1
  OK   POST /api/products/1/reviews {"rating": 5, "comment": "seed dast Usuario Comum"} -> 201
  avaliacao id=1

## admin@test.com

  register admin@test.com -> 201
  login admin@test.com -> 200
  produto alvo: 1
  OK   POST /api/cart/items {"product_id": 1, "quantity": 2} -> 201
  OK   POST /api/checkout {"address": {"name": "Admin Teste", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 201
  payment_intent=pi_3UDDJ0RG5ULykWvo0Fqtg07R  order=2
  stripe confirm -> 200 succeeded
  OK   POST /api/orders {"orderId": 2, "paymentIntentId": "pi_3UDDJ0RG5ULykWvo0Fqtg07R"} -> 200
  pedido id=2
  OK   POST /api/products/1/reviews {"rating": 5, "comment": "seed dast Admin Teste"} -> 201
  avaliacao id=2

## IDs consolidados (usar na Fase 4 - IDOR)

```json
{
  "user@test.com": {
    "produto_usado": 1,
    "carrinho": "criado",
    "pedido": 1,
    "avaliacao": 1
  },
  "admin@test.com": {
    "produto_usado": 1,
    "carrinho": "criado",
    "pedido": 2,
    "avaliacao": 2
  }
}
```
