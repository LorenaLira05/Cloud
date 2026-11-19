# Evidência E2: Prova de Persistência e Integridade dos Dados

**Desafio:** 02 - Almoxarifado da Cantina-Escola  
**Código do Registro:** `G02-NIMBUS` (Exemplo com a Palavra do Dia)  
**Registro do Professor (Nível A):** `PROF-2045`  

---

## Roteiro Obrigatório de Comprovação

Para comprovar que os dados sobrevivem ao reinício da aplicação e residem em um banco de dados real (não em memória nem arquivo volátil temporário):

### Passo 1: Cadastro do Registro `G02-PALAVRA`
Pela aplicação (via interface web ou requisição HTTP):
```http
POST /api/produtos
Content-Type: application/json

{
  "nome": "G02-NIMBUS",
  "unidade": "un",
  "estoque_minimo": 1.0
}
```
* **Retorno da API:** Status HTTP 201 Created com `{ "id": 7, "nome": "G02-NIMBUS", "saldo": 0.0, ... }`.

### Passo 2: Listagem pela Aplicação (Print 1)
Requisição: `GET /api/produtos`  
* **Evidência:** O produto `G02-NIMBUS` aparece na lista retornada pela API e na tabela do painel web com ID único.

### Passo 3: Verificação do `iniciado_em` na Rota `/health` (Print 2)
Requisição: `GET /health`  
* **Evidência:** Anotação do timestamp original:
  `"iniciado_em": "2026-11-18T19:10:06.499482+00:00"`

### Passo 4: Reinício da Aplicação
* **No Azure App Service (Nível A):** Executar no Azure CLI:
  ```bash
  az webapp restart --name app-cloud-g02-cantina --resource-group rg-cloud-g02
  ```
  Ou clicar no botão **Reiniciar** no Portal Azure.
* **No Ambiente Local (Nível C):** Encerrar o processo (`Ctrl+C`) e executar novamente `python app.py`.

### Passo 5: Confirmação de Sobrevivência e Novo `iniciado_em` (Print 3)
* Nova requisição `GET /health`:
  `"iniciado_em": "2026-11-18T20:35:12.102938+00:00"` (O timestamp de início MUDOU, provando que o processo reiniciou).
* Nova requisição `GET /api/produtos`: O registro `G02-NIMBUS` continua presente com todas as suas informações intactas.

### Passo 6: Consulta Direta ao Banco de Dados (Print 4)
Via Cloud Shell / psql / Editor de Consultas Azure:
```sql
SELECT id, nome, unidade, estoque_minimo, saldo, criado_em 
FROM produtos 
WHERE nome = 'G02-NIMBUS';
```
* **Evidência:** Registro conferido diretamente nas tabelas físicas do PostgreSQL.

## Critérios de Validação

- Dados preservados após reinicialização.
- `iniciado_em` atualizado após reinício.
- Registro confirmado na API e no banco de dados.
