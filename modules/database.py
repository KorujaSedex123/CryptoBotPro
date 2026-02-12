import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "trades.db"

def get_connection():
    """Retorna conexão com modo WAL ativado para permitir leitura/escrita simultâneas"""
    conn = sqlite3.connect(DB_NAME)
    # Ativa o modo WAL para evitar 'database is locked'
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memoria_bot (
            symbol TEXT PRIMARY KEY,
            saldo REAL,
            posicao BOOLEAN,
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

def criar_tabela_configs():
    """Cria tabela para configurações globais e API Keys"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config_global (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)
    # Valores padrão iniciais
    configs_padrao = [
        ('perfil_risco', 'moderado'),
        ('bot_rodando', 'true'),
        ('modo_producao', 'false'),
        ('comando_venda_total', 'false')
    ]
    cursor.executemany("INSERT OR IGNORE INTO config_global VALUES (?, ?)", configs_padrao)
    conn.commit()
    conn.close()

def salvar_trade(symbol, tipo, preco, quantidade, lucro):
    """Regista uma operação de compra ou venda no histórico"""
    conn = get_connection()
    cursor = conn.cursor()
    data_hora = datetime.now().isoformat()
    cursor.execute("INSERT INTO trades (symbol, tipo, preco, quantidade, lucro, data_hora) VALUES (?, ?, ?, ?, ?, ?)", 
                   (symbol, tipo, preco, quantidade, lucro, data_hora))
    conn.commit()
    conn.close()

def salvar_estado(symbol, saldo, posicao, preco_compra, qtd_btc, preco_maximo):
    """Salva ou atualiza o estado de um robô específico usando o símbolo"""
    conn = get_connection()
    cursor = conn.cursor()
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
        cursor.execute("SELECT saldo, posicao, preco_compra, qtd_btc, preco_maximo FROM memoria_bot WHERE symbol=?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "saldo": row[0], 
                "posicao": bool(row[1]), 
                "preco_compra": row[2], 
                "qtd_btc": row[3], 
                "preco_maximo": row[4]
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

def carregar_configs_globais():
    """Busca todas as configurações da tabela config_global e retorna um dict"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chave, valor FROM config_global")
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}
    except Exception as e:
        print(f"⚠️ Erro ao carregar configs do banco: {e}")
        return {}
    
def resetar_comando_venda():
    """Desliga a flag de panic sell no banco após a execução"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE config_global SET valor='false' WHERE chave='comando_venda_total'")
        conn.commit()
        conn.close()
        print("✅ Comando de Panic Sell resetado com sucesso.")
    except Exception as e:
        print(f"⚠️ Erro ao resetar panic sell: {e}")

def obter_ultimo_saldo(symbol):
    """Busca o saldo final da última operação deste ativo ou retorna 100.0"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Tenta pegar o saldo da memória
        cursor.execute("SELECT saldo FROM memoria_bot WHERE symbol=?", (symbol,))
        row = cursor.fetchone()
        
        if row:
            return float(row[0])
        
        # Se não tiver memória, tenta pegar do último trade de VENDA
        cursor.execute("SELECT saldo FROM trades WHERE symbol=? AND tipo='VENDA' ORDER BY id DESC LIMIT 1", (symbol,))
        row_trade = cursor.fetchone()
        
        if row_trade:
            return float(row_trade[0])
            
        return 100.0 # Saldo inicial padrão se nunca operou
    except Exception as e:
        return 100.0

def obter_resumo_diario():
    """Calcula o lucro total e estatísticas de trades do dia atual"""
    try:
        conn = get_connection()
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
        print(f"Erro ao gerar resumo no banco: {e}")
        return None