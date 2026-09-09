# Seed DAST - qwen-3.8-8b

Gerado em: 2026-09-07T22:32:33
Base: http://localhost:5173

Usuarios criados via `POST /api/auth/register` (senha `Test1234!`).
A promocao de `admin@test.com` para role admin e feita por SQL,
fora deste script, porque nenhuma das aplicacoes expoe rota para isso.

## user@test.com

  register user@test.com -> 201
  login user@test.com -> 200
  produto alvo: 9
  OK   POST /api/cart/items {"product_id": 9, "quantity": 2} -> 201
  OK   POST /api/checkout {"address": {"name": "Usuario Comum", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 200
  payment_intent=pi_3UDDtmRG5ULykWvo1BujDc82  order=None
  stripe confirm -> 200 succeeded
  --   POST /api/orders {"orderId": null, "paymentIntentId": "pi_3UDDtmRG5ULykWvo1BujDc82"} -> 400
  --   POST /api/orders {"order_id": null, "payment_intent_id": "pi_3UDDtmRG5ULykWvo1BujDc82"} -> 400
  --   POST /api/orders {"payment_intent_id": "pi_3UDDtmRG5ULykWvo1BujDc82", "address": {"name": "Usuario Comum", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 400
  OK   POST /api/orders {"paymentIntentId": "pi_3UDDtmRG5ULykWvo1BujDc82", "address": {"name": "Usuario Comum", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 201
  pedido id=86783fc1-103a-42ee-8c71-d37958e7fa33
  OK   POST /api/products/9/reviews {"rating": 5, "comment": "seed dast Usuario Comum"} -> 201
  avaliacao id=1

## admin@test.com

  register admin@test.com -> 201
  login admin@test.com -> 200
  produto alvo: 9
  OK   POST /api/cart/items {"product_id": 9, "quantity": 2} -> 201
  OK   POST /api/checkout {"address": {"name": "Admin Teste", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 200
  payment_intent=pi_3UDDtpRG5ULykWvo03cIxgVj  order=None
  stripe confirm -> 200 succeeded
  --   POST /api/orders {"orderId": null, "paymentIntentId": "pi_3UDDtpRG5ULykWvo03cIxgVj"} -> 400
  --   POST /api/orders {"order_id": null, "payment_intent_id": "pi_3UDDtpRG5ULykWvo03cIxgVj"} -> 400
  --   POST /api/orders {"payment_intent_id": "pi_3UDDtpRG5ULykWvo03cIxgVj", "address": {"name": "Admin Teste", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 400
  OK   POST /api/orders {"paymentIntentId": "pi_3UDDtpRG5ULykWvo03cIxgVj", "address": {"name": "Admin Teste", "phone": "51999990000", "line1": "Rua Teste 100", "line2": "Apto 1", "street": "Rua Teste 100", "city": "Porto Alegre", "state": "RS", "postal_code": "90000000", "postalCode": "90000000", "zip": "90000000", "country": "BR"}} -> 201
  pedido id=eb413cbb-df93-460b-85bb-4aec026388ce
  OK   POST /api/products/9/reviews {"rating": 5, "comment": "seed dast Admin Teste"} -> 201
  avaliacao id=2

## IDs consolidados (usar na Fase 4 - IDOR)

```json
{
  "user@test.com": {
    "produto_usado": 9,
    "carrinho": "criado",
    "pedido": "86783fc1-103a-42ee-8c71-d37958e7fa33",
    "avaliacao": 1
  },
  "admin@test.com": {
    "produto_usado": 9,
    "carrinho": "criado",
    "pedido": "eb413cbb-df93-460b-85bb-4aec026388ce",
    "avaliacao": 2
  }
}
```
