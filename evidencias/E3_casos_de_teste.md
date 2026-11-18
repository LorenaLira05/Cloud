# Evidência E3: Casos de Teste e Validações do Domínio

A tabela abaixo documenta a bateria de testes automatizados e manuais, cobrindo 100% dos critérios de aceitação (CA1 a CA5), com casos positivos e negativos, regras de concorrência e integridade.

| ID | Cenário de Teste | Tipo | Requisição / Entrada | Resultado Esperado | Status Obtido |
|:---|:---|:---:|:---|:---|:---:|
| **CA1** | Fluxo de entrada e saída com histórico | Positivo | 1. Entrada de 10 kg<br>2. Saída de 4 kg | HTTP 201 em ambas as operações.<br>Saldo final = 6.00.<br>Histórico com exatamente 2 registros ordenados. | **Aprovado (201)** |
| **CA2** | **REGRA CENTRAL:** Saída maior que saldo disponível | **Negativo** | Com saldo = 6.00, requisitar saída de 7.00 | **HTTP 409 Conflict**.<br>Mensagem clara de saldo insuficiente.<br>Saldo permanece inalterado em 6.00.<br>Nenhum registro criado no histórico. | **Aprovado (409)** |
| **CA3** | Quantidade zero ou negativa | **Negativo** | `POST /movimentacoes` com `quantidade: 0` ou `quantidade: -10` | **HTTP 400 Bad Request** com mensagem de validação no servidor. Nada gravado. | **Aprovado (400)** |
| **CA4** | Alerta de estoque baixo (Abaixo do Mínimo) | Regra / Consulta | Produto A (saldo 3, min 5);<br>Produto B (saldo 5, min 5).<br>`GET /api/produtos/abaixo-minimo` | Produto A **aparece** na lista de alerta.<br>Produto B **não aparece** na lista de alerta. | **Aprovado (200)** |
| **CA5** | Duplicidade de nome de produto | **Negativo** | `POST /api/produtos` com nome idêntico a produto já cadastrado | **HTTP 409 Conflict** informando que o produto já existe no catálogo. | **Aprovado (409)** |
| **CT6** | Consulta de produto inexistente | **Negativo** | `GET /api/produtos/99999` | **HTTP 404 Not Found** com payload JSON claro. | **Aprovado (404)** |
| **CT7** | Conexão de Health Check | Sistema | `GET /health` | **HTTP 200 OK** com status do banco e timestamp `iniciado_em`. | **Aprovado (200)** |
| **CT8** | Estorno compensatório (Extra) | Auditoria | `POST /api/movimentacoes/1/estorno` | **HTTP 201 Created** com lançamento inverso sem exclusão física do registro original. | **Aprovado (201)** |
| **CT9** | Exportação CSV (Extra) | Relatório | `GET /api/relatorio/csv` | **HTTP 200 OK** com cabeçalhos MIME e conteúdo separado por ponto e vírgula. | **Aprovado (200)** |
