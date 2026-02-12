from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import numpy as np

app = FastAPI()

# Configuração de CORS para o Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "trades.db"
STOP_LOSS = 1.5      
TRAILING_DROP = 0.5

def get_connection():
    """Conexão segura com modo WAL para leitura e escrita simultâneas"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

@app.get("/elite")
def get_elite():
    """Retorna os 3 ativos selecionados pela Elite"""
    try:
        conn = get_connection()
        query = "SELECT symbol FROM status_ia WHERE decisao != 'OBSERVAÇÃO' ORDER BY timestamp DESC LIMIT 3"
        df = pd.read_sql_query(query, conn)
        conn.close()
        lista = df['symbol'].unique().tolist()
        return lista if lista else ["BTC/BRL"]
    except Exception as e:
        print(f"Erro ao buscar Elite: {e}")
        return []

@app.get("/stats")
def stats(symbol: str = Query("BTC/BRL")):
    """Estatísticas de performance quantitativa por ativo"""
    try:
        conn = get_connection()
        query = "SELECT lucro FROM trades WHERE symbol=? AND tipo='VENDA' ORDER BY id ASC"
        df = pd.read_sql_query(query, conn, params=(symbol,))
        
        cursor = conn.cursor()
        cursor.execute("SELECT decisao FROM status_ia WHERE symbol=? ORDER BY timestamp DESC LIMIT 1", (symbol,))
        ultima_decisao = cursor.fetchone()
        conn.close()

        if df.empty:
            return {
                "lucro_total": 0, "win_rate": 0, "total_trades": 0,
                "profit_factor": 0, "max_drawdown": 0, "sharpe_ratio": 0,
                "ultimo_trade": {"decisao": ultima_decisao[0] if ultima_decisao else "AGUARDAR"}
            }

        lucro_total = df['lucro'].sum()
        total_trades = len(df)
        wins = df[df['lucro'] > 0]['lucro']
        losses = df[df['lucro'] < 0]['lucro']
        win_rate = (len(wins) / total_trades) * 100

        bruto_ganho = wins.sum()
        bruto_perda = abs(losses.sum())
        profit_factor = round(bruto_ganho / bruto_perda, 2) if bruto_perda > 0 else round(bruto_ganho, 2)

        equity_curve = 100 + df['lucro'].cumsum()
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak
        max_drawdown = round(abs(drawdown.min()) * 100, 2) if not drawdown.empty else 0
        sharpe = round(df['lucro'].mean() / df['lucro'].std(), 2) if df['lucro'].std() > 0 else 0

        return {
            "lucro_total": round(lucro_total, 2),
            "win_rate": round(win_rate, 1),
            "total_trades": total_trades,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "ultimo_trade": {"decisao": ultima_decisao[0] if ultima_decisao else "AGUARDAR"}
        }
    except Exception as e:
        print(f"Erro Stats: {e}")
        return {"lucro_total": 0, "win_rate": 0, "total_trades": 0}

@app.get("/equity")
def equity(symbol: str = Query("BTC/BRL")):
    """Retorna a curva de patrimônio filtrada"""
    try:
        conn = get_connection()
        query = "SELECT data_hora, lucro FROM trades WHERE tipo='VENDA' AND symbol=? ORDER BY data_hora ASC"
        df = pd.read_sql_query(query, conn, params=(symbol,))
        conn.close()
        if df.empty:
            return [{"time": int(pd.Timestamp.now().timestamp()), "value": 100.0}]
        df['time'] = pd.to_datetime(df['data_hora']).view('int64') // 10**9
        df['value'] = 100.0 + df['lucro'].cumsum()
        return df[['time', 'value']].to_dict(orient="records")
    except:
        return []

@app.get("/history")
def history(symbol: str = Query("BTC/BRL")):
    """Histórico de ordens"""
    try:
        conn = get_connection()
        query = "SELECT * FROM trades WHERE symbol=? ORDER BY id DESC LIMIT 20"
        df = pd.read_sql_query(query, conn, params=(symbol,))
        conn.close()
        return df.to_dict(orient="records")
    except:
        return []

@app.get("/ia-status")
def ia_status(symbol: str = Query("BTC/BRL")):
    """Status atual da Mente da IA"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT rsi, potencial, decisao, timestamp FROM status_ia WHERE symbol=? ORDER BY timestamp DESC LIMIT 1", (symbol,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"rsi": row[0], "potencial": row[1], "decisao": row[2], "atualizado_em": row[3]}
        return None
    except:
        return None

@app.get("/scan-results")
def get_scan_results():
    """Retorna o resultado do backtest de todas as moedas"""
    try:
        conn = get_connection()
        query = "SELECT symbol, potencial as lucro, decisao FROM status_ia GROUP BY symbol ORDER BY potencial DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except:
        return []

@app.get("/status-bot")
def status_bot(symbol: str = Query("BTC/BRL")):
    """Memória de posição com cálculo de Stop em tempo real"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT saldo, posicao, preco_compra, qtd_btc, preco_maximo FROM memoria_bot WHERE symbol=?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            posicionado = bool(row[1])
            preco_compra = row[2]
            # Fallback: Se o preco_maximo for nulo ou zero, usa o preco_compra
            preco_maximo = preco_compra if (row[4] is None or row[4] == 0) else row[4]
            
            # Cálculo dos Gatilhos de Saída
            stop_trailing = preco_maximo * (1 - (TRAILING_DROP / 100))
            stop_fixo = preco_compra * (1 - (STOP_LOSS / 100))
            preco_stop_ativo = max(stop_trailing, stop_fixo)

            return {
                "saldo_disponivel": row[0],
                "posicionado": posicionado,
                "preco_compra": preco_compra,
                "qtd_btc": row[3],
                "preco_maximo": preco_maximo,
                "preco_stop": round(preco_stop_ativo, 2)
            }
        return None
    except Exception as e:
        print(f"Erro Status Bot: {e}")
        return None

@app.get("/trigger-report")
def trigger_report():
    """Gatilho manual para o Discord"""
    try:
        from modules.database import obter_resumo_diario
        import modules.notifier as notifier
        resumo = obter_resumo_diario()
        notifier.enviar_relatorio_diario(resumo)
        return {"status": "sucesso", "mensagem": "Relatório enviado para o Discord!"}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}