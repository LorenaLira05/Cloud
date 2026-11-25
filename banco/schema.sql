-- =====================================================================
-- Cloud Challenge - Desafio 02: Almoxarifado da Cantina-Escola
-- Arquivo: banco/schema.sql (PostgreSQL)
-- =====================================================================

-- Dropar tabelas se já existirem para recriação limpa (em ambiente de teste/setup)
DROP TABLE IF EXISTS movimentacoes CASCADE;
DROP TABLE IF EXISTS produtos CASCADE;

-- Tabela: produtos
-- Armazena os itens de consumo e ingredientes da cantina-escola
CREATE TABLE produtos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL UNIQUE,
    unidade VARCHAR(10) NOT NULL CHECK (unidade IN ('un', 'kg', 'L')),
    estoque_minimo NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    saldo NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (saldo >= 0),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabela: movimentacoes
-- Armazena o histórico imutável de entradas (compras) e saídas (cozinha)
CREATE TABLE movimentacoes (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade NUMERIC(10, 2) NOT NULL CHECK (quantidade > 0),
    motivo VARCHAR(255) NOT NULL,
    estorno_de INTEGER UNIQUE REFERENCES movimentacoes(id),
    criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimização de consultas e relatórios
CREATE INDEX idx_movimentacoes_produto_id ON movimentacoes(produto_id);
CREATE INDEX idx_movimentacoes_criada_em ON movimentacoes(criada_em);
CREATE INDEX idx_produtos_abaixo_minimo ON produtos(saldo, estoque_minimo);
