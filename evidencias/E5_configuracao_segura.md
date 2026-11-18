# Evidência E5: Configuração Segura e Conformidade

A solução foi projetada seguindo as boas práticas de segurança recomendadas pelo OWASP e pelas diretrizes da disciplina:

## 1. Segregação de Credenciais e Variáveis de Ambiente
* Nenhuma senha, token ou string de conexão está presente no código-fonte.
* A conexão com o banco de dados é injetada estritamente via variável de ambiente `DATABASE_URL`.
* O arquivo `.env` está explicitamente incluído no `.gitignore` para impedir vazamento acidental em repositórios Git.
* Foi disponibilizado o arquivo `.env.example` com valores mascarados/fictícios para servir de gabarito para a equipe e o professor.

### Trecho do `.gitignore`:
```gitignore
# Variáveis de ambiente e segredos (NUNCA comitar)
.env
*.env
.env.local
```

### Configuração no Azure App Service:
No Portal Azure (ou Azure CLI):
```bash
az webapp config appsettings set \
  --name app-cloud-g02-cantina \
  --resource-group rg-cloud-g02 \
  --settings DATABASE_URL="postgresql://usuario:SENHA_OCULTADA@servidor.postgres.database.azure.com:5432/cantina_db?sslmode=require"
```

## 2. Prevenção Contra SQL Injection (Consultas Parametrizadas)
Todas as operações de consulta, inserção e atualização usam consultas estritamente parametrizadas (`%s` no PostgreSQL / `?` no SQLite). Nenhuma concatenação de strings com dados fornecidos pelo usuário é executada:

```python
# Exemplo de consulta parametrizada em app.py:
cur.execute("SELECT id FROM produtos WHERE LOWER(nome) = LOWER(%s)", (nome,))
```

## 3. Conformidade LGPD e Dados Fictícios
* Todos os dados de produtos, fornecedores e requisições são 100% fictícios (ex: "Fornecedor Fictício Café Brasil", "NF-e 0001").
* Nenhum dado pessoal real, CPF ou telefone foi incluído na base.

## 4. Comunicação Criptografada (TLS/SSL)
* A conexão entre o App Service e o Azure Database for PostgreSQL é obrigatória com criptografia TLS ativa (`sslmode=require`).
