from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd

app = FastAPI()

# Permite que o Next.js (rodando em outra porta) acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "trades.db"

def get_db_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        # Lê os últimos 50 trades
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

@app.get("/stats")
def stats():
    df = get_db_data()
    if df.empty:
        return {"lucro_total": 0, "win_rate": 0, "total_trades": 0}

    lucro_total = df['lucro'].sum()
    total_trades = len(df)
    # Calcula win rate (trades com lucro > 0)
    wins = len(df[df['lucro'] > 0])
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

    return {
        "lucro_total": round(lucro_total, 2),
        "win_rate": round(win_rate, 1),
        "total_trades": total_trades,
        "ultimo_trade": df.iloc[0].to_dict() if not df.empty else None
    }

@app.get("/history")
def history():
    df = get_db_data()
    if df.empty: return []
    return df.to_dict(orient="records")

@app.get("/ia-status")
def ia_status():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM status_ia ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "rsi": row[1],
                "potencial": row[2],
                "decisao": row[3],
                "atualizado_em": row[4]
            }
        else:
            return None
    except:
        return None
    
@app.get("/status-bot")
def status_bot():
    try:
        conn = sqlite3.connect(DB_NAME) # Certifique-se que DB_NAME está correto (trades.db)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        # Lê a memória do bot
        cursor.execute("SELECT saldo, posicao, preco_compra, qtd_btc, preco_maximo FROM memoria_bot WHERE id=1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "saldo_disponivel": row[0],
                "posicionado": bool(row[1]),
                "preco_compra": row[2],
                "qtd_btc": row[3],
                "preco_maximo": row[4] # <--- O dado crucial pro Trailing Stop
            }
        return None
    except Exception as e:
        print(f"Erro API Status: {e}")
        return None