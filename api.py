from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "trades.db"

def get_connection():
    """Conexão segura com WAL"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

@app.get("/equity")
def equity():
    """Retorna a curva de crescimento do patrimônio"""
    try:
        conn = get_connection()
        # Pegamos apenas as vendas (onde o lucro é realizado)
        df = pd.read_sql_query("SELECT data_hora, lucro FROM trades WHERE tipo='VENDA' ORDER BY data_hora ASC", conn)
        conn.close()

        if df.empty:
            # Se não tiver trade, retorna ponto inicial
            return [{"time": pd.Timestamp.now().timestamp(), "value": 100.0}]

        # 1. Converter data para Timestamp (Segundos)
        df['time'] = pd.to_datetime(df['data_hora']).astype(int) // 10 ** 9
        
        # 2. Calcular o Saldo Acumulado (Começando de 100 reais)
        # Saldo = 100 + Soma Acumulada dos Lucros
        df['value'] = 100.0 + df['lucro'].cumsum()

        # 3. Retornar no formato do gráfico
        return df[['time', 'value']].to_dict(orient="records")
    except Exception as e:
        print(f"Erro Equity: {e}")
        return []

@app.get("/stats")
def stats():
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC LIMIT 50", conn)
        conn.close()
        
        if df.empty:
            return {"lucro_total": 0, "win_rate": 0, "total_trades": 0}

        lucro_total = df['lucro'].sum()
        total_trades = len(df)
        wins = len(df[df['lucro'] > 0])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

        return {
            "lucro_total": round(lucro_total, 2),
            "win_rate": round(win_rate, 1),
            "total_trades": total_trades,
            "ultimo_trade": df.iloc[0].to_dict() if not df.empty else None
        }
    except:
        return {"lucro_total": 0, "win_rate": 0, "total_trades": 0}

@app.get("/history")
def history():
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC LIMIT 20", conn)
        conn.close()
        if df.empty: return []
        return df.to_dict(orient="records")
    except:
        return []

@app.get("/ia-status")
def ia_status():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM status_ia ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"rsi": row[1], "potencial": row[2], "decisao": row[3], "atualizado_em": row[4]}
        return None
    except:
        return None

@app.get("/status-bot")
def status_bot():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT saldo, posicao, preco_compra, qtd_btc, preco_maximo FROM memoria_bot WHERE id=1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "saldo_disponivel": row[0],
                "posicionado": bool(row[1]),
                "preco_compra": row[2],
                "qtd_btc": row[3],
                "preco_maximo": row[4]
            }
        return None
    except:
        return None