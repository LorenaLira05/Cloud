#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desafio de Cloud - Senac 2026.2
Desafio 02: Almoxarifado da Cantina-Escolar
Tecnologia: Python 3 (WSGI nativo / Gunicorn para Azure App Service)
Compatibilidade: Azure Database for PostgreSQL & SQLite local
"""

import os
import sys
import json
import sqlite3
import datetime
import urllib.parse
from decimal import Decimal

# Timestamp de inicialização da aplicação (para comprovação na rota /health)
APP_INICIADO_EM = datetime.datetime.now(datetime.timezone.utc).isoformat()

# Carregar variáveis de ambiente simples if arquivo .env existir
def carregar_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

carregar_env()

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")

# Normalizar URL postgres para compatibilidade com SQLAlchemy / psycopg2
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Conexão com o banco de dados
def get_db():
    if IS_POSTGRES:
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            return conn, "postgres"
        except ImportError:
            try:
                import pg8000.dbapi
                url_parsed = urllib.parse.urlparse(DATABASE_URL)
                conn = pg8000.dbapi.connect(
                    user=url_parsed.username,
                    password=url_parsed.password,
                    host=url_parsed.hostname,
                    port=url_parsed.port or 5432,
                    database=url_parsed.path.lstrip("/")
                )
                return conn, "postgres"
            except Exception as e:
                raise RuntimeError(f"Driver PostgreSQL não encontrado ou erro de conexão: {e}")
    else:
        # SQLite Local
        db_dir = os.path.join(os.path.dirname(__file__), "banco")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "almoxarifado.db")
        conn = sqlite3.connect(db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn, "sqlite"

def init_db_if_needed():
    """Garante que as tabelas existam e carrega dados iniciais caso o  banco estiver vazio"""
    try:
        conn, engine = get_db()
        cur = conn.cursor()
        
        if engine == "sqlite":
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='produtos'")
            tabela_existe = cur.fetchone() is not None
            if not tabela_existe:
                schema_path = os.path.join(os.path.dirname(__file__), "banco", "schema-sqlite.sql")
                if os.path.exists(schema_path):
                    with open(schema_path, "r", encoding="utf-8") as f:
                        cur.executescript(f.read())
                
                # Inserir dados iniciais se arquivo existir
                dados_path = os.path.join(os.path.dirname(__file__), "banco", "dados-iniciais.sql")
                if os.path.exists(dados_path):
                    with open(dados_path, "r", encoding="utf-8") as f:
                        cur.executescript(f.read())
                conn.commit()
        else:
            # PostgreSQL
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'produtos'
                );
            """)
            existe = cur.fetchone()[0]
            if not existe:
                schema_path = os.path.join(os.path.dirname(__file__), "banco", "schema.sql")
                if os.path.exists(schema_path):
                    with open(schema_path, "r", encoding="utf-8") as f:
                        cur.execute(f.read())
                    conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[AVISO] Falha ao verificar/inicializar tabelas do banco: {e}", file=sys.stderr)

# esse aqui Inicializa o banco se necessário
init_db_if_needed()

# Helpers para respostas HTTP
def json_response(start_response, status_code, data):
    status_map = {
        200: "200 OK",
        201: "201 Created",
        400: "400 Bad Request",
        404: "404 Not Found",
        409: "409 Conflict",
        500: "500 Internal Server Error",
        503: "503 Service Unavailable"
    }
    status = status_map.get(status_code, f"{status_code} Unknown")
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
        ("Access-Control-Allow-Headers", "Content-Type")
    ]
    start_response(status, headers)
    return [body]

def html_response(start_response, html_content):
    body = html_content.encode("utf-8")
    headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body)))
    ]
    start_response("200 OK", headers)
    return [body]

def csv_response(start_response, csv_content, filename="relatorio_almoxarifado.csv"):
    body = csv_content.encode("utf-8-sig")
    headers = [
        ("Content-Type", "text/csv; charset=utf-8"),
        ("Content-Disposition", f'attachment; filename="{filename}"'),
        ("Content-Length", str(len(body)))
    ]
    start_response("200 OK", headers)
    return [body]

def parse_json_body(environ):
    try:
        content_length = int(environ.get("CONTENT_LENGTH", 0))
        if content_length > 0:
            raw = environ["wsgi.input"].read(content_length)
            return json.loads(raw.decode("utf-8")), None
        return {}, None
    except Exception as e:
        return None, f"JSON mal formatado: {str(e)}"

# ROTAS E REGRAS DE NEGÓCIO DO DOMÍNIO

def handle_health(environ, start_response):
    """
    Rota obrigatória GET /health
    Testa conexão com o banco e retorna timestamp de início 'iniciado_em'
    """
    try:
        conn, engine = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()

        agora = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return json_response(start_response, 200, {
            "status": "ok",
            "banco": "conectado",
            "tipo_banco": engine,
            "iniciado_em": APP_INICIADO_EM,
            "consultado_em": agora,
            "servico": "Almoxarifado da Cantina-Escola",
            "desafio": "02",
            "grupo": os.environ.get("GRUPO_ID", "G02")
        })
    except Exception as e:
        return json_response(start_response, 503, {
            "status": "erro",
            "banco": "desconectado",
            "iniciado_em": APP_INICIADO_EM,
            "mensagem": "Não foi possível conectar ao banco de dados.",
            "erro": str(e)
        })

def handle_listar_produtos(environ, start_response, apenas_abaixo_minimo=False):
    """
    RF2 / RF5: Listar produtos e destacar ou filtrar abaixo do estoque mínimo
    """
    query_string = environ.get("QUERY_STRING", "")
    params = urllib.parse.parse_qs(query_string)
    filtro_minimo = apenas_abaixo_minimo or params.get("abaixo_minimo", ["false"])[0].lower() in ("true", "1")

    try:
        conn, engine = get_db()
        cur = conn.cursor()
        
        sql = """
            SELECT id, nome, unidade, estoque_minimo, saldo, criado_em
            FROM produtos
        """
        if filtro_minimo:
            sql += " WHERE saldo < estoque_minimo"
        sql += " ORDER BY nome ASC"

        cur.execute(sql)
        linhas = cur.fetchall()
        
        produtos = []
        for row in linhas:
            if engine == "sqlite":
                p = dict(row)
            else:
                p = {
                    "id": row[0],
                    "nome": row[1],
                    "unidade": row[2],
                    "estoque_minimo": float(row[3]),
                    "saldo": float(row[4]),
                    "criado_em": str(row[5])
                }
            p["estoque_minimo"] = float(p["estoque_minimo"])
            p["saldo"] = float(p["saldo"])
            p["abaixo_minimo"] = p["saldo"] < p["estoque_minimo"]
            produtos.append(p)

        cur.close()
        conn.close()
        return json_response(start_response, 200, produtos)
    except Exception as e:
        return json_response(start_response, 500, {"erro": "Falha ao consultar produtos.", "detalhes": str(e)})

def handle_cadastrar_produto(environ, start_response):
    """
    RF1: Cadastrar produto com nome único, unidade ('un', 'kg' ou 'L'), estoque_minimo >= 0. Saldo inicial = 0.
    CA3 / CA5: Validação de entradas e tratamento de conflito (409)
    """
    dados, erro = parse_json_body(environ)
    if erro:
        return json_response(start_response, 400, {"erro": erro})

    nome = dados.get("nome", "").strip()
    unidade = dados.get("unidade", "").strip()
    estoque_minimo = dados.get("estoque_minimo", 0)

    # Validações no servidor
    if not nome or len(nome) < 2 or len(nome) > 120:
        return json_response(start_response, 400, {"erro": "O nome do produto é obrigatório e deve ter entre 2 e 120 caracteres."})

    unidades_validas = ("un", "kg", "L")
    if unidade not in unidades_validas:
        return json_response(start_response, 400, {
            "erro": f"Unidade inválida: '{unidade}'. Permitidas: {', '.join(unidades_validas)}."
        })

    try:
        estoque_minimo = float(estoque_minimo)
        if estoque_minimo < 0:
            return json_response(start_response, 400, {"erro": "O estoque mínimo deve ser maior ou igual a zero."})
    except (ValueError, TypeError):
        return json_response(start_response, 400, {"erro": "O estoque mínimo deve ser um número válido."})

    try:
        conn, engine = get_db()
        cur = conn.cursor()

        # Verificar duplicidade de nome (CA5)
        check_sql = "SELECT id FROM produtos WHERE LOWER(nome) = LOWER(%s)" if engine == "postgres" else "SELECT id FROM produtos WHERE LOWER(nome) = LOWER(?)"
        cur.execute(check_sql, (nome,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return json_response(start_response, 409, {
                "erro": f"Já existe um produto cadastrado com o nome '{nome}'."
            })

        # Inserção com saldo inicial 0
        if engine == "postgres":
            insert_sql = """
                INSERT INTO produtos (nome, unidade, estoque_minimo, saldo)
                VALUES (%s, %s, %s, 0)
                RETURNING id, nome, unidade, estoque_minimo, saldo, criado_em;
            """
            cur.execute(insert_sql, (nome, unidade, estoque_minimo))
            novo = cur.fetchone()
            produto = {
                "id": novo[0],
                "nome": novo[1],
                "unidade": novo[2],
                "estoque_minimo": float(novo[3]),
                "saldo": float(novo[4]),
                "criado_em": str(novo[5]),
                "abaixo_minimo": 0 < float(novo[3])
            }
        else:
            insert_sql = """
                INSERT INTO produtos (nome, unidade, estoque_minimo, saldo)
                VALUES (?, ?, ?, 0);
            """
            cur.execute(insert_sql, (nome, unidade, estoque_minimo))
            novo_id = cur.lastrowid
            cur.execute("SELECT id, nome, unidade, estoque_minimo, saldo, criado_em FROM produtos WHERE id = ?", (novo_id,))
            row = cur.fetchone()
            produto = {
                "id": row["id"],
                "nome": row["nome"],
                "unidade": row["unidade"],
                "estoque_minimo": float(row["estoque_minimo"]),
                "saldo": float(row["saldo"]),
                "criado_em": str(row["criado_em"]),
                "abaixo_minimo": 0 < float(row["estoque_minimo"])
            }

        conn.commit()
        cur.close()
        conn.close()
        return json_response(start_response, 201, produto)
    except Exception as e:
        return json_response(start_response, 500, {"erro": "Erro ao cadastrar produto.", "detalhes": str(e)})

def handle_consultar_produto(environ, start_response, produto_id):
    """
    RF4: Consultar produto com saldo atual e histórico completo de movimentações
    """
    try:
        conn, engine = get_db()
        cur = conn.cursor()

        p_sql = "SELECT id, nome, unidade, estoque_minimo, saldo, criado_em FROM produtos WHERE id = %s" if engine == "postgres" else "SELECT id, nome, unidade, estoque_minimo, saldo, criado_em FROM produtos WHERE id = ?"
        cur.execute(p_sql, (produto_id,))
        p_row = cur.fetchone()

        if not p_row:
            cur.close()
            conn.close()
            return json_response(start_response, 404, {"erro": f"Produto com ID {produto_id} não encontrado."})

        if engine == "sqlite":
            produto = dict(p_row)
        else:
            produto = {
                "id": p_row[0],
                "nome": p_row[1],
                "unidade": p_row[2],
                "estoque_minimo": float(p_row[3]),
                "saldo": float(p_row[4]),
                "criado_em": str(p_row[5])
            }
        produto["estoque_minimo"] = float(produto["estoque_minimo"])
        produto["saldo"] = float(produto["saldo"])
        produto["abaixo_minimo"] = produto["saldo"] < produto["estoque_minimo"]

        # Buscar histórico de movimentações
        m_sql = """
            SELECT id, tipo, quantidade, motivo, criada_em
            FROM movimentacoes
            WHERE produto_id = """ + ("%s" if engine == "postgres" else "?") + """
            ORDER BY criada_em ASC, id ASC
        """
        cur.execute(m_sql, (produto_id,))
        m_rows = cur.fetchall()

        historico = []
        for m in m_rows:
            if engine == "sqlite":
                item = dict(m)
            else:
                item = {
                    "id": m[0],
                    "tipo": m[1],
                    "quantidade": float(m[2]),
                    "motivo": m[3],
                    "criada_em": str(m[4])
                }
            item["quantidade"] = float(item["quantidade"])
            historico.append(item)

        produto["movimentacoes"] = historico
        produto["total_movimentacoes"] = len(historico)

        cur.close()
        conn.close()
        return json_response(start_response, 200, produto)
    except Exception as e:
        return json_response(start_response, 500, {"erro": "Falha ao consultar produto.", "detalhes": str(e)})

def handle_registrar_movimentacao(environ, start_response, produto_id):
    """
    RF2 / RF3 (REGRA CENTRAL):
    Registrar movimentação de entrada ou saída.
    Uma saída maior que o saldo atual é RECUSADA com 409, SEM REGISTRAR NADA.
    Usa UPDATE atômico com predicado:
      UPDATE produtos SET saldo = saldo - :qtd WHERE id = :id AND saldo >= :qtd
    e INSERT dentro da mesma transação ACID.
    """
    dados, erro = parse_json_body(environ)
    if erro:
        return json_response(start_response, 400, {"erro": erro})

    tipo = dados.get("tipo", "").strip().lower()
    quantidade_raw = dados.get("quantidade")
    motivo = dados.get("motivo", "").strip()

    # Validação do tipo
    if tipo not in ("entrada", "saida"):
        return json_response(start_response, 400, {
            "erro": f"Tipo de movimentação inválido: '{tipo}'. Permitidos: 'entrada' ou 'saida'."
        })

    # Validação da quantidade (CA3: <= 0 -> 400)
    try:
        quantidade = float(quantidade_raw)
        if quantidade <= 0:
            return json_response(start_response, 400, {
                "erro": "A quantidade movimentada deve ser estritamente maior que zero."
            })
    except (ValueError, TypeError):
        return json_response(start_response, 400, {
            "erro": "Quantidade inválida. Deve ser um número maior que zero."
        })

    if not motivo:
        return json_response(start_response, 400, {
            "erro": "O motivo da movimentação é obrigatório."
        })

    conn = None
    try:
        conn, engine = get_db()
        cur = conn.cursor()

        # 1. Verificar se produto existe
        p_sql = "SELECT id, nome, saldo FROM produtos WHERE id = %s" if engine == "postgres" else "SELECT id, nome, saldo FROM produtos WHERE id = ?"
        cur.execute(p_sql, (produto_id,))
        prod = cur.fetchone()
        if not prod:
            cur.close()
            conn.close()
            return json_response(start_response, 404, {"erro": f"Produto com ID {produto_id} não encontrado."})

        saldo_atual = float(prod[2] if engine == "postgres" else prod["saldo"])

        # 2. Processar de acordo com o tipo
        if tipo == "saida":
            # REGRA CENTRAL: Atualização com predicado atômico
            # Se saldo < quantidade, o UPDATE afeta 0 linhas.
            if engine == "postgres":
                update_sql = """
                    UPDATE produtos
                    SET saldo = saldo - %s
                    WHERE id = %s AND saldo >= %s
                    RETURNING saldo;
                """
                cur.execute(update_sql, (quantidade, produto_id, quantidade))
                res = cur.fetchone()
                if not res:
                    # Falha: saldo insuficiente! Rollback e recusar com 409
                    conn.rollback()
                    cur.close()
                    conn.close()
                    return json_response(start_response, 409, {
                        "erro": "Saída recusada: saldo insuficiente.",
                        "saldo_atual": saldo_atual,
                        "quantidade_solicitada": quantidade,
                        "mensagem": f"Não é possível retirar {quantidade} unidades. O saldo atual disponível é de {saldo_atual}."
                    })
                novo_saldo = float(res[0])
            else:
                # SQLite
                update_sql = """
                    UPDATE produtos
                    SET saldo = saldo - ?
                    WHERE id = ? AND saldo >= ?;
                """
                cur.execute(update_sql, (quantidade, produto_id, quantidade))
                if cur.rowcount == 0:
                    conn.rollback()
                    cur.close()
                    conn.close()
                    return json_response(start_response, 409, {
                        "erro": "Saída recusada: saldo insuficiente.",
                        "saldo_atual": saldo_atual,
                        "quantidade_solicitada": quantidade,
                        "mensagem": f"Não é possível retirar {quantidade} unidades. O saldo atual disponível é de {saldo_atual}."
                    })
                cur.execute("SELECT saldo FROM produtos WHERE id = ?", (produto_id,))
                novo_saldo = float(cur.fetchone()["saldo"])

        else: # entrada
            if engine == "postgres":
                update_sql = """
                    UPDATE produtos
                    SET saldo = saldo + %s
                    WHERE id = %s
                    RETURNING saldo;
                """
                cur.execute(update_sql, (quantidade, produto_id))
                novo_saldo = float(cur.fetchone()[0])
            else:
                update_sql = "UPDATE produtos SET saldo = saldo + ? WHERE id = ?"
                cur.execute(update_sql, (quantidade, produto_id))
                cur.execute("SELECT saldo FROM produtos WHERE id = ?", (produto_id,))
                novo_saldo = float(cur.fetchone()["saldo"])

        # 3. Registrar a movimentação no histórico dentro da MESMA transação
        if engine == "postgres":
            insert_m_sql = """
                INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo)
                VALUES (%s, %s, %s, %s)
                RETURNING id, criada_em;
            """
            cur.execute(insert_m_sql, (produto_id, tipo, quantidade, motivo))
            m_res = cur.fetchone()
            mov_id = m_res[0]
            criada_em = str(m_res[1])
        else:
            insert_m_sql = """
                INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo)
                VALUES (?, ?, ?, ?);
            """
            cur.execute(insert_m_sql, (produto_id, tipo, quantidade, motivo))
            mov_id = cur.lastrowid
            cur.execute("SELECT criada_em FROM movimentacoes WHERE id = ?", (mov_id,))
            criada_em = str(cur.fetchone()["criada_em"])

        # Confirma a transação atômica
        conn.commit()
        cur.close()
        conn.close()

        return json_response(start_response, 201, {
            "mensagem": "Movimentação registrada com sucesso.",
            "movimentacao": {
                "id": mov_id,
                "produto_id": produto_id,
                "tipo": tipo,
                "quantidade": quantidade,
                "motivo": motivo,
                "criada_em": criada_em
            },
            "saldo_anterior": saldo_atual,
            "novo_saldo": novo_saldo
        })

    except Exception as e:
        if conn:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
        return json_response(start_response, 500, {"erro": "Erro ao processar movimentação.", "detalhes": str(e)})

def handle_estorno_movimentacao(environ, start_response, mov_id):
    """
    EXTRA: Estorno de movimentação.
    Nunca apaga o histórico! Realiza uma movimentação compensatória de tipo oposto.
    """
    dados, _ = parse_json_body(environ)
    motivo_estorno = (dados.get("motivo") or "Estorno solicitado pelo almoxarife").strip()

    conn = None
    try:
        conn, engine = get_db()
        cur = conn.cursor()

        # Buscar movimentação original
        m_sql = "SELECT id, produto_id, tipo, quantidade, motivo FROM movimentacoes WHERE id = %s" if engine == "postgres" else "SELECT id, produto_id, tipo, quantidade, motivo FROM movimentacoes WHERE id = ?"
        cur.execute(m_sql, (mov_id,))
        m_row = cur.fetchone()
        if not m_row:
            cur.close()
            conn.close()
            return json_response(start_response, 404, {"erro": f"Movimentação com ID {mov_id} não encontrada."})

        p_id = m_row[1] if engine == "postgres" else m_row["produto_id"]
        tipo_orig = m_row[2] if engine == "postgres" else m_row["tipo"]
        qtd = float(m_row[3] if engine == "postgres" else m_row["quantidade"])

        # Tipo compensatório
        novo_tipo = "saida" if tipo_orig == "entrada" else "entrada"
        novo_motivo = f"ESTORNO da Movimentação #{mov_id} ({tipo_orig}): {motivo_estorno}"

        # Se o estorno for uma saída, verificar se há saldo suficiente
        if novo_tipo == "saida":
            upd_sql = "UPDATE produtos SET saldo = saldo - %s WHERE id = %s AND saldo >= %s" if engine == "postgres" else "UPDATE produtos SET saldo = saldo - ? WHERE id = ? AND saldo >= ?"
            cur.execute(upd_sql, (qtd, p_id, qtd))
            if cur.rowcount == 0:
                conn.rollback()
                cur.close()
                conn.close()
                return json_response(start_response, 409, {
                    "erro": "Não é possível estornar esta entrada pois o saldo atual ficaria negativo."
                })
        else:
            upd_sql = "UPDATE produtos SET saldo = saldo + %s WHERE id = %s" if engine == "postgres" else "UPDATE produtos SET saldo = saldo + ? WHERE id = ?"
            cur.execute(upd_sql, (qtd, p_id))

        # Registrar movimentação de estorno
        ins_sql = "INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo) VALUES (%s, %s, %s, %s)" if engine == "postgres" else "INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo) VALUES (?, ?, ?, ?)"
        cur.execute(ins_sql, (p_id, novo_tipo, qtd, novo_motivo))

        conn.commit()
        cur.close()
        conn.close()
        return json_response(start_response, 201, {
            "mensagem": "Estorno realizado com sucesso através de lançamento compensatório.",
            "movimentacao_estornada": mov_id,
            "tipo_compensatorio": novo_tipo,
            "quantidade": qtd
        })
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return json_response(start_response, 500, {"erro": "Falha no estorno.", "detalhes": str(e)})

def handle_exportar_csv(environ, start_response):
    """
    EXTRA: Exportar relatório de movimentações em formato CSV
    """
    try:
        conn, engine = get_db()
        cur = conn.cursor()
        sql = """
            SELECT m.id, m.criada_em, p.nome AS produto, p.unidade, m.tipo, m.quantidade, m.motivo, p.saldo AS saldo_final_produto
            FROM movimentacoes m
            JOIN produtos p ON p.id = m.produto_id
            ORDER BY m.criada_em DESC, m.id DESC;
        """
        cur.execute(sql)
        linhas = cur.fetchall()
        
        csv_lines = ["ID;Data/Hora;Produto;Unidade;Tipo;Quantidade;Motivo;Saldo Atual do Produto"]
        for row in linhas:
            if engine == "sqlite":
                r = dict(row)
                csv_lines.append(f"{r['id']};{r['criada_em']};\"{r['produto']}\";{r['unidade']};{r['tipo']};{r['quantidade']};\"{r['motivo']}\";{r['saldo_final_produto']}")
            else:
                csv_lines.append(f"{row[0]};{row[1]};\"{row[2]}\";{row[3]};{row[4]};{row[5]};\"{row[6]}\";{row[7]}")

        cur.close()
        conn.close()
        return csv_response(start_response, "\n".join(csv_lines))
    except Exception as e:
        return json_response(start_response, 500, {"erro": "Erro ao gerar CSV.", "detalhes": str(e)})

# INTERFACE WEB EMBUTIDA (DASHBOARD VISUAL COMPLETO)

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Almoxarifado da Cantina-Escola | Senac Cloud Challenge</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1e3a8a;
            --primary-light: #3b82f6;
            --success: #15803d;
            --success-bg: #dcfce7;
            --warning: #b45309;
            --warning-bg: #fef3c7;
            --danger: #b91c1c;
            --danger-bg: #fee2e2;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            padding: 24px;
            line-height: 1.5;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            padding: 20px 28px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 24px;
            border: 1px solid var(--border);
        }
        .header-title h1 { font-size: 1.4rem; color: var(--primary); font-weight: 700; }
        .header-title p { font-size: 0.88rem; color: var(--text-muted); margin-top: 4px; }
        .health-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--success-bg);
            color: var(--success);
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 600;
        }
        .health-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); }
        
        .grid-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .stat-label { font-size: 0.85rem; color: var(--text-muted); font-weight: 500; }
        .stat-value { font-size: 1.8rem; font-weight: 700; margin-top: 8px; }
        .stat-card.alert .stat-value { color: var(--danger); }

        .actions-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .filter-group { display: flex; gap: 8px; }
        .btn {
            font-family: inherit;
            font-size: 0.88rem;
            font-weight: 600;
            padding: 10px 18px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
        }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: #172554; }
        .btn-secondary { background: white; color: var(--text-main); border: 1px solid var(--border); }
        .btn-secondary:hover { background: #f1f5f9; }
        .btn-secondary.active { background: var(--primary); color: white; border-color: var(--primary); }
        .btn-success { background: var(--success); color: white; }
        .btn-danger { background: var(--danger); color: white; }
        .btn-sm { padding: 6px 12px; font-size: 0.8rem; }

        .card {
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            overflow: hidden;
            margin-bottom: 24px;
        }
        .table-responsive { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
        th { background: #f8fafc; padding: 14px 18px; font-weight: 600; color: var(--text-muted); border-bottom: 1px solid var(--border); }
        td { padding: 14px 18px; border-bottom: 1px solid var(--border); vertical-align: middle; }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #fafafa; }
        
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
        }
        .badge-danger { background: var(--danger-bg); color: var(--danger); }
        .badge-success { background: var(--success-bg); color: var(--success); }

        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 14px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            display: none;
            max-width: 400px;
        }
        .toast.success { background: var(--success); }
        .toast.error { background: var(--danger); }

        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(15, 23, 42, 0.6);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 999;
            padding: 16px;
        }
        .modal {
            background: white;
            border-radius: 12px;
            max-width: 550px;
            width: 100%;
            padding: 24px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
        }
        .modal-title { font-size: 1.15rem; font-weight: 700; color: var(--primary); }
        .modal-close {
            background: none; border: none; font-size: 1.4rem; cursor: pointer; color: var(--text-muted);
        }
        .form-group { margin-bottom: 16px; }
        .form-label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px; }
        .form-control {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-family: inherit;
            font-size: 0.9rem;
        }
        .form-control:focus { outline: none; border-color: var(--primary-light); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

        .test-box {
            background: #f1f5f9;
            border: 1px dashed #cbd5e1;
            border-radius: 8px;
            padding: 16px;
            margin-top: 24px;
        }
        .test-box h3 { font-size: 0.95rem; font-weight: 700; color: #334155; margin-bottom: 8px; }
        .test-buttons { display: flex; flex-wrap: wrap; gap: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <h1>🍽️ Cantina-Escola: Almoxarifado</h1>
                <p>Controle de estoque, compras (entradas), requisições da cozinha (saídas) e alertas</p>
            </div>
            <div id="healthBadge" class="health-badge">
                <span class="health-dot"></span>
                <span id="healthText">Testando /health...</span>
            </div>
        </header>

        <div class="grid-stats">
            <div class="stat-card">
                <div class="stat-label">Total de Itens Cadastrados</div>
                <div class="stat-value" id="statTotal">--</div>
            </div>
            <div class="stat-card alert">
                <div class="stat-label">Itens Abaixo do Mínimo (Alerta)</div>
                <div class="stat-value" id="statAbaixoMin">--</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Persistência na Nuvem</div>
                <div class="stat-value" style="font-size: 1.2rem; color: var(--success);" id="statPersistencia">Ativa (ACID)</div>
            </div>
        </div>

        <div class="actions-bar">
            <div class="filter-group">
                <button id="btnTodos" class="btn btn-secondary active" onclick="filtrarProdutos(false)">Todos os Produtos</button>
                <button id="btnAlerta" class="btn btn-secondary" onclick="filtrarProdutos(true)">⚠️ Abaixo do Mínimo</button>
            </div>
            <div style="display: flex; gap: 8px;">
                <a href="/api/relatorio/csv" class="btn btn-secondary" target="_blank">📥 Exportar CSV</a>
                <button class="btn btn-primary" onclick="abrirModalCadastro()">+ Novo Produto</button>
            </div>
        </div>

        <div class="card">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Produto</th>
                            <th>Unidade</th>
                            <th>Estoque Mínimo</th>
                            <th>Saldo Atual</th>
                            <th>Situação</th>
                            <th style="text-align: right;">Ações</th>
                        </tr>
                    </thead>
                    <tbody id="tabelaProdutosCorpo">
                        <tr><td colspan="7" style="text-align:center; padding: 30px;">Carregando produtos...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Painel de Demonstração e Verificação Rápida dos Casos de Teste (CA1 a CA5) -->
        <div class="test-box">
            <h3>🧪 Validação Rápida dos Critérios de Aceitação (Apresentação ao Vivo)</h3>
            <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px;">
                Clique nos botões abaixo para disparar os testes automáticos dos requisitos avaliados pelo professor:
            </p>
            <div class="test-buttons">
                <button class="btn btn-secondary btn-sm" onclick="executarTesteCA1()">Testar CA1 (Entrada 10 + Saída 4 = Saldo 6)</button>
                <button class="btn btn-secondary btn-sm" onclick="executarTesteCA2()" style="border-color: var(--danger); color: var(--danger);">Testar CA2 (Saída 7 com Saldo 6 -> Recusa 409)</button>
                <button class="btn btn-secondary btn-sm" onclick="executarTesteCA3()">Testar CA3 (Qtd <= 0 -> 400)</button>
                <button class="btn btn-secondary btn-sm" onclick="executarTesteCA4()">Testar CA4 (Filtro Abaixo do Mínimo)</button>
                <button class="btn btn-secondary btn-sm" onclick="executarTesteCA5()">Testar CA5 (Nome Duplicado -> 409)</button>
                <button class="btn btn-secondary btn-sm" onclick="gravarRegistroPalavra()">Gravar GXX-PALAVRA</button>
            </div>
        </div>
    </div>

    <!-- Modal Novo Produto -->
    <div id="modalProduto" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h2 class="modal-title">Cadastrar Novo Produto</h2>
                <button class="modal-close" onclick="fecharModais()">&times;</button>
            </div>
            <form id="formProduto" onsubmit="salvarProduto(event)">
                <div class="form-group">
                    <label class="form-label">Nome do Produto (Fictício)</label>
                    <input type="text" id="prodNome" class="form-control" placeholder="Ex: Café em Grãos Tipo Especial" required>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Unidade de Medida</label>
                        <select id="prodUnidade" class="form-control" required>
                            <option value="un">un (Unidade)</option>
                            <option value="kg">kg (Quilograma)</option>
                            <option value="L">L (Litro)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Estoque Mínimo</label>
                        <input type="number" step="0.01" min="0" id="prodMinimo" class="form-control" value="10" required>
                    </div>
                </div>
                <div style="display:flex; justify-content: flex-end; gap: 8px; margin-top: 16px;">
                    <button type="button" class="btn btn-secondary" onclick="fecharModais()">Cancelar</button>
                    <button type="submit" class="btn btn-primary">Cadastrar</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Modal Movimentação (Entrada/Saída) -->
    <div id="modalMov" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h2 class="modal-title" id="modalMovTitulo">Registrar Movimentação</h2>
                <button class="modal-close" onclick="fecharModais()">&times;</button>
            </div>
            <form id="formMov" onsubmit="salvarMovimentacao(event)">
                <input type="hidden" id="movProdutoId">
                <input type="hidden" id="movTipo">
                
                <div class="form-group" style="background:#f8fafc; padding:12px; border-radius:8px;">
                    <div><strong>Produto:</strong> <span id="movProdNome">--</span></div>
                    <div><strong>Saldo Atual:</strong> <span id="movProdSaldo">--</span></div>
                </div>

                <div class="form-group">
                    <label class="form-label">Quantidade</label>
                    <input type="number" step="0.01" min="0.01" id="movQtd" class="form-control" placeholder="Ex: 5" required>
                </div>

                <div class="form-group">
                    <label class="form-label">Motivo da Movimentação</label>
                    <input type="text" id="movMotivo" class="form-control" placeholder="Ex: Compra NF 1024 / Cozinha Refeitório" required>
                </div>

                <div style="display:flex; justify-content: flex-end; gap: 8px; margin-top: 16px;">
                    <button type="button" class="btn btn-secondary" onclick="fecharModais()">Cancelar</button>
                    <button type="submit" id="btnConfirmarMov" class="btn btn-primary">Confirmar</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Modal Detalhe / Histórico -->
    <div id="modalHistorico" class="modal-overlay">
        <div class="modal" style="max-width: 700px;">
            <div class="modal-header">
                <h2 class="modal-title" id="histProdNome">Histórico de Movimentações</h2>
                <button class="modal-close" onclick="fecharModais()">&times;</button>
            </div>
            <div id="histResumo" style="margin-bottom: 16px; font-size: 0.9rem;"></div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Tipo</th>
                            <th>Quantidade</th>
                            <th>Motivo</th>
                            <th>Data/Hora</th>
                        </tr>
                    </thead>
                    <tbody id="histTabelaCorpo">
                    </tbody>
                </table>
            </div>
            <div style="text-align:right; margin-top: 16px;">
                <button class="btn btn-secondary" onclick="fecharModais()">Fechar</button>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        let produtosCache = [];
        let filtroApenasAlerta = false;

        function showToast(msg, tipo = 'success') {
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.className = `toast ${tipo}`;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        async function verificarHealth() {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                const badge = document.getElementById('healthBadge');
                const text = document.getElementById('healthText');
                if (data.status === 'ok') {
                    text.innerHTML = `Banco: ${data.tipo_banco} | Up desde: ${new Date(data.iniciado_em).toLocaleTimeString()}`;
                } else {
                    badge.className = 'health-badge';
                    badge.style.background = '#fee2e2';
                    badge.style.color = '#b91c1c';
                    text.textContent = 'Banco Indisponível (503)';
                }
            } catch (err) {
                document.getElementById('healthText').textContent = 'Erro ao verificar /health';
            }
        }

        async function carregarProdutos() {
            try {
                const res = await fetch('/api/produtos');
                produtosCache = await res.json();
                renderizarTabela();
            } catch (err) {
                showToast('Erro ao carregar lista de produtos.', 'error');
            }
        }

        function renderizarTabela() {
            const corpo = document.getElementById('tabelaProdutosCorpo');
            const lista = filtroApenasAlerta 
                ? produtosCache.filter(p => p.saldo < p.estoque_minimo)
                : produtosCache;

            document.getElementById('statTotal').textContent = produtosCache.length;
            const abaixoCount = produtosCache.filter(p => p.saldo < p.estoque_minimo).length;
            document.getElementById('statAbaixoMin').textContent = abaixoCount;

            if (lista.length === 0) {
                corpo.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--text-muted);">Nenhum produto encontrado.</td></tr>`;
                return;
            }

            corpo.innerHTML = lista.map(p => {
                const isAlerta = p.saldo < p.estoque_minimo;
                const badgeClass = isAlerta ? 'badge-danger' : 'badge-success';
                const badgeTexto = isAlerta ? '⚠️ Abaixo do Mínimo' : '✅ Normal';
                
                return `
                    <tr>
                        <td><strong>#${p.id}</strong></td>
                        <td><strong>${p.nome}</strong></td>
                        <td>${p.unidade}</td>
                        <td>${p.estoque_minimo.toFixed(2)} ${p.unidade}</td>
                        <td><strong style="color: ${isAlerta ? 'var(--danger)' : 'var(--text-main)'}; font-size: 1.05rem;">${p.saldo.toFixed(2)} ${p.unidade}</strong></td>
                        <td><span class="badge ${badgeClass}">${badgeTexto}</span></td>
                        <td style="text-align: right;">
                            <button class="btn btn-secondary btn-sm" onclick="abrirHistorico(${p.id})">🔍 Histórico</button>
                            <button class="btn btn-success btn-sm" onclick="abrirModalMov(${p.id}, 'entrada')">+ Entrada</button>
                            <button class="btn btn-danger btn-sm" onclick="abrirModalMov(${p.id}, 'saida')">- Saída</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function filtrarProdutos(apenasAlerta) {
            filtroApenasAlerta = apenasAlerta;
            document.getElementById('btnTodos').className = `btn btn-secondary ${!apenasAlerta ? 'active' : ''}`;
            document.getElementById('btnAlerta').className = `btn btn-secondary ${apenasAlerta ? 'active' : ''}`;
            renderizarTabela();
        }

        function fecharModais() {
            document.querySelectorAll('.modal-overlay').forEach(m => m.style.display = 'none');
        }

        function abrirModalCadastro() {
            document.getElementById('prodNome').value = '';
            document.getElementById('prodMinimo').value = '10';
            document.getElementById('modalProduto').style.display = 'flex';
        }

        async function salvarProduto(e) {
            e.preventDefault();
            const payload = {
                nome: document.getElementById('prodNome').value.trim(),
                unidade: document.getElementById('prodUnidade').value,
                estoque_minimo: parseFloat(document.getElementById('prodMinimo').value)
            };
            const res = await fetch('/api/produtos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.status === 201) {
                showToast(`Produto '${data.nome}' cadastrado com sucesso!`);
                fecharModais();
                carregarProdutos();
            } else {
                showToast(data.erro || 'Falha ao cadastrar produto.', 'error');
            }
        }

        function abrirModalMov(prodId, tipo) {
            const p = produtosCache.find(item => item.id === prodId);
            if (!p) return;
            document.getElementById('movProdutoId').value = p.id;
            document.getElementById('movTipo').value = tipo;
            document.getElementById('movProdNome').textContent = `${p.nome} (${p.unidade})`;
            document.getElementById('movProdSaldo').textContent = `${p.saldo.toFixed(2)} ${p.unidade}`;
            document.getElementById('movQtd').value = '';
            document.getElementById('movMotivo').value = '';

            const titulo = tipo === 'entrada' ? '📥 Registrar Entrada (Compra)' : '📤 Registrar Saída (Uso Cozinha)';
            document.getElementById('modalMovTitulo').textContent = titulo;
            const btn = document.getElementById('btnConfirmarMov');
            btn.className = tipo === 'entrada' ? 'btn btn-success' : 'btn btn-danger';
            btn.textContent = tipo === 'entrada' ? 'Confirmar Entrada' : 'Confirmar Saída';

            document.getElementById('modalMov').style.display = 'flex';
        }

        async function salvarMovimentacao(e) {
            e.preventDefault();
            const prodId = document.getElementById('movProdutoId').value;
            const tipo = document.getElementById('movTipo').value;
            const qtd = parseFloat(document.getElementById('movQtd').value);
            const motivo = document.getElementById('movMotivo').value.trim();

            const res = await fetch(`/api/produtos/${prodId}/movimentacoes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tipo, quantidade: qtd, motivo })
            });
            const data = await res.json();
            if (res.status === 201) {
                showToast(`Movimentação de ${tipo} confirmada! Novo saldo: ${data.novo_saldo}`);
                fecharModais();
                carregarProdutos();
            } else if (res.status === 409) {
                showToast(`[409 CONFLITO] ${data.erro}`, 'error');
            } else {
                showToast(data.erro || 'Erro ao registrar movimentação.', 'error');
            }
        }

        async function abrirHistorico(prodId) {
            const res = await fetch(`/api/produtos/${prodId}`);
            if (!res.ok) {
                showToast('Erro ao consultar histórico.', 'error');
                return;
            }
            const p = await res.json();
            document.getElementById('histProdNome').textContent = `Histórico: ${p.nome}`;
            document.getElementById('histResumo').innerHTML = `
                <strong>Saldo Atual:</strong> ${p.saldo.toFixed(2)} ${p.unidade} | 
                <strong>Mínimo:</strong> ${p.estoque_minimo.toFixed(2)} ${p.unidade} | 
                <strong>Total de Registros:</strong> ${p.movimentacoes.length}
            `;
            const corpo = document.getElementById('histTabelaCorpo');
            if (p.movimentacoes.length === 0) {
                corpo.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px;">Nenhuma movimentação registrada até o momento.</td></tr>`;
            } else {
                corpo.innerHTML = p.movimentacoes.map(m => `
                    <tr>
                        <td>#${m.id}</td>
                        <td><span class="badge ${m.tipo === 'entrada' ? 'badge-success' : 'badge-danger'}">${m.tipo.toUpperCase()}</span></td>
                        <td><strong>${m.quantidade.toFixed(2)}</strong></td>
                        <td>${m.motivo}</td>
                        <td>${new Date(m.criada_em).toLocaleString()}</td>
                    </tr>
                `).join('');
            }
            document.getElementById('modalHistorico').style.display = 'flex';
        }

        // --- TESTES AUTOMÁTICOS DEMO PARA APRESENTAÇÃO ---
        async function executarTesteCA1() {
            // CA1. Entrada de 10 e depois saída de 4 -> saldo 6 e duas linhas no histórico
            const prodRes = await fetch('/api/produtos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome: 'Teste CA1 Produto ' + Date.now(), unidade: 'kg', estoque_minimo: 5 })
            });
            const prod = await prodRes.json();
            await fetch(`/api/produtos/${prod.id}/movimentacoes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tipo: 'entrada', quantidade: 10, motivo: 'Entrada CA1 de 10' })
            });
            await fetch(`/api/produtos/${prod.id}/movimentacoes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tipo: 'saida', quantidade: 4, motivo: 'Saida CA1 de 4' })
            });
            await carregarProdutos();
            await abrirHistorico(prod.id);
            showToast('CA1 Executado com Sucesso: Saldo final 6.00 com 2 movimentações no histórico!');
        }

        async function executarTesteCA2() {
            // CA2. Com saldo 6, saída de 7 -> 409; saldo continua 6 e histórico continua 2
            const prodRes = await fetch('/api/produtos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome: 'Teste CA2 Regra Central ' + Date.now(), unidade: 'un', estoque_minimo: 2 })
            });
            const prod = await prodRes.json();
            await fetch(`/api/produtos/${prod.id}/movimentacoes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tipo: 'entrada', quantidade: 6, motivo: 'Entrada 6' })
            });
            const failRes = await fetch(`/api/produtos/${prod.id}/movimentacoes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tipo: 'saida', quantidade: 7, motivo: 'Tentativa saída maior que saldo' })
            });
            const data = await failRes.json();
            await carregarProdutos();
            await abrirHistorico(prod.id);
            if (failRes.status === 409) {
                showToast(`✅ CA2 Validado com 409: ${data.erro}`, 'error');
            } else {
                showToast('Falha no CA2', 'error');
            }
        }

        async function executarTesteCA3() {
            const res = await fetch('/api/produtos/1/movimentacoes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tipo: 'entrada', quantidade: -5, motivo: 'Teste Qtd Negativa' })
            });
            const data = await res.json();
            if (res.status === 400) {
                showToast(`✅ CA3 Validado com 400 Bad Request: ${data.erro}`, 'success');
            }
        }

        async function executarTesteCA4() {
            filtrarProdutos(true);
            showToast('✅ CA4: Filtrando produtos com saldo < estoque_minimo.');
        }

        async function executarTesteCA5() {
            const res = await fetch('/api/produtos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome: 'Leite Integral UHT Escolar', unidade: 'L', estoque_minimo: 10 })
            });
            const data = await res.json();
            if (res.status === 409) {
                showToast(`✅ CA5 Validado com 409 Conflito: ${data.erro}`, 'error');
            }
        }

        async function gravarRegistroPalavra() {
            const codigo = prompt('Informe o código da palavra do dia (ex: G02-AZURE):', 'G02-NIMBUS');
            if (!codigo) return;
            const res = await fetch('/api/produtos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome: codigo, unidade: 'un', estoque_minimo: 1 })
            });
            const data = await res.json();
            if (res.status === 201) {
                showToast(`Registro de persistência '${codigo}' cadastrado com sucesso!`);
                carregarProdutos();
            } else {
                showToast(data.erro || 'Falha ao cadastrar', 'error');
            }
        }

        // Inicialização
        verificarHealth();
        carregarProdutos();
    </script>
</body>
</html>
"""

# ROTEADOR WSGI PRINCIPAL

def app(environ, start_response):
    path = environ.get("PATH_INFO", "/").rstrip("/")
    if not path:
        path = "/"
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # Preflight CORS
    if method == "OPTIONS":
        headers = [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type")
        ]
        start_response("200 OK", headers)
        return [b""]

    # 1. Interface Web
    if path == "/" and method == "GET":
        return html_response(start_response, HTML_DASHBOARD)

    # 2. Rota Health
    if path == "/health" and method == "GET":
        return handle_health(environ, start_response)

    # 3. Listar Produtos / Cadastrar Produto
    if path == "/api/produtos":
        if method == "GET":
            return handle_listar_produtos(environ, start_response)
        elif method == "POST":
            return handle_cadastrar_produto(environ, start_response)
        else:
            return json_response(start_response, 405, {"erro": "Método não permitido"})

    # 4. Produtos Abaixo do Mínimo (RF5)
    if path == "/api/produtos/abaixo-minimo" and method == "GET":
        return handle_listar_produtos(environ, start_response, apenas_abaixo_minimo=True)

    # 5. Exportar Relatório CSV (Extra)
    if path == "/api/relatorio/csv" and method == "GET":
        return handle_exportar_csv(environ, start_response)

    # 6. Rotas por Produto ID: /api/produtos/:id e /api/produtos/:id/movimentacoes
    parts = path.split("/")
    # Ex: /api/produtos/1 -> parts = ['', 'api', 'produtos', '1']
    if len(parts) == 4 and parts[1] == "api" and parts[2] == "produtos":
        try:
            prod_id = int(parts[3])
            if method == "GET":
                return handle_consultar_produto(environ, start_response, prod_id)
            else:
                return json_response(start_response, 405, {"erro": "Método não permitido"})
        except ValueError:
            return json_response(start_response, 400, {"erro": "ID de produto inválido"})

    # Ex: /api/produtos/1/movimentacoes -> parts = ['', 'api', 'produtos', '1', 'movimentacoes']
    if len(parts) == 5 and parts[1] == "api" and parts[2] == "produtos" and parts[4] == "movimentacoes":
        try:
            prod_id = int(parts[3])
            if method == "POST":
                return handle_registrar_movimentacao(environ, start_response, prod_id)
            else:
                return json_response(start_response, 405, {"erro": "Método não permitido"})
        except ValueError:
            return json_response(start_response, 400, {"erro": "ID de produto inválido"})

    # 7. Estorno de Movimentação (Extra): /api/movimentacoes/:id/estorno
    if len(parts) == 5 and parts[1] == "api" and parts[2] == "movimentacoes" and parts[4] == "estorno":
        try:
            mov_id = int(parts[3])
            if method == "POST":
                return handle_estorno_movimentacao(environ, start_response, mov_id)
            else:
                return json_response(start_response, 405, {"erro": "Método não permitido"})
        except ValueError:
            return json_response(start_response, 400, {"erro": "ID de movimentação inválido"})

    # Rota não encontrada
    return json_response(start_response, 404, {"erro": f"Rota '{path}' não encontrada."})

# Servidor de Desenvolvimento Local
if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    port = int(os.environ.get("PORT", 8000))
    print(f"===============================================================")
    print(f"🚀 Almoxarifado da Cantina-Escola rodando em http://localhost:{port}")
    print(f"📡 Rota de verificação: http://localhost:{port}/health")
    print(f"💾 Banco ativo: {'PostgreSQL' if IS_POSTGRES else 'SQLite local (banco/almoxarifado.db)'}")
    print(f"===============================================================")
    server = make_server("0.0.0.0", port, app)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor finalizado com sucesso.")
