# Evidência E4: Diagrama de Arquitetura e Decisões Técnicas

## 1. Diagrama de Arquitetura em Nuvem

```mermaid
flowchart TD
    subgraph Cliente ["Cliente / Interface"]
        UserBrowser["Navegador Web do Almoxarife\n(Dashboard HTML5 / JS Vanilla)"]
        RestClient["VS Code REST Client\n(requisicoes.http)"]
    end

    subgraph AzureCloud ["Microsoft Azure Cloud (Brazil South)"]
        subgraph AppService ["Azure App Service (Linux B1/F1)"]
            WSGI["Gunicorn WSGI Server\n(Porta process.env.PORT)"]
            Router["Roteador & Validador de Negócio\n(app.py)"]
            ConnPool["Driver de Banco (psycopg2)"]
        end

        subgraph DatabaseServ ["Azure Database for PostgreSQL (Flexible Server)"]
            PG["Instância PostgreSQL v16"]
            TabProd[("Tabela produtos\nCHECK saldo >= 0")]
            TabMov[("Tabela movimentacoes\nCHECK quantidade > 0")]
        end

        subgraph StorageOpt ["Armazenamento Opcional"]
            Blob["Azure Blob Storage\n(Relatórios CSV e Backups)"]
        end
    end

    UserBrowser -->|HTTPS :443 / REST JSON| WSGI
    RestClient -->|HTTP/HTTPS REST| WSGI
    WSGI --> Router
    Router --> ConnPool
    ConnPool -->|Conexão Segura TLS/SSL :5432\nDATABASE_URL| PG
    PG --> TabProd
    PG --> TabMov
    Router -.->|Exportação CSV| Blob
```

---

## 2. Caminho de uma Requisição de Saída (Fluxo Crítico da Regra Central)

1. O almoxarife submete a retirada de um item (`POST /api/produtos/1/movimentacoes` com `{ tipo: "saida", quantidade: 7 }`).
2. O App Service recebe o payload, valida no servidor os campos (`quantidade > 0`, `motivo preenchido`).
3. Uma transação ACID é iniciada no PostgreSQL.
4. O motor executa a instrução atômica com predicado de guarda:
   ```sql
   UPDATE produtos 
   SET saldo = saldo - 7 
   WHERE id = 1 AND saldo >= 7;
   ```
5. **Verificação imediata do lock:** Se o saldo atual for 6, a condição `saldo >= 7` é falsa. Nenhuma linha é alterada (`rows_affected = 0`).
6. A aplicação detecta a falha, executa `ROLLBACK;` imediato e devolve status **409 Conflict** ao cliente.
7. O banco permanece íntegro, sem saldo negativo e sem registro espúrio no histórico de movimentações.
