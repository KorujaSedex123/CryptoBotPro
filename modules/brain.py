import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange, BollingerBands
from sklearn.ensemble import RandomForestClassifier

def preparar_dados(candles):
    """
    Transforma a lista de candles bruta em um DataFrame com indicadores técnicos (Features).
    Usando a biblioteca 'ta' (mais estável que pandas_ta).
    """
    # Cria o DataFrame
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Garante que os dados sejam float
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    
    # --- Engenharia de Features (Indicadores com 'ta') ---
    
    # 1. RSI (Momentum)
    rsi_indicator = RSIIndicator(close=df['close'], window=14)
    df['RSI'] = rsi_indicator.rsi()
    
    # 2. MACD (Tendência)
    macd = MACD(close=df['close'])
    df['MACD_line'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_hist'] = macd.macd_diff() # O histograma é o mais importante para IA
    
    # 3. ATR (Volatilidade)
    atr_indicator = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['ATR'] = atr_indicator.average_true_range()
    
    # 4. Bollinger Bands (%B)
    bb_indicator = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BBP'] = bb_indicator.bollinger_pband()

    # Remove linhas com NaN (os primeiros candles não têm indicadores calculados)
    df.dropna(inplace=True)
    return df

def treinar_e_prever(df):
    """
    Treina um modelo Random Forest com os dados recentes e prevê a direção do próximo candle.
    """
    try:
        # --- Definição do Alvo (Target) ---
        # Queremos prever se o fechamento do PRÓXIMO candle será maior que o atual.
        df['Target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # O último candle do DF é o "agora". Ele não tem Target.
        candle_atual = df.iloc[[-1]].copy()
        
        # Dados de treino: Tudo menos o último candle
        dados_treino = df.iloc[:-1].copy()

        # Features: Usamos apenas os indicadores calculados
        features = ['RSI', 'ATR', 'BBP', 'MACD_line', 'MACD_signal', 'MACD_hist'] 
        
        # Verifica se temos dados suficientes para treino
        if len(dados_treino) < 50:
            return 0.5, "Dados insuficientes"

        X = dados_treino[features]
        y = dados_treino['Target']
        
        # --- Treinamento ---
        model = RandomForestClassifier(n_estimators=100, min_samples_split=5, random_state=42, n_jobs=-1)
        model.fit(X, y)
        
        # --- Previsão ---
        # Probabilidade de ser classe 1 (Alta)
        probabilidade_alta = model.predict_proba(candle_atual[features])[0][1]
        
        return probabilidade_alta, "Random Forest AI"

    except Exception as e:
        print(f"Erro ML: {e}")
        return 0.5, "Erro ML"

def analisar_multitimeframe(candles_1m, candles_15m, config=None):
    """
    Substitui a lógica antiga de If/Else por uma análise baseada em Probabilidade (Machine Learning).
    """
    if config is None:
        config = {'min_score': 6}

    # Usamos o timeframe de 15m para a IA (menos ruído)
    df_15m = preparar_dados(candles_15m)
    
    # Chama o cérebro de ML
    probabilidade, motivo_ia = treinar_e_prever(df_15m)
    
    # Converte probabilidade (0.0 a 1.0) para Score (0 a 10)
    score = round(probabilidade * 10, 1)
    
    # Pega RSI atual apenas para exibição
    rsi_atual = df_15m['RSI'].iloc[-1] if 'RSI' in df_15m else 50
    
    motivos = [f"{motivo_ia}: Prob. Alta {probabilidade*100:.1f}%"]
    
    # --- Filtro de Segurança Híbrido ---
    if rsi_atual > 75 and score > 6:
        score -= 2
        motivos.append("Penalidade: RSI Esticado (>75)")
        
    # Decisão Final
    min_score = config.get('min_score', 6)
    decisao = "COMPRA" if score >= min_score else "AGUARDAR"

    return {
        "score": score,
        "decisao": decisao,
        "rsi": round(rsi_atual, 2),
        "tendencia_macro": "IA-Driven",
        "motivos": motivos
    }