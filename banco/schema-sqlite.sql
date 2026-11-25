-- =====================================================================
-- Cloud Challenge - Desafio 02: Almoxarifado da Cantina-Escola
-- Arquivo: banco/schema-sqlite.sql (SQLite local)
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS movimentacoes;
DROP TABLE IF EXISTS produtos;

CREATE TABLE produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    unidade TEXT NOT NULL CHECK (unidade IN ('un', 'kg', 'L')),
    estoque_minimo REAL NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    saldo REAL NOT NULL DEFAULT 0 CHECK (saldo >= 0),
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade REAL NOT NULL CHECK (quantidade > 0),
    motivo TEXT NOT NULL,
    estorno_de INTEGER UNIQUE REFERENCES movimentacoes(id),
    criada_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_movimentacoes_produto_id ON movimentacoes(produto_id);
CREATE INDEX idx_movimentacoes_criada_em ON movimentacoes(criada_em);
CREATE INDEX idx_produtos_abaixo_minimo ON produtos(saldo, estoque_minimo);
