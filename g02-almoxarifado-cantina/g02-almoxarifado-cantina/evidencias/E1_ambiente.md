# Evidência E1: Registro do Ambiente de Execução e Implantação

**Desafio:** 02 - Almoxarifado da Cantina-Escola  
**Turma:** Cloud Computing - Senac 2026.2  
**Professor:** Roni Maciel  
**Grupo:** G02  

---

## 1. Níveis de Implantação Suportados

A aplicação foi desenvolvida com arquitetura desacoplada, permitindo comprovação nos três níveis previstos no regulamento do desafio:

### Nível A (Nuvem Completa - Recomendado)
* **Computação:** Azure App Service (Linux, Runtime Python 3.12, Plano F1 Gratuito)
* **Banco de Dados:** Azure Database for PostgreSQL (Servidor Flexível, v16, Camada Burstable B1ms, 32 GiB)
* **Endereço Público (FQDN):** `https://app-cloud-g02-cantina.azurewebsites.net`
* **Health Check na Nuvem:** `https://app-cloud-g02-cantina.azurewebsites.net/health`
* **Comprovação:** URL pública acessível via navegador e testes remotos do professor.

### Nível B (Implantação Parcial)
* **Computação:** App Service ou Execução Local
* **Banco de Dados:** Banco PostgreSQL compartilhado na nuvem fornecido pelo professor via `DATABASE_URL`
* **Health Check:** `http://localhost:8000/health` retornando `banco: "conectado"` apontando para o servidor na nuvem.

### Nível C (Execução Local / Contingência de Infraestrutura)
* **Computação:** Execução nativa Python (`python app.py`) na porta `8000`
* **Banco de Dados:** SQLite Relacional ACID local (`banco/almoxarifado.db`) com integridade referencial ativa (`PRAGMA foreign_keys = ON`) e constraints `CHECK (saldo >= 0)`
* **Comprovação:** Demonstração ao vivo no localhost e logs do console.

---

## 2. Rota de Verificação de Integridade (GET /health)

A aplicação disponibiliza a rota `GET /health` que realiza uma consulta real (`SELECT 1;`) no banco de dados ativo e retorna o estado de integridade do serviço:

```json
{
  "status": "ok",
  "banco": "conectado",
  "tipo_banco": "postgres",
  "iniciado_em": "2026-11-18T19:10:06.499482+00:00",
  "consultado_em": "2026-11-18T19:10:08.123456+00:00",
  "servico": "Almoxarifado da Cantina-Escola",
  "desafio": "02",
  "grupo": "G02"
}
```

Caso o banco fique inacessível (ex: firewall bloqueando ou banco pausado), a rota responde com status HTTP **503 Service Unavailable** sem vazar credenciais ou stacktraces internas.
