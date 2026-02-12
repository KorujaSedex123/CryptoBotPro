import pandas as pd
import talib
import numpy as np

def analisar_multitimeframe(candles_1m, candles_15m, config=None):
    """
    Analisa o mercado com parâmetros dinâmicos calibrados pelo Backtest.
    Se config for None, utiliza os padrões de segurança.
    """
    # Configuração Padrão (Fallback de Segurança)
    if config is None:
        config = {
            'rsi_threshold': 30,
            'min_score': 6,
            'ma_period': 20
        }

    # Conversão para Dataframe para processamento TA-Lib
    df_1m = pd.DataFrame(candles_1m, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    df_15m = pd.DataFrame(candles_15m, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    
    # --- INDICADORES ---
    # RSI (1m) para detecção de sobrevenda
    rsi = talib.RSI(df_1m['c'], timeperiod=14).iloc[-1]
    
    # Médias Móveis (Tendência Macro 15m)
    ma_fast = talib.EMA(df_15m['c'], timeperiod=config['ma_period']).iloc[-1]
    ma_slow = talib.EMA(df_15m['c'], timeperiod=50).iloc[-1]
    tendencia_macro = "ALTA" if ma_fast > ma_slow else "BAIXA"
    
    # Padrões de Candle (TA-Lib)
    hammer = talib.CDLHAMMER(df_1m['o'], df_1m['h'], df_1m['l'], df_1m['c']).iloc[-1]
    engulfing = talib.CDLENGULFING(df_1m['o'], df_1m['h'], df_1m['l'], df_1m['c']).iloc[-1]

    # --- SISTEMA DE SCORE (CONFLUÊNCIA) ---
    score = 0
    motivos = []

    if tendencia_macro == "ALTA":
        score += 3
        motivos.append("Tendência Macro Favorável (15m)")

    if rsi <= config['rsi_threshold']:
        score += 4
        motivos.append(f"RSI Sobrevendido (<{config['rsi_threshold']})")
    
    if hammer != 0 or engulfing != 0:
        score += 3
        motivos.append("Padrão de Reversão Detectado")

    # Decisão baseada no score dinâmico definido na inicialização
    decisao = "COMPRA" if score >= config['min_score'] else "AGUARDAR"

    return {
        "score": score,
        "decisao": decisao,
        "rsi": rsi,
        "tendencia_macro": tendencia_macro,
        "motivos": motivos
    }