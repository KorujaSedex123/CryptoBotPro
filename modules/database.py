import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "trades.db"

def conectar():
    """Conecta ao banco com WAL ativado"""
    # Ajuste do caminho dependendo de onde chama
    caminho = f"../{DB_NAME}" if __name__ == "__main__" else DB_NAME
    if __name__ == "__main__": caminho = DB_NAME # Se rodar direto na pasta modules
    
    conn = sqlite3.connect(caminho)
    conn.execute("PRAGMA journal_mode=WAL;") 
    return conn

def criar_tabelas():
    try:
        conn = sqlite3.connect(DB_NAME) # Cria na raiz se chamado do main
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                tipo TEXT,
                preco REAL,
                quantidade REAL,
                lucro REAL,
                data_hora TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS status_ia (
                id INTEGER PRIMARY KEY,
                rsi REAL,
                potencial REAL,
                decisao TEXT,
                atualizado_em TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memoria_bot (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                saldo REAL,
                posicao BOOLEAN,
                preco_compra REAL,
                qtd_btc REAL,
                preco_maximo REAL,
                ultima_atualizacao TEXT
            )
        ''')
        
        # Cria a linha inicial se não existir (Começa zerado)
        cursor.execute('''
            INSERT OR IGNORE INTO memoria_bot (id, saldo, posicao, preco_compra, qtd_btc, preco_maximo, ultima_atualizacao)
            VALUES (1, 100.0, 0, 0.0, 0.0, 0.0, datetime('now'))
        ''')
        conn.commit()
        conn.close()
        print("📂 Banco de dados pronto.")
    except Exception as e:
        print(f"Erro ao criar banco: {e}")

        # --- FUNÇÕES DE MEMÓRIA ---

def salvar_estado(saldo, posicao, preco_compra, qtd_btc, preco_maximo):
    """Grava o estado atual no disco"""
    try:
        conn = conectar()
        cursor = conn.cursor()
        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Atualiza a ÚNICA linha (id=1)
        cursor.execute('''
            UPDATE memoria_bot 
            SET saldo=?, posicao=?, preco_compra=?, qtd_btc=?, preco_maximo=?, ultima_atualizacao=?
            WHERE id=1
        ''', (saldo, posicao, preco_compra, qtd_btc, preco_maximo, data_hora))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar estado: {e}")

def carregar_estado():
    """Lê o último estado gravado ao iniciar"""
    try:
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT saldo, posicao, preco_compra, qtd_btc, preco_maximo FROM memoria_bot WHERE id=1")
        dados = cursor.fetchone()
        conn.close()
        
        if dados:
            return {
                "saldo": dados[0],
                "posicao": bool(dados[1]), # Converte 0/1 pra True/False
                "preco_compra": dados[2],
                "qtd_btc": dados[3],
                "preco_maximo": dados[4]
            }
        return None
    except Exception as e:
        print(f"Erro ao carregar estado: {e}")
        return None

def salvar_trade(symbol, tipo, preco, quantidade, lucro=0.0):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO trades (symbol, tipo, preco, quantidade, lucro, data_hora)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, tipo, preco, quantidade, lucro, data_hora))
        conn.commit()
        conn.close()
        print(f"💾 Trade registrado: {tipo} @ ${preco:.2f}")
    except Exception as e:
        print(f"Erro ao salvar trade: {e}")

def atualizar_status_ia(rsi, potencial, decisao):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        data_hora = datetime.now().strftime("%H:%M:%S")
        
        # Limpa o status antigo e põe o novo (sempre teremos só 1 linha)
        cursor.execute("DELETE FROM status_ia")
        cursor.execute('''
            INSERT INTO status_ia (rsi, potencial, decisao, atualizado_em)
            VALUES (?, ?, ?, ?)
        ''', (rsi, potencial, decisao, data_hora))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar status IA: {e}")