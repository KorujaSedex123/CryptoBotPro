import sqlite3
import json

DB_NAME = "trades.db"

def get_connection():
    """Retorna conexão com modo WAL ativado para evitar travamentos"""
    conn = sqlite3.connect(DB_NAME)
    # Ativa o modo WAL (Leitura e Escrita simultâneas)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def criar_tabelas():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Trades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            tipo TEXT,
            preco REAL,
            quantidade REAL,
            lucro REAL,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Memória (Estado do Bot)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memoria_bot (
            id INTEGER PRIMARY KEY,
            saldo REAL,
            posicao INTEGER,
            preco_compra REAL,
            qtd_btc REAL,
            preco_maximo REAL
        )
    ''')

    # Tabela da Mente da IA (Novo Cérebro V3)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS status_ia (
            id INTEGER PRIMARY KEY,
            rsi REAL,
            potencial REAL, -- Agora usado como SCORE
            decisao TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inicializa memória se não existir
    cursor.execute("SELECT count(*) FROM memoria_bot")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO memoria_bot (id, saldo, posicao, preco_compra, qtd_btc, preco_maximo) VALUES (1, 100.0, 0, 0, 0, 0)")
        
    # Inicializa IA se não existir
    cursor.execute("SELECT count(*) FROM status_ia")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO status_ia (id, rsi, potencial, decisao) VALUES (1, 50, 0, 'AGUARDAR')")

    conn.commit()
    conn.close()

def salvar_trade(symbol, tipo, preco, quantidade, lucro):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO trades (symbol, tipo, preco, quantidade, lucro) VALUES (?, ?, ?, ?, ?)", 
                   (symbol, tipo, preco, quantidade, lucro))
    conn.commit()
    conn.close()

def salvar_estado(saldo, posicao, preco_compra, qtd_btc, preco_maximo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE memoria_bot 
        SET saldo=?, posicao=?, preco_compra=?, qtd_btc=?, preco_maximo=? 
        WHERE id=1
    ''', (saldo, int(posicao), preco_compra, qtd_btc, preco_maximo))
    conn.commit()
    conn.close()

def carregar_estado():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memoria_bot WHERE id=1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'saldo': row[1],
                'posicao': row[2],
                'preco_compra': row[3],
                'qtd_btc': row[4],
                'preco_maximo': row[5]
            }
        return None
    except:
        return None

def atualizar_status_ia(rsi, score, decisao):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE status_ia 
        SET rsi=?, potencial=?, decisao=?, timestamp=CURRENT_TIMESTAMP 
        WHERE id=1
    ''', (rsi, score, decisao))
    conn.commit()
    conn.close()