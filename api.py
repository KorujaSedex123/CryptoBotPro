from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
from modules.database import get_connection

# Inicializa o APP
app = FastAPI()

# Configuração de CORS (Permite o Dashboard conectar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "version": "6.0"}

@app.get("/elite")
def get_elite():
    """Retorna a lista de moedas que estão sendo monitoradas (Elite)"""
    try:
        conn = get_connection()
        # Busca moedas que têm status gravado na tabela da IA
        df = pd.read_sql_query("SELECT DISTINCT symbol FROM status_ia", conn)
        conn.close()
        return df['symbol'].tolist()
    except Exception as e:
        print(f"Erro Elite: {e}")
        return []

@app.get("/scan-results")
def get_scan_results():
    """Retorna o placar da IA para o Dashboard"""
    try:
        conn = get_connection()
        # Pega o registro mais recente de cada moeda
        query = """
        SELECT symbol, potencial as lucro, decisao 
        FROM status_ia 
        GROUP BY symbol 
        ORDER BY timestamp DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except:
        return []

@app.get("/stats")
def get_stats(symbol: str):
    """Retorna estatísticas de performance da moeda"""
    try:
        conn = get_connection()
        trades = pd.read_sql_query("SELECT * FROM trades WHERE symbol=?", conn, params=(symbol,))
        conn.close()
        
        lucro_total = trades['lucro'].sum() if not trades.empty else 0.0
        
        return {
            "lucro_total": lucro_total,
            "profit_factor": 1.5, # Placeholder para cálculo futuro
            "sharpe_ratio": 1.2,
            "max_drawdown": 5.0,
            "ultimo_trade": trades.iloc[-1].to_dict() if not trades.empty else {"decisao": "NEUTRO"}
        }
    except:
        return {"lucro_total": 0.0}

@app.get("/history")
def get_history(symbol: str):
    """Retorna histórico de trades para o gráfico"""
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM trades WHERE symbol=? ORDER BY data_hora DESC LIMIT 50", conn, params=(symbol,))
        conn.close()
        return df.to_dict(orient="records")
    except:
        return []

@app.get("/status-bot")
def get_bot_status(symbol: str):
    """Retorna se o bot está comprado ou vendido"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memoria_bot WHERE symbol=?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Índices baseados na criação da tabela em database.py
            return {
                "saldo_disponivel": row[1],
                "posicionado": bool(row[2]),
                "preco_compra": row[3],
                "qtd": row[4]
            }
        return {"posicionado": False, "saldo_disponivel": 0.0}
    except:
        return {"posicionado": False}

@app.get("/bot-control")
def bot_control(status: str):
    """Pausa ou Inicia o Bot (status='true' ou 'false')"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO config_global (chave, valor) VALUES ('bot_rodando', ?)", (status,))
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except:
        return {"status": "error"}

@app.post("/save-config")
def save_config(chave: str, valor: str):
    """Salva configurações (API Keys, Perfil)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO config_global (chave, valor) VALUES (?, ?)", (chave, valor))
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except:
        return {"status": "error"}

@app.post("/panic-sell")
def panic_sell():
    """Aciona o modo de pânico"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO config_global (chave, valor) VALUES ('comando_venda_total', 'true')")
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except:
        return {"status": "error"}

@app.get("/ai-simulation")
def ai_simulation():
    """Simula a análise da IA para o botão de teste"""
    return {
        "recomendacao": "Moderado",
        "volatilidade_detectada": "Média",
        "analise": "O mercado apresenta padrões mistos. A IA recomenda cautela (Perfil Moderado)."
    }