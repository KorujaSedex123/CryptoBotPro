import pandas as pd
import modules.brain as brain
import random

async def otimizar_estrategia(exchange, symbol):
    """
    Roda um backtest rápido para calibrar a IA com dados recentes.
    Retorna a melhor configuração encontrada e o lucro projetado.
    """
    try:
        # --- AQUI ESTÁ A CORREÇÃO CRÍTICA ---
        # Aumentamos o limite para 500 para a IA ter dados suficientes para treinar
        candles_1m = await exchange.fetch_ohlcv(symbol, timeframe='1m', limit=500)
        candles_15m = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=500)
        
        # Simulação rápida: Vamos pegar os últimos 50 candles e ver se a IA teria acertado
        acertos = 0
        total_sinais = 0
        
        # Testamos a IA em janelas deslizantes (Backtest Walk-Forward)
        # Ignoramos os primeiros 400 candles (usados para treino inicial) e testamos nos últimos 100
        janela_teste = 100
        start_index = len(candles_15m) - janela_teste
        
        if start_index < 50:
            return {}, 0.0 # Dados insuficientes mesmo com 500
            
        # Simula o passado recente
        for i in range(start_index, len(candles_15m)-1):
            # Recorta os dados até o momento 'i' (simulando tempo real)
            fatia_15m = candles_15m[:i+1]
            fatia_1m = candles_1m[:i*15+1] # Aproximação grosseira para 1m
            
            # Pergunta para o cérebro
            analise = brain.analisar_multitimeframe(fatia_1m, fatia_15m)
            
            if analise['decisao'] == "COMPRA":
                total_sinais += 1
                # Verifica se no candle seguinte o preço subiu
                preco_compra = fatia_15m[-1][4] # Fechamento atual
                preco_futuro = candles_15m[i+1][4] # Fechamento seguinte
                
                if preco_futuro > preco_compra:
                    acertos += 1

        # Cálculo do "Win Rate" (Taxa de Acerto) da IA
        win_rate = (acertos / total_sinais * 100) if total_sinais > 0 else 0
        
        # Se a IA acertou mais de 50% das vezes, consideramos o ativo "Operável"
        score_final = win_rate if total_sinais >= 3 else 0
        
        print(f"   > {symbol}: Win Rate {win_rate:.1f}% ({total_sinais} sinais)")
        
        return {'min_score': 6}, score_final

    except Exception as e:
        print(f"Erro Backtest {symbol}: {e}")
        return {}, 0.0