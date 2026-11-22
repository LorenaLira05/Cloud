#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Challenge - Senac 2026.2
Script de Testes Automatizados - Desafio 02: Almoxarifado da Cantina-Escola
Valida 100% dos Critérios de Aceitação (CA1 a CA5) e regras de negócio.
"""

import os
import sys
import json
import unittest
import io
import shutil

# Para garantir importação do módulo app
sys.path.insert(0, os.path.dirname(__file__))

# Força o ambiente de teste local limpo com SQLite isolado
os.environ["DATABASE_URL"] = ""

import app

class AlmoxarifadoTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Resetar banco de teste limpo
        banco_dir = os.path.join(os.path.dirname(__file__), "banco")
        test_db = os.path.join(banco_dir, "almoxarifado.db")
        if os.path.exists(test_db):
            os.remove(test_db)
        app.init_db_if_needed()

    def call_api(self, method, path, body=None, query_string=""):
        environ = {
            "REQUEST_METHOD": method.upper(),
            "PATH_INFO": path,
            "QUERY_STRING": query_string,
            "wsgi.input": io.BytesIO(json.dumps(body).encode("utf-8") if body else b""),
            "CONTENT_LENGTH": str(len(json.dumps(body).encode("utf-8"))) if body else "0"
        }
        status_holder = {}
        headers_holder = {}

        def start_response(status, headers):
            status_holder["status"] = status
            headers_holder["headers"] = dict(headers)

        response_chunks = app.app(environ, start_response)
        status_code = int(status_holder["status"].split()[0])
        response_body = b"".join(response_chunks).decode("utf-8")
        
        parsed_json = None
        if "application/json" in headers_holder["headers"].get("Content-Type", ""):
            try:
                parsed_json = json.loads(response_body)
            except Exception:
                pass

        return status_code, parsed_json, response_body

    def test_01_health_check(self):
        """Valida que /health retorna 200, status ok e o campo iniciado_em"""
        status, data, _ = self.call_api("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["banco"], "conectado")
        self.assertIn("iniciado_em", data)
        print("[OK] /health validado com sucesso. iniciado_em:", data["iniciado_em"])

    def test_02_ca1_fluxo_saldo_historico(self):
        """
        CA1. Entrada de 10 e depois saída de 4 -> saldo 6 e duas linhas no histórico.
        """
        # Cria produto exclusivo para o teste
        status, prod, _ = self.call_api("POST", "/api/produtos", {
            "nome": "Produto Teste CA1",
            "unidade": "kg",
            "estoque_minimo": 2.0
        })
        self.assertEqual(status, 201)
        prod_id = prod["id"]
        self.assertEqual(prod["saldo"], 0.0)

        # 1. Entrada de 10
        status, mov1, _ = self.call_api("POST", f"/api/produtos/{prod_id}/movimentacoes", {
            "tipo": "entrada",
            "quantidade": 10.0,
            "motivo": "Compra teste 10 kg"
        })
        self.assertEqual(status, 201)
        self.assertEqual(mov1["novo_saldo"], 10.0)

        # 2. Saída de 4
        status, mov2, _ = self.call_api("POST", f"/api/produtos/{prod_id}/movimentacoes", {
            "tipo": "saida",
            "quantidade": 4.0,
            "motivo": "Uso cozinha 4 kg"
        })
        self.assertEqual(status, 201)
        self.assertEqual(mov2["novo_saldo"], 6.0)

        # 3. Consultar produto e verificar histórico (RF4)
        status, consulta, _ = self.call_api("GET", f"/api/produtos/{prod_id}")
        self.assertEqual(status, 200)
        self.assertEqual(consulta["saldo"], 6.0)
        self.assertEqual(len(consulta["movimentacoes"]), 2)
        print("[OK] CA1 Aprovado: Entrada 10 + Saída 4 resultou em saldo 6.0 e exatamente 2 registros no histórico.")

    def test_03_ca2_regra_central_saida_maior_que_saldo(self):
        """
        CA2. Com saldo 6, saída de 7 -> 409; o saldo continua 6 e o histórico continua com 2 linhas.
        """
        # Usa o produto do CA1 (que tem saldo 6.0 e 2 linhas no histórico)
        status, prod, _ = self.call_api("POST", "/api/produtos", {
            "nome": "Produto Teste CA2 Regra Central",
            "unidade": "un",
            "estoque_minimo": 1.0
        })
        prod_id = prod["id"]

        # Abastecer com 6 unidades
        self.call_api("POST", f"/api/produtos/{prod_id}/movimentacoes", {
            "tipo": "entrada",
            "quantidade": 6.0,
            "motivo": "Abastecimento inicial 6"
        })

        # Verificar saldo antes
        _, antes, _ = self.call_api("GET", f"/api/produtos/{prod_id}")
        self.assertEqual(antes["saldo"], 6.0)
        historico_qtd_antes = len(antes["movimentacoes"])

        # Tentativa de saída de 7 (> que saldo de 6)
        status, erro_data, _ = self.call_api("POST", f"/api/produtos/{prod_id}/movimentacoes", {
            "tipo": "saida",
            "quantidade": 7.0,
            "motivo": "Tentativa indevida de retirar 7 com saldo 6"
        })
        self.assertEqual(status, 409, f"Esperado status 409 Conflict, recebido {status}")
        self.assertIn("erro", erro_data)

        # Verificar que saldo continua 6 e nenhuma movimentação foi inserida
        status, depois, _ = self.call_api("GET", f"/api/produtos/{prod_id}")
        self.assertEqual(depois["saldo"], 6.0)
        self.assertEqual(len(depois["movimentacoes"]), historico_qtd_antes)
        print("[OK] CA2 Aprovado (REGRA CENTRAL): Saída de 7 com saldo 6 recusada com 409. Saldo manteve-se em 6.0 e histórico inalterado.")

    def test_04_ca3_quantidade_zero_ou_negativa(self):
        """
        CA3. Quantidade 0 ou negativa -> 400.
        """
        # Teste com zero
        status, _, _ = self.call_api("POST", "/api/produtos/1/movimentacoes", {
            "tipo": "entrada",
            "quantidade": 0,
            "motivo": "Tentativa qtd zero"
        })
        self.assertEqual(status, 400)

        # Teste com negativa
        status, _, _ = self.call_api("POST", "/api/produtos/1/movimentacoes", {
            "tipo": "entrada",
            "quantidade": -15.5,
            "motivo": "Tentativa qtd negativa"
        })
        self.assertEqual(status, 400)
        print("[OK] CA3 Aprovado: Quantidade 0 ou negativa rejeitada com 400 Bad Request.")
    
    def test_05_ca4_alerta_estoque_minimo(self):
        """
        CA4. Produto com saldo 3 e mínimo 5 aparece em 'abaixo do mínimo'; com saldo 5, não aparece.
        """
        # Cadastrar produto com estoque_minimo = 5.0
        status, prod_a, _ = self.call_api("POST", "/api/produtos", {
            "nome": "Produto Teste CA4 Alerta A",
            "unidade": "kg",
            "estoque_minimo": 5.0
        })
        id_a = prod_a["id"]
        # Abastecer com saldo 3 (abaixo de 5)
        self.call_api("POST", f"/api/produtos/{id_a}/movimentacoes", {
            "tipo": "entrada",
            "quantidade": 3.0,
            "motivo": "Entrada de 3"
        })

        # Cadastrar produto com estoque_minimo = 5.0 e saldo 5.0
        status, prod_b, _ = self.call_api("POST", "/api/produtos", {
            "nome": "Produto Teste CA4 Alerta B",
            "unidade": "kg",
            "estoque_minimo": 5.0
        })
        id_b = prod_b["id"]
        self.call_api("POST", f"/api/produtos/{id_b}/movimentacoes", {
            "tipo": "entrada",
            "quantidade": 5.0,
            "motivo": "Entrada de 5"
        })

        # Consultar rota de abaixo do mínimo
        status, lista_minimo, _ = self.call_api("GET", "/api/produtos/abaixo-minimo")
        self.assertEqual(status, 200)

        ids_na_lista = [p["id"] for p in lista_minimo]
        self.assertIn(id_a, ids_na_lista, "Produto com saldo 3 e mínimo 5 DEVE aparecer em abaixo-minimo")
        self.assertNotIn(id_b, ids_na_lista, "Produto com saldo 5 e mínimo 5 NÃO DEVE aparecer em abaixo-minimo")
        print("[OK] CA4 Aprovado: Produto com saldo 3 e mínimo 5 listado em alerta; produto com saldo 5 não listado.")

    def test_06_ca5_produto_duplicado(self):
        """
        CA5. Cadastrar um produto com nome já existente -> 409.
        """
        nome_duplicado = "Produto Exclusivo CA5"
        # Primeiro cadastro
        status, _, _ = self.call_api("POST", "/api/produtos", {
            "nome": nome_duplicado,
            "unidade": "un",
            "estoque_minimo": 10.0
        })
        self.assertEqual(status, 201)

        # Segundo cadastro com o mesmo nome
        status, erro_data, _ = self.call_api("POST", "/api/produtos", {
            "nome": nome_duplicado,
            "unidade": "un",
            "estoque_minimo": 10.0
        })
        self.assertEqual(status, 409)
        self.assertIn("erro", erro_data)
        print("[OK] CA5 Aprovado: Tentativa de cadastrar produto duplicado retornou 409 Conflict.")

    def test_07_extra_estorno(self):
        """
        EXTRA: Estorno de movimentação sem apagar histórico
        """
        status, prod, _ = self.call_api("POST", "/api/produtos", {
            "nome": "Produto Teste Estorno",
            "unidade": "L",
            "estoque_minimo": 1.0
        })
        p_id = prod["id"]
        # Entrada de 10
        status, mov_res, _ = self.call_api("POST", f"/api/produtos/{p_id}/movimentacoes", {
            "tipo": "entrada",
            "quantidade": 10.0,
            "motivo": "Compra inicial"
        })
        m_id = mov_res["movimentacao"]["id"]
        
        # Realiza estorno
        status, estorno_res, _ = self.call_api("POST", f"/api/movimentacoes/{m_id}/estorno", {
            "motivo": "Erro de digitação"
        })
        self.assertEqual(status, 201)

        # Verificar que o saldo voltou a 0 e o histórico tem 2 linhas ( = auditoria preservada)
        status, p_check, _ = self.call_api("GET", f"/api/produtos/{p_id}")
        self.assertEqual(p_check["saldo"], 0.0)
        self.assertEqual(len(p_check["movimentacoes"]), 2)
        print("[OK] EXTRA Aprovado: Estorno compensatório executado com sucesso e trilha de auditoria preservada.")

    def test_08_extra_exportacao_csv(self):
        """
        EXTRA: Exportação do relatório de movimentações em CSV
        """
        status, _, body = self.call_api("GET", "/api/relatorio/csv")
        self.assertEqual(status, 200)
        self.assertIn("ID;Data/Hora;Produto;Unidade;Tipo;Quantidade;Motivo;Saldo Atual do Produto", body)
        print("[OK] EXTRA Aprovado: Relatório CSV gerado com cabeçalho e dados formatados.")

if __name__ == "__main__":
    unittest.main()
