-- =====================================================================
-- Cloud Challenge - Desafio 02: Almoxarifado da Cantina-Escola
-- Arquivo: banco/dados-iniciais.sql (Dados Fictícios Iniciais)
-- =====================================================================

-- Inserção de produtos fictícios com saldo 0
INSERT INTO produtos (nome, unidade, estoque_minimo, saldo) VALUES
('Café Torrado Especial Fictício', 'kg', 5.00, 0.00),
('Leite Integral UHT Escolar', 'L', 20.00, 0.00),
('Arroz Parboilizado Tipo 1', 'kg', 15.00, 0.00),
('Farinha de Trigo Tradicional', 'kg', 10.00, 0.00),
('Açúcar Cristal Orgânico', 'kg', 8.00, 0.00),
('Guardanapo de Papel 100un', 'un', 30.00, 0.00);

-- Movimentações iniciais de compras (Entradas) que abastecem o estoque
-- 1. Café: Entrada de 12 kg (saldo passa a 12.00, min 5.00 -> OK)
INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo)
VALUES (1, 'entrada', 12.00, 'NF-e 0001 - Fornecedor Fictício Café Brasil');
UPDATE produtos SET saldo = saldo + 12.00 WHERE id = 1;

-- 2. Leite: Entrada de 15 L (saldo passa a 15.00, min 20.00 -> Abaixo do mínimo!)
INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo)
VALUES (2, 'entrada', 15.00, 'NF-e 0002 - Laticínios Escolares Exemplo');
UPDATE produtos SET saldo = saldo + 15.00 WHERE id = 2;

-- 3. Arroz: Entrada de 25 kg, depois saída de 12 kg (saldo = 13.00, min 15.00 -> Abaixo do mínimo!)
INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo)
VALUES (3, 'entrada', 25.00, 'NF-e 0003 - Distribuidora Alimentos Fictícia');
UPDATE produtos SET saldo = saldo + 25.00 WHERE id = 3;

INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo)
VALUES (3, 'saida', 12.00, 'Requisição Cozinha #01 - Almoço dos Estudantes');
UPDATE produtos SET saldo = saldo - 12.00 WHERE id = 3;

-- 4. Farinha: Entrada de 20 kg (saldo passa a 20.00, min 10.00 -> OK)
INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo)
VALUES (4, 'entrada', 20.00, 'NF-e 0004 - Moagem Modelo');
UPDATE produtos SET saldo = saldo + 20.00 WHERE id = 4;
