import sqlite3
from datetime import datetime
import json

DB_NAME = "trades.db"

def get_connection():
    """Retorna conexão com modo WAL ativado para permitir leitura/escrita simultâneas"""
    conn = sqlite3.connect(DB_NAME)
    # Ativa o modo WAL (Write-Ahead Logging) para evitar o erro 'database is locked'
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def criar_tabelas():
    """Cria a estrutura de tabelas compatível com múltiplos ativos"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Histórico de Trades (Geral)
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
    
    # 2. Memória do Bot (Estado Independente por Ativo)
    # O 'symbol' agora é a PRIMARY KEY
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memoria_bot (
            symbol TEXT PRIMARY KEY,
            saldo REAL,
            posicao INTEGER,
            preco_compra REAL,
            qtd_btc REAL,
            preco_maximo REAL
        )
    ''')

    # 3. Mente da IA (Score e Indicadores por Ativo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS status_ia (
            symbol TEXT PRIMARY KEY,
            rsi REAL,
            potencial REAL, -- Score (0 a 10)
            decisao TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def salvar_trade(symbol, tipo, preco, quantidade, lucro):
    """Regista uma operação de compra ou venda no histórico"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO trades (symbol, tipo, preco, quantidade, lucro) VALUES (?, ?, ?, ?, ?)", 
                   (symbol, tipo, preco, quantidade, lucro))
    conn.commit()
    conn.close()

def salvar_estado(symbol, saldo, posicao, preco_compra, qtd_btc, preco_maximo):
    """Salva ou atualiza o estado de um robô específico usando o símbolo"""
    conn = get_connection()
    cursor = conn.cursor()
    # INSERT OR REPLACE garante que se o ativo não existir ele cria, se existir ele atualiza
    cursor.execute('''
        INSERT OR REPLACE INTO memoria_bot (symbol, saldo, posicao, preco_compra, qtd_btc, preco_maximo)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (symbol, saldo, int(posicao), preco_compra, qtd_btc, preco_maximo))
    conn.commit()
    conn.close()

def carregar_estado(symbol):
    """Recupera a memória de um ativo específico para retoma após reinicialização"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memoria_bot WHERE symbol=?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'symbol': row[0],
                'saldo': row[1],
                'posicao': bool(row[2]),
                'preco_compra': row[3],
                'qtd_btc': row[4],
                'preco_maximo': row[5]
            }
        return None
    except Exception as e:
        print(f"Erro ao carregar estado de {symbol}: {e}")
        return None

def atualizar_status_ia(symbol, rsi, score, decisao):
    """Atualiza os indicadores e a decisão da IA para exibição no Dashboard"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO status_ia (symbol, rsi, potencial, decisao, timestamp)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (symbol, rsi, score, decisao))
    conn.commit()
    conn.close()

def obter_resumo_diario():
    """Calcula o lucro total e estatísticas de trades do dia atual"""
    try:
        conn = sqlite3.connect("trades.db")
        hoje = datetime.now().strftime('%Y-%m-%d')
        
        query = """
            SELECT 
                symbol,
                SUM(lucro) as lucro_total,
                COUNT(*) as total_trades,
                COUNT(CASE WHEN lucro > 0 THEN 1 END) as wins
            FROM trades 
            WHERE data_hora LIKE ? AND tipo='VENDA'
            GROUP BY symbol
        """
        df = pd.read_sql_query(query, conn, params=(f"{hoje}%",))
        conn.close()
        return df
    except Exception as e:
        print(f"Erro ao gerar resumo: {e}")
        return None