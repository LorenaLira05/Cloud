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


-- ==========================================
-- 1. CAFÉ TORRADO ESPECIAL
-- Saldo final: 10 kg
-- ==========================================

INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo) VALUES
(1, 'entrada', 12.00, 'NF-e 0001 - Compra inicial'),
(1, 'saida', 2.00, 'Requisição #01 - Café da manhã'),
(1, 'entrada', 8.00, 'NF-e 0007 - Reposição de estoque'),
(1, 'saida', 5.00, 'Requisição #02 - Consumo interno'),
(1, 'saida', 3.00, 'Requisição #03 - Evento escolar');

UPDATE produtos SET saldo = 10.00 WHERE id = 1;


-- ==========================================
-- 2. LEITE INTEGRAL UHT
-- Saldo final: 18 L
-- ==========================================

INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo) VALUES
(2, 'entrada', 15.00, 'NF-e 0002 - Compra de laticínios'),
(2, 'saida', 3.00, 'Requisição #04 - Merenda escolar'),
(2, 'entrada', 12.00, 'NF-e 0008 - Reposição de leite'),
(2, 'saida', 4.00, 'Requisição #05 - Preparação de alimentos'),
(2, 'saida', 2.00, 'Requisição #06 - Consumo interno');

UPDATE produtos SET saldo = 18.00 WHERE id = 2;


-- ==========================================
-- 3. ARROZ PARBOILIZADO
-- Saldo final: 16 kg
-- ==========================================

INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo) VALUES
(3, 'entrada', 25.00, 'NF-e 0003 - Compra de arroz'),
(3, 'saida', 12.00, 'Requisição #07 - Almoço dos estudantes'),
(3, 'entrada', 15.00, 'NF-e 0009 - Reposição de arroz'),
(3, 'saida', 8.00, 'Requisição #08 - Preparação de refeições'),
(3, 'saida', 4.00, 'Requisição #09 - Consumo interno');

UPDATE produtos SET saldo = 16.00 WHERE id = 3;


-- ==========================================
-- 4. FARINHA DE TRIGO
-- Saldo final: 12 kg
-- ==========================================

INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo) VALUES
(4, 'entrada', 20.00, 'NF-e 0004 - Compra de farinha'),
(4, 'saida', 5.00, 'Requisição #10 - Preparação de massas'),
(4, 'entrada', 10.00, 'NF-e 0010 - Reposição de farinha'),
(4, 'saida', 8.00, 'Requisição #11 - Produção de alimentos'),
(4, 'saida', 5.00, 'Requisição #12 - Consumo interno');

UPDATE produtos SET saldo = 12.00 WHERE id = 4;


-- ==========================================
-- 5. AÇÚCAR CRISTAL ORGÂNICO
-- Saldo final: 9 kg
-- ==========================================

INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo) VALUES
(5, 'entrada', 18.00, 'NF-e 0005 - Compra de açúcar'),
(5, 'saida', 4.00, 'Requisição #13 - Preparação de bebidas'),
(5, 'entrada', 10.00, 'NF-e 0011 - Reposição de açúcar'),
(5, 'saida', 8.00, 'Requisição #14 - Produção de alimentos'),
(5, 'saida', 7.00, 'Requisição #15 - Consumo interno');

UPDATE produtos SET saldo = 9.00 WHERE id = 5;


-- ==========================================
-- 6. GUARDANAPO DE PAPEL
-- Saldo final: 35 unidades
-- ==========================================

INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo) VALUES
(6, 'entrada', 50.00, 'NF-e 0006 - Compra de guardanapos'),
(6, 'saida', 10.00, 'Requisição #16 - Refeitório'),
(6, 'entrada', 30.00, 'NF-e 0012 - Reposição de guardanapos'),
(6, 'saida', 20.00, 'Requisição #17 - Evento escolar'),
(6, 'saida', 15.00, 'Requisição #18 - Consumo interno');

UPDATE produtos SET saldo = 35.00 WHERE id = 6;