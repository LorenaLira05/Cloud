# Almoxarifado da Cantina-Escola
> **Cloud Computing · Atividade Prática · Cloud Challenge (Senac 2026.2)**  
> **Professor:** Roni Maciel | **Desafio:** 02 | **Equipe:** Grupo 02 (G02)
>
> ### Integrantes da equipe
- Caio Barreto Cursino Monteiro Valle
- Lorena Beatriz Lira da Silva
- Luiz Felipe Ferreira dos Santos
- Maria Clara de Morais Silva
- Ricardo Rafael Arruda Lins
- Ruan Gualberto Dias Santos
- Vitor Daniel Ferreira dos Santos

[![Status](https://img.shields.io/badge/status-entregue%20e%20testado-success.svg)](#)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](#)
[![Database](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-336791.svg)](#)
[![Cloud](https://img.shields.io/badge/azure-App%20Service-0078D4.svg)](#)

---

## 1. Problema e Usuário

A cantina-escola gerenciava seu estoque de ingredientes e descartáveis através de uma planilha aberta a múltiplos funcionários, o que resultava frequentemente em saldos negativos, retiradas sem registro de autoria e desabastecimento da cozinha.  
O usuário principal é o **responsável pelo almoxarifado**, que necessita registrar compras (entradas) e requisições da cozinha (saídas) com total garantia de que saídas maiores que o saldo disponível sejam bloqueadas, mantendo o saldo estritamente coerente, o histórico de movimentações 100% auditável e emitindo alertas visuais de reposição para itens abaixo do estoque mínimo.

---

## 2. Status dos Requisitos da Ficha

| Código | Requisito | Descrição | Status |
|:---:|:---|:---|:---:|
| **RF1** | Cadastro de Produto | Nome único, unidade (`un`, `kg` ou `L`), estoque mínimo $\ge 0$ e saldo inicial $0$. | **Implementado** |
| **RF2** | Registro de Movimentações | Registro de entrada ou saída com quantidade $> 0$ e motivo obrigatório. | **Implementado** |
| **RF3** | **Regra Central** | **Saída maior que o saldo atual é recusada com 409 Conflict sem registrar nada.** | **Implementado** |
| **RF4** | Consulta Completa | Consulta de produto por ID exibindo saldo atual e histórico de movimentações. | **Implementado** |
| **RF5** | Alerta de Estoque Mínimo | Listagem de produtos onde $\text{saldo} < \text{estoque\_minimo}$. | **Implementado** |
| **CA1** | Teste de Fluxo | Entrada de 10 e depois saída de 4 $\rightarrow$ saldo 6 e 2 linhas no histórico. | **Aprovado** |
| **CA2** | Teste da Regra Central | Com saldo 6, saída de 7 $\rightarrow$ 409; saldo continua 6 e histórico com 2 linhas. | **Aprovado** |
| **CA3** | Validação de Entrada | Quantidade 0 ou negativa $\rightarrow$ 400 Bad Request. | **Aprovado** |
| **CA4** | Validação de Alerta | Produto com saldo 3 e mínimo 5 aparece em "abaixo do mínimo"; com saldo 5, não aparece. | **Aprovado** |
| **CA5** | Unicidade de Catálogo | Cadastrar produto com nome já existente $\rightarrow$ 409 Conflict. | **Aprovado** |
| **EXTRA** | Estorno Compensatório | Estorno de movimentação através de lançamento inverso sem apagar histórico. | **Implementado** |
| **EXTRA** | Exportação CSV | Exportação completa do relatório de movimentações e saldo em formato `.csv`. | **Implementado** |

---

## 3. Diagrama de Arquitetura e Decisões Justificadas

### 3.1. Arquitetura da Solução

```mermaid
flowchart TD
    subgraph Cliente ["Camada de Interação"]
        Browser["Interface Web Responsiva\n(Dashboard HTML5 / Vanilla JS)"]
        HTTPClient["Arquivo de Requisições\n(requisicoes.http / cURL)"]
    end

    subgraph NuvemAzure ["Microsoft Azure Cloud (Brazil South)"]
        subgraph AppService ["Azure App Service (Linux)"]
            WSGI["Servidor WSGI (Gunicorn / wsgiref)\nPorta: process.env.PORT"]
            API["API REST e Regras de Negócio (app.py)\nTransações ACID & Validação"]
        end

        subgraph Dados ["Camada de Persistência"]
            PG["Azure Database for PostgreSQL\n(Flexible Server v16)"]
            TabProd[("produtos\nCHECK saldo >= 0")]
            TabMov[("movimentacoes\nCHECK quantidade > 0")]
        end

        subgraph Storage ["Armazenamento"]
            Blob["Azure Blob Storage (Opcional)\nRelatórios de Auditoria CSV"]
        end
    end

    Browser -->|HTTPS :443| WSGI
    HTTPClient -->|HTTPS :443| WSGI
    WSGI --> API
    API -->|Pool TLS/SSL :5432\nDATABASE_URL| PG
    PG --> TabProd
    PG --> TabMov
    API -.->|Exportação| Blob
```

### 3.2. Decisões Arquiteturais Justificadas

#### Decisão 1: Saldo armazenado (rápido) ou calculado com `SUM` das movimentações (sempre coerente)?
* **Decisão adotada:** **Saldo armazenado na tabela `produtos`** com atualização atômica e proteção dupla (`CHECK (saldo >= 0)` + transação ACID).
* **O que se ganha:** Desempenho $O(1)$ imediato. A verificação de disponibilidade durante saídas de alta frequência e a listagem de alerta de estoque mínimo (`WHERE saldo < estoque_minimo`) ocorrem instantaneamente por varredura de índice, sem necessitar de agregações caras (`SUM()`) em milhões de linhas de histórico.
* **O que se perde e como mitigar:** Risco teórico de dessincronização entre o histórico e o saldo. Mitigado através de **transações ACID estritas**: o `UPDATE` de saldo e o `INSERT` na tabela `movimentacoes` ocorrem impreterivelmente dentro do mesmo bloco transacional (`BEGIN ... COMMIT`). Se qualquer etapa falhar, o `ROLLBACK` é acionado.

#### Decisão 2: Como garantir que a atualização do saldo e o registro da movimentação aconteçam juntos?
* **Decisão adotada:** Uso de **predicado atômico no comando SQL** associado ao bloco de transação:
  ```sql
  UPDATE produtos 
  SET saldo = saldo - :quantidade 
  WHERE id = :produto_id AND saldo >= :quantidade;
  ```
  Caso duas requisições concorrentes tentem retirar o mesmo saldo simultaneamente, o motor relacional aplica o lock a nível de linha (*Row-level Locking*). Se o saldo restante for insuficiente, o `rowcount` retornado é `0`. A aplicação intercepta essa resposta, aborta a transação (`ROLLBACK`) e responde com `409 Conflict`. Nenhuma movimentação espúria é inserida.

#### Decisão 3: A quantidade é inteira ou decimal (kg)?
* **Decisão adotada:** **Decimal (`NUMERIC(10, 2)`)**, mapeada no Python como ponto flutuante/Decimal.
* **Justificativa:** Na cantina-escola coexistem itens contáveis em unidades inteiras (como pacotes de guardanapos) e insumos fracionáveis medidos em quilogramas ou litros (ex.: $2.50\text{ kg}$ de arroz, $1.75\text{ L}$ de leite). O uso de tipo decimal exato com duas casas evita erros de arredondamento inerentes a números de ponto flutuante binário padrão IEEE 754.

#### Decisão 4: Banco Gerenciado na Azure (PaaS) vs. PostgreSQL Instalado em VM Linux (IaaS)
* **Comparativo:**
  * **Manutenção:** A VM exige que o grupo aplique patches de segurança do SO Linux, configure repositórios do Postgres, cuide de inicialização de serviços (`systemd`) e monitoramento manual. No **Azure Database for PostgreSQL**, a manutenção e patches são automatizados pela Microsoft sem parada de serviço.
  * **Backup:** Na VM, o backup exige scripts customizados (`pg_dump` ou `wal-g`) agendados via cron para storage secundário. No banco gerenciado, backups point-in-time (PITR) com retenção de até 35 dias e redundância geográfica estão incluídos nativamente.
  * **Custo e Tempo:** O provisionamento do banco gerenciado Burstable B1ms leva minutos pelo Portal ou CLI e pode ser pausado ao final da aula para custo zero de computação. Instalar e endurecer (*harden*) uma VM consome horas de laboratório que deveriam ser focadas no domínio do produto.

---

## 4. Modelo de Dados Relacional

```sql
-- Tabela de Produtos (com restrição de saldo positivo e unidade padronizada)
CREATE TABLE produtos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL UNIQUE,
    unidade VARCHAR(10) NOT NULL CHECK (unidade IN ('un', 'kg', 'L')),
    estoque_minimo NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    saldo NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (saldo >= 0),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Movimentações (histórico imutável de entradas e saídas)
CREATE TABLE movimentacoes (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade NUMERIC(10, 2) NOT NULL CHECK (quantidade > 0),
    motivo VARCHAR(255) NOT NULL,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Como Executar a Aplicação

### 5.1. Execução Local Imediata (Nível C - SQLite / Postgres)

1. Clone o repositório ou navegue até a pasta do projeto:
   ```bash
   cd g02-almoxarifado-cantina
   ```
2. Crie e ative um ambiente virtual (opcional):
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure as variáveis de ambiente:
   ```bash
   cp .env.example .env
   ```
   *(Por padrão, se `DATABASE_URL` não for configurada com Postgres, a aplicação inicia instantaneamente com SQLite local sem necessidade de servidor externo).*
5. Inicie o servidor:
   ```bash
   python app.py
   ```
6. Acesse no navegador:
   * **Dashboard Visual:** `http://localhost:8000`
   * **Health Check:** `http://localhost:8000/health`

### 5.2. Execução da Bateria de Testes Automatizados

O projeto inclui um executor de testes automatizados com cobertura total dos requisitos avaliados pelo professor:
```bash
python test_suite.py
```
*Saída esperada:*
```text
[OK] /health validado com sucesso. iniciado_em: 2026-11-18T19:10:06.499482+00:00
[OK] CA1 Aprovado: Entrada 10 + Saída 4 resultou em saldo 6.0 e exatamente 2 registros no histórico.
[OK] CA2 Aprovado (REGRA CENTRAL): Saída de 7 com saldo 6 recusada com 409. Saldo manteve-se em 6.0 e histórico inalterado.
[OK] CA3 Aprovado: Quantidade 0 ou negativa rejeitada com 400 Bad Request.
[OK] CA4 Aprovado: Produto com saldo 3 e mínimo 5 listado em alerta; produto com saldo 5 não listado.
[OK] CA5 Aprovado: Tentativa de cadastrar produto duplicado retornou 409 Conflict.
[OK] EXTRA Aprovado: Estorno compensatório executado com sucesso e trilha de auditoria preservada.
[OK] EXTRA Aprovado: Relatório CSV gerado com cabeçalho e dados formatados.

Ran 8 tests in 0.082s - OK
```

---

## 6. Plano de Implantação na Nuvem (Nível A - Azure App Service + PostgreSQL)

### Passo 1: Criar o Grupo de Recursos
```bash
az group create --name rg-cloud-g02 --location brazilsouth --tags aula=cloud-challenge grupo=g02
```

### Passo 2: Criar o Banco PostgreSQL Gerenciado
```bash
az postgres flexible-server create \
  --resource-group rg-cloud-g02 \
  --name srv-cloud-g02-db \
  --location brazilsouth \
  --admin-user adm_cantina \
  --admin-password "SenhaFicticiaForte123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --storage-size 32 \
  --public-access 0.0.0.0
```

### Passo 3: Criar o App Service Plan e a Aplicação Web
```bash
az appservice plan create \
  --name plan-cloud-g02 \
  --resource-group rg-cloud-g02 \
  --sku F1 \
  --is-linux

az webapp create \
  --name app-cloud-g02-cantina \
  --resource-group rg-cloud-g02 \
  --plan plan-cloud-g02 \
  --runtime "PYTHON:3.12"
```

### Passo 4: Configurar as Variáveis de Ambiente no App Service
```bash
az webapp config appsettings set \
  --name app-cloud-g02-cantina \
  --resource-group rg-cloud-g02 \
  --settings \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    DATABASE_URL="postgresql://adm_cantina:SenhaFicticiaForte123!@srv-cloud-g02-db.postgres.database.azure.com:5432/cantina_db?sslmode=require" \
    GRUPO_ID="G02"
```

### Passo 5: Configurar o Comando de Inicialização e Deploy
Configurar o comando Gunicorn no App Service:
```bash
az webapp config set \
  --name app-cloud-g02-cantina \
  --resource-group rg-cloud-g02 \
  --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app"
```

Publicar via arquivo ZIP ou GitHub Deployment Center:
```bash
az webapp deploy \
  --name app-cloud-g02-cantina \
  --resource-group rg-cloud-g02 \
  --src-path . \
  --type zip
```

---

## 7. Tabela de Casos de Teste (Evidência E3)

| Teste | Objetivo | Dados de Entrada | Resposta Esperada | Resposta Obtida | Status |
|:---:|:---|:---|:---:|:---:|:---:|
| **CA1** | Fluxo de Entrada e Saída | Entrada 10, depois Saída 4 | Saldo 6.00 e 2 movimentações | Saldo 6.00 e 2 movimentações | **Passou** |
| **CA2** | **Regra Central: Bloqueio de Saída** | Saldo 6.00, tentar saída de 7 | **409 Conflict**, saldo 6.00 | **409 Conflict**, saldo 6.00 | **Passou** |
| **CA3** | Validação de Quantidade | Quantidade $\le 0$ (-5 ou 0) | **400 Bad Request** | **400 Bad Request** | **Passou** |
| **CA4** | Alerta de Estoque Mínimo | Prod A (saldo 3, min 5); Prod B (saldo 5, min 5) | Prod A aparece; Prod B não aparece | Prod A aparece; Prod B não aparece | **Passou** |
| **CA5** | Unicidade de Nome | Cadastrar nome repetido | **409 Conflict** | **409 Conflict** | **Passou** |

---

## 8. Dificuldade Superada

* **Problema Encontrado:** Ao testar requisições concorrentes de saída na cozinha, se a aplicação fizesse uma leitura prévia do saldo (`SELECT saldo`) para depois executar o `UPDATE`, duas saídas quase simultâneas poderiam ler o mesmo saldo de 6 unidades e ambas serem aceitas para saídas de 4 unidades, gerando um saldo final negativo de -2 unidades, violando a regra central.
* **Diagnóstico e Causa:** Condição de corrida (*race condition*) entre a leitura e a escrita (ausência de atomicidade no nível de banco de dados).
* **Solução Implementada:** O débito de estoque foi refatorado para utilizar uma instrução SQL atômica com predicado de guarda condicional:
  `UPDATE produtos SET saldo = saldo - :qtd WHERE id = :id AND saldo >= :qtd`
  junto com a constraint de integridade `CHECK (saldo >= 0)` como última linha de defesa. Se nenhuma linha for afetada (`rowcount == 0`), a transação é imediatamente revertida com `ROLLBACK` e a API devolve `409 Conflict`.

---

## 9. Limitações Conhecidas e Próximos Passos

1. **Autenticação e Perfis:** No momento, o sistema opera em modo de confiança acadêmico (qualquer usuário na rede da cantina pode acessar a tela e registrar ações). Como próximo passo, integrar o **Azure AD B2C** ou **Auth0** para diferenciar almoxarifes (entradas) de auxiliares de cozinha (apenas saídas).
2. **Integração com Azure Blob Storage:** A exportação de CSV atualmente gera o arquivo em streaming dinâmico; o próximo incremento é salvar snapshots diários automaticamente em um contêiner privado do Blob Storage com links assinados de curta duração (SAS).
3. **Ponto de Reposição Sugerido:** Cálculo automático de previsão de dias restantes de estoque com base na média móvel das saídas dos últimos 14 dias.

---
