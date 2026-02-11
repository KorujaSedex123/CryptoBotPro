import pandas as pd
import talib 
import numpy as np

def analisar_multitimeframe(candles_1m, candles_15m):
    """
    Analisa 15m (Tendência) + 1m (Padrões TA-Lib + Indicadores).
    Retorna decisão robusta.
    """
    
    # --- 1. PREPARAÇÃO DOS DADOS ---
    # DataFrame 15 Minutos (Macro)
    df_15m = pd.DataFrame(candles_15m, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    close_15m = df_15m['close'].to_numpy(dtype=float)
    
    # DataFrame 1 Minuto (Micro)
    df_1m = pd.DataFrame(candles_1m, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    close_1m = df_1m['close'].to_numpy(dtype=float)
    high_1m = df_1m['high'].to_numpy(dtype=float)
    low_1m = df_1m['low'].to_numpy(dtype=float)
    open_1m = df_1m['open'].to_numpy(dtype=float)
    vol_1m = df_1m['vol'].to_numpy(dtype=float)

    # --- 2. ANÁLISE MACRO (15m) ---
    # Tendência de Alta se preço > EMA 21
    ema21_macro = talib.EMA(close_15m, timeperiod=21)[-1]
    preco_macro = close_15m[-1]
    tendencia_alta = preco_macro > ema21_macro

    # --- 3. ANÁLISE MICRO (1m) - INDICADORES ---
    # RSI
    rsi = talib.RSI(close_1m, timeperiod=14)[-1]
    
    # Bandas de Bollinger
    upper, middle, lower = talib.BBANDS(close_1m, timeperiod=20)
    bb_lower = lower[-1]
    
    # Volume Médio
    vol_medio = talib.SMA(vol_1m, timeperiod=20)[-1]
    vol_atual = vol_1m[-1]

    # --- 4. ANÁLISE MICRO (1m) - PADRÕES DE VELAS (TA-LIB) ---
    # Retorna 100 se encontrou padrão de alta
    engolfo = talib.CDLENGULFING(open_1m, high_1m, low_1m, close_1m)[-1]
    martelo = talib.CDLHAMMER(open_1m, high_1m, low_1m, close_1m)[-1]
    morning = talib.CDLMORNINGSTAR(open_1m, high_1m, low_1m, close_1m)[-1]
    harami = talib.CDLHARAMI(open_1m, high_1m, low_1m, close_1m)[-1]

    # --- 5. SISTEMA DE SCORE ---
    score = 0
    motivos = []

    # Fator Crítico: Macro Tendência
    if tendencia_alta:
        score += 2
        motivos.append("Tendência 15m Alta")
    else:
        score -= 2
        motivos.append("Contra Tendência 15m")

    # Indicadores Técnicos
    if rsi < 30:
        score += 2
        motivos.append("RSI < 30")
    elif rsi < 40:
        score += 1
    elif rsi > 70:
        score -= 2 # Muito caro

    if close_1m[-1] < bb_lower:
        score += 1
        motivos.append("Abaixo Bollinger")

    if vol_atual > vol_medio:
        score += 1
        motivos.append("Volume Alto")

    # Padrões de Candlestick (O "Sinal Divino")
    if engolfo == 100:
        score += 3
        motivos.append("🕯️ Engolfo de Alta")
    if martelo == 100:
        score += 2
        motivos.append("🕯️ Martelo")
    if morning == 100:
        score += 3
        motivos.append("🕯️ Morning Star")
    if harami == 100:
        score += 2
        motivos.append("🕯️ Harami Bullish")

    # --- DECISÃO ---
    decisao = "AGUARDAR"
    
    # Precisamos de 5 pontos para entrar (Ex: Tendência + RSI + Padrão)
    if score >= 5:
        decisao = "COMPRA"

    return {
        "decisao": decisao,
        "score": score,
        "rsi": rsi,
        "motivos": motivos,
        "preco_atual": close_1m[-1],
        "tendencia_macro": "ALTA" if tendencia_alta else "BAIXA"
    }