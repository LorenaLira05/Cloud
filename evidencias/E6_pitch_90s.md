# Evidência E6: Roteiro do Pitch de 90 Segundos

Roteiro planejado e cronometrado para a feira de projetos da disciplina Cloud Challenge (Senac 2026.2).

---

### (00:00 - 00:15) - O Problema e o Usuário
> "Boa noite a todos! Na cantina-escola, o controle de estoque era feito numa planilha compartilhada onde qualquer um editava. O saldo frequentemente ficava negativo, ninguém sabia quem retirava os insumos e as compras de reposição eram feitas tarde demais. Nosso produto é o **Almoxarifado da Cantina-Escola**: um sistema em nuvem que garante saldo sempre coerente, histórico auditável de cada grama ou litro movimentado e alertas automáticos de reposição."

---

### (00:15 - 00:50) - Demonstração ao Vivo e Regra Central (Caso Recusado 409)
> "Vamos à prática: aqui na tela temos o produto 'Café Torrado', atualmente com **saldo 6.00 kg**. 
> Se a cozinha requisitar 4 kg, registramos a saída e o saldo cai perfeitamente para 2.00 kg, gerando a linha de histórico. 
> Agora, a **Regra Central**: se alguém tentar retirar 10 kg, o sistema recusa imediatamente com **status HTTP 409 Conflict** e mensagem clara de saldo insuficiente! 
> Notem que o saldo continuou intacto e nenhuma linha foi criada no histórico. Isso é garantido no banco por um `UPDATE` atômico com predicado `WHERE saldo >= quantidade` e uma constraint `CHECK (saldo >= 0)` que é a nossa última linha de defesa contra condições de corrida."

---

### (00:50 - 01:05) - Persistência Comprovada (G02-PALAVRA e PROF-HHMM)
> "Aqui no painel exibimos o registro **G02-NIMBUS** cadastrado durante o sprint 1. Mesmo após reiniciarmos o Azure App Service — o que pode ser conferido pela mudança no timestamp `iniciado_em` da rota `/health` —, o registro permanece íntegro. Ele mora fisicamente nas tabelas do nosso servidor flexível PostgreSQL gerenciado na Azure."

---

### (01:05 - 01:20) - Serviços Usados e Decisão Arquitetural Justificada
> "Usamos **Azure App Service Linux** com Python WSGI e **Azure Database for PostgreSQL**. 
> Nossa principal decisão arquitetural foi **armazenar o saldo na tabela em vez de recalcular com `SUM()` a cada consulta**. 
> O que ganhamos? Desempenho O(1) imediato em consultas de saldo e alertas de reposição. 
> O que perdemos? A necessidade de gerenciar transações estritas para evitar dessincronia. Resolvemos isso garantindo atomicidade total: débito e histórico ocorrem sempre dentro do mesmo bloco de transação."

---

### (01:20 - 01:30) - Dificuldade Superada e Próximos Passos
> "Nossa maior dificuldade foi contornar concorrência de saídas simultâneas sem criar gargalos de trava global de tabela, o que superamos usando o predicado condicional no `UPDATE`. 
> Como próximos passos, implementamos o estorno compensatório e pretendemos conectar o Azure Blob Storage para exportação programada de relatórios. Obrigado!"
