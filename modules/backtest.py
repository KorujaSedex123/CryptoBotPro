import pandas as pd
from modules.brain import analisar_multitimeframe

async def otimizar_estrategia(exchange, symbol):
    """
    Roda um backtest nos dados recentes e retorna o melhor setup e o lucro obtido.
    """
    try:
        # Busca 1000 velas para um backtest mais robusto na inicialização
        candles = await exchange.fetch_ohlcv(symbol, timeframe='1m', limit=1000)
        candles_15m = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
        
        melhor_lucro = -999
        melhor_config = {'rsi_threshold': 30, 'min_score': 6, 'ma_period': 20}
        
        # Otimização em grade (Grid Search)
        for rsi_test in [25, 30, 35]:
            for score_test in [6, 7]:
                lucro_simulado = 0
                posicionado = False
                preco_entrada = 0
                
                for i in range(50, len(candles) - 1):
                    slice_1m = candles[i-50:i]
                    analise = analisar_multitimeframe(slice_1m, candles_15m, config={
                        'rsi_threshold': rsi_test, 'min_score': score_test, 'ma_period': 20
                    })
                    
                    if not posicionado and analise['decisao'] == "COMPRA":
                        preco_entrada = candles[i][4]
                        posicionado = True
                    elif posicionado:
                        preco_atual = candles[i][4]
                        lucro_pct = ((preco_atual - preco_entrada) / preco_entrada) * 100
                        if lucro_pct >= 0.5 or lucro_pct <= -1.0:
                            lucro_simulado += (lucro_pct - 0.2)
                            posicionado = False
                
                if lucro_simulado > melhor_lucro:
                    melhor_lucro = lucro_simulado
                    melhor_config = {'rsi_threshold': rsi_test, 'min_score': score_test, 'ma_period': 20}
        
        return melhor_config, melhor_lucro
    except Exception as e:
        print(f"Erro Backtest {symbol}: {e}")
        return {'rsi_threshold': 30, 'min_score': 6, 'ma_period': 20}, -1.0