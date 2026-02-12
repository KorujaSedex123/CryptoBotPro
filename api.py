import asyncio
import json
import os
import logging
from datetime import datetime
import ccxt.async_support as ccxt 
import websockets
from dotenv import load_dotenv

# Módulos Locais
from modules.database import (
    criar_tabelas, salvar_trade, atualizar_status_ia, 
    salvar_estado, carregar_estado, carregar_configs_globais, 
    criar_tabela_configs, resetar_comando_venda, obter_ultimo_saldo
)
from modules.backtest import otimizar_estrategia 
import modules.brain as brain
import modules.notifier as notifier

logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(message)s')
load_dotenv()

# --- CONFIGURAÇÕES GLOBAIS ---
PERFIS = {
    "conservador": { "STOP_LOSS": 1.0, "TRAILING_DROP": 0.2, "LUCRO_MINIMO": 0.1, "SCORE_MINIMO": 8, "RSI_COMPRA": 30 },
    "moderado":    { "STOP_LOSS": 1.5, "TRAILING_DROP": 0.5, "LUCRO_MINIMO": 0.2, "SCORE_MINIMO": 6, "RSI_COMPRA": 35 },
    "agressivo":   { "STOP_LOSS": 3.0, "TRAILING_DROP": 1.0, "LUCRO_MINIMO": 0.4, "SCORE_MINIMO": 5, "RSI_COMPRA": 45 }
}

CANDIDATOS = os.getenv('TRADING_PAIRS', 'BTC/BRL,ETH/BRL,SOL/BRL,BNB/BRL,ADA/BRL').split(',')
LIMITE_ELITE = 3  
TAXA_TOTAL = 0.2 # Taxa estimada (inclui spread + taxas da exchange)

ESTADO = {
    "ativos_ativos": [],
    "ativos_data": {},
    "precos_live": {},
    "configs_ia": {},
    "bot_rodando": True,
    "modo_producao": False,
    "perfil_ativo": "moderado",
    "saldo_brl_real": 0.0 # Novo campo para saldo real da Binance
}

# --- FUNÇÃO DE COMANDO E SINCRONIZAÇÃO ---
async def sincronizar_configs(exchange):
    global ESTADO
    while True:
        try:
            db_configs = carregar_configs_globais()
            ESTADO["bot_rodando"] = db_configs.get('bot_rodando') == 'true'
            ESTADO["modo_producao"] = db_configs.get('modo_producao') == 'true'
            ESTADO["perfil_ativo"] = db_configs.get('perfil_risco', 'moderado')
            
            # COMANDO DE PÂNICO (VENDA TOTAL)
            if db_configs.get('comando_venda_total') == 'true':
                print("\n🚨 COMANDO DE EMERGÊNCIA: Vendendo todos os ativos!")
                for sym in ESTADO["ativos_ativos"]:
                    # Tenta vender se tiver posição na memória OU saldo na exchange (se modo real)
                    if ESTADO["ativos_data"][sym]["posicao"]:
                        await executar_venda(sym, "PANIC BUTTON", exchange)
                resetar_comando_venda()
                
            # ATUALIZA SALDO REAL BRL (Se estiver em produção)
            if ESTADO["modo_producao"]:
                try:
                    balance = await exchange.fetch_balance()
                    ESTADO["saldo_brl_real"] = balance['total'].get('BRL', 0.0)
                except Exception as e:
                    print(f"Erro ao ler saldo Binance: {e}")

        except Exception as e:
            logging.error(f"Erro Sync: {e}")
        await asyncio.sleep(10)

# --- EXECUÇÃO (O CORAÇÃO DO MODO REAL) ---

async def executar_venda(symbol, motivo, exchange):
    dados = ESTADO["ativos_data"][symbol]
    preco_atual = ESTADO["precos_live"][symbol]
    qtd = dados["qtd"]
    
    lucro_reais = 0.0
    sucesso = False

    # 1. TENTATIVA DE VENDA REAL NA BINANCE
    if ESTADO["modo_producao"]:
        try:
            print(f"🔄 Enviando ordem de VENDA para Binance: {symbol}...")
            # Envia ordem a mercado
            ordem = await exchange.create_market_sell_order(symbol, qtd)
            
            # Pega o preço real que foi executado lá na Binance
            preco_execucao = float(ordem['average']) if ordem.get('average') else preco_atual
            lucro_reais = (preco_execucao * qtd) - (dados["preco_compra"] * qtd)
            
            notifier.enviar_discord(f"💰 VENDA REAL: {symbol}", f"Preço: {preco_execucao}\nLucro: R$ {lucro_reais:.2f}\nMotivo: {motivo}", 0x00ff00)
            sucesso = True
        except Exception as e:
            notifier.enviar_discord(f"❌ ERRO VENDA REAL: {symbol}", str(e), 0xff0000)
            print(f"Erro Binance Venda: {e}")
            return # Aborta se falhar na real
    else:
        # SIMULAÇÃO
        valor_bruto = qtd * preco_atual
        lucro_reais = (valor_bruto - (dados["qtd"] * dados["preco_compra"])) * (1 - (TAXA_TOTAL/100))
        dados["saldo"] = valor_bruto * (1 - (TAXA_TOTAL/100)) # Reinveste o lucro simulado
        sucesso = True

    # 2. ATUALIZAÇÃO DO BANCO DE DADOS (Só se vendeu com sucesso)
    if sucesso:
        dados["posicao"] = False
        dados["qtd"] = 0
        salvar_estado(symbol, dados["saldo"], False, 0, 0, 0)
        salvar_trade(symbol, "VENDA", preco_atual, qtd, lucro_reais)
        
        if not ESTADO["modo_producao"]:
            cor = 0x00ff00 if lucro_reais > 0 else 0xff0000
            notifier.enviar_discord(f"🚨 VENDA SIMULADA: {symbol}", f"Motivo: {motivo}\nLucro: R$ {lucro_reais:.2f}", cor)

async def executar_compra(symbol, analise, exchange):
    dados = ESTADO["ativos_data"][symbol]
    preco_atual = ESTADO["precos_live"][symbol]
    
    qtd_compra = 0.0
    sucesso = False
    
    # 1. TENTATIVA DE COMPRA REAL NA BINANCE
    if ESTADO["modo_producao"]:
        try:
            # Verifica saldo em BRL
            balance = await exchange.fetch_balance()
            saldo_disponivel = balance['free'].get('BRL', 0.0)
            
            # Define quanto usar (ex: 95% do saldo disponível dividido pelo nº de ativos livres)
            # Simplificação: Usa R$ 50,00 ou o saldo disponível, o que for menor, pra testar
            valor_investimento = min(saldo_disponivel, 100.0) 
            
            if valor_investimento < 20.0: # Mínimo da Binance costuma ser uns 10 USD/BRL
                print(f"⚠️ Saldo insuficiente para compra real de {symbol}: R$ {saldo_disponivel}")
                return

            # Calcula quantidade aproximada
            qtd_estimada = valor_investimento / preco_atual
            
            print(f"🔄 Enviando ordem de COMPRA para Binance: {symbol}...")
            # Ordem de compra a mercado (usando quoteOrderQty para especificar valor em BRL)
            params = {'quoteOrderQty': valor_investimento} 
            ordem = await exchange.create_order(symbol, 'market', 'buy', params=params)
            
            # Dados reais da execução
            qtd_compra = float(ordem['amount']) # Qtd de moedas compradas (ex: 0.001 BTC)
            preco_real = float(ordem['average']) if ordem.get('average') else preco_atual
            
            dados["preco_compra"] = preco_real
            notifier.enviar_discord(f"🛍️ COMPRA REAL: {symbol}", f"Qtd: {qtd_compra}\nPreço: {preco_real}\nScore IA: {analise['score']}", 0x00ff00)
            sucesso = True
            
        except Exception as e:
            notifier.enviar_discord(f"❌ ERRO COMPRA REAL: {symbol}", str(e), 0xff0000)
            print(f"Erro Binance Compra: {e}")
            return
    else:
        # SIMULAÇÃO
        dados["preco_compra"] = preco_atual
        qtd_compra = dados["saldo"] / preco_atual
        notifier.enviar_discord(f"🚀 COMPRA SIMULADA: {symbol}", f"Score IA: {analise['score']}/10", 0x00ff00)
        sucesso = True

    # 2. ATUALIZAÇÃO LOCAL
    if sucesso:
        dados["qtd"] = qtd_compra
        dados["posicao"] = True
        dados["preco_maximo"] = dados["preco_compra"]
        
        salvar_estado(symbol, dados["saldo"], True, dados["preco_compra"], dados["qtd"], dados["preco_maximo"])
        salvar_trade(symbol, "COMPRA", dados["preco_compra"], dados["qtd"], 0)
        atualizar_status_ia(symbol, analise['rsi'], analise['score'], "COMPRA")

# --- CORE ---

async def vigilante_multi_preco(exchange):
    if not ESTADO["ativos_ativos"]: return
    streams = "/".join([f"{s.replace('/', '').lower()}@miniTicker" for s in ESTADO["ativos_ativos"]])
    url = f"wss://stream.binance.com:9443/ws/{streams}"
    
    async with websockets.connect(url) as ws:
        while True:
            try:
                if not ESTADO["bot_rodando"]:
                    await asyncio.sleep(1)
                    continue

                data = await ws.recv()
                msg = json.loads(data)
                symbol_raw = msg['s'] 
                price = float(msg['c'])

                # Mapeia símbolo raw (BTCBRL) para formatado (BTC/BRL)
                sym = next((s for s in ESTADO["ativos_ativos"] if s.replace('/','') == symbol_raw), None)
                if not sym: continue

                ESTADO["precos_live"][sym] = price
                dados = ESTADO["ativos_data"][sym]

                if dados["posicao"]:
                    # Lógica de Trailing Stop
                    if price > dados["preco_maximo"]: 
                        dados["preco_maximo"] = price
                        # Salva o novo topo no banco para não perder se reiniciar
                        salvar_estado(sym, dados["saldo"], True, dados["preco_compra"], dados["qtd"], price)

                    regra = PERFIS[ESTADO["perfil_ativo"]]
                    recuo = ((price - dados["preco_maximo"]) / dados["preco_maximo"]) * 100
                    lucro = ((price - dados["preco_compra"]) / dados["preco_compra"]) * 100
                    
                    if (lucro - TAXA_TOTAL) > regra["LUCRO_MINIMO"] and recuo <= -regra["TRAILING_DROP"]:
                        await executar_venda(sym, "Trailing Stop", exchange)
                    elif lucro <= -regra["STOP_LOSS"]:
                        await executar_venda(sym, "Stop Loss", exchange)
                
                # Log de Status
                modo_txt = "REAL 💸" if ESTADO["modo_producao"] else "SIM 🎮"
                print(f"[{modo_txt}] {ESTADO['perfil_ativo'].upper()} | {sym}: {price:.2f}", end='\r')

            except Exception as e:
                # print(f"Erro Vigilante: {e}") 
                await asyncio.sleep(1)

async def estrategista_cerebro(exchange):
    while True:
        try:
            if not ESTADO["bot_rodando"]:
                await asyncio.sleep(5)
                continue

            for sym in ESTADO["ativos_ativos"]:
                dados = ESTADO["ativos_data"][sym]
                
                # Só analisa compra se NÃO estiver posicionado
                if not dados["posicao"]:
                    # Se for modo REAL, usa a API privada para ter rate limit maior, senão publica
                    c1m = await exchange.fetch_ohlcv(sym, timeframe='1m', limit=100)
                    c15m = await exchange.fetch_ohlcv(sym, timeframe='15m', limit=100)
                    
                    config = ESTADO["configs_ia"].get(sym)
                    analise = brain.analisar_multitimeframe(c1m, c15m, config=config)
                    atualizar_status_ia(sym, analise['rsi'], analise['score'], analise['decisao'])
                    
                    regra = PERFIS[ESTADO["perfil_ativo"]]
                    if analise['decisao'] == "COMPRA" and analise['score'] >= regra["SCORE_MINIMO"]:
                        await executar_compra(sym, analise, exchange)
            
            await asyncio.sleep(10)
        except Exception as e:
            logging.error(f"Erro Estrategista: {e}")
            await asyncio.sleep(5)

# --- LOOP PRINCIPAL ---
async def main():
    criar_tabelas()
    criar_tabela_configs()
    
    # 1. CARREGA CONFIGURAÇÕES E CHAVES
    db_configs = carregar_configs_globais()
    api_key = db_configs.get('binance_key')
    secret_key = db_configs.get('binance_secret')
    ESTADO["modo_producao"] = db_configs.get('modo_producao') == 'true'

    # 2. INICIALIZA EXCHANGE (COM CHAVES SE EXISTIREM)
    if api_key and secret_key:
        print("🔑 Chaves de API detectadas. Configurando acesso Binance...")
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
    else:
        print("⚠️ Sem chaves de API. O bot rodará apenas em SIMULAÇÃO.")
        exchange = ccxt.binance({'enableRateLimit': True})

    # 3. CALIBRAÇÃO (Igual ao anterior)
    while True:
        ranking = []
        print(f"\n🔍 [CALIBRAÇÃO] Analisando {len(CANDIDATOS)} candidatos...")
        for sym in CANDIDATOS:
            config, lucro = await otimizar_estrategia(exchange, sym)
            atualizar_status_ia(sym, 0, lucro, "OBSERVAÇÃO" if lucro <= 0 else "ELITE")
            if lucro > 0: ranking.append({'symbol': sym, 'config': config, 'lucro': lucro})
        
        elite_data = sorted(ranking, key=lambda x: x['lucro'], reverse=True)[:LIMITE_ELITE]
        ESTADO["ativos_ativos"] = [item['symbol'] for item in elite_data]

        if not ESTADO["ativos_ativos"]:
            print("⚠️ Nenhuma moeda lucrativa. Aguardando 15 min...")
            await asyncio.sleep(900)
            continue
        break

    # 4. CARREGA MEMÓRIA
    for sym in ESTADO["ativos_ativos"]:
        memoria = carregar_estado(sym)
        ESTADO["configs_ia"][sym] = next(item['config'] for item in elite_data if item['symbol'] == sym)
        ESTADO["precos_live"][sym] = 0.0
        
        if memoria:
            ESTADO["ativos_data"][sym] = {
                "saldo": memoria['saldo'], "posicao": memoria['posicao'],
                "preco_compra": memoria['preco_compra'], "qtd": memoria['qtd_btc'], "preco_maximo": memoria['preco_maximo']
            }
        else:
            saldo_inicial = obter_ultimo_saldo(sym)
            ESTADO["ativos_data"][sym] = {
                "saldo": saldo_inicial, "posicao": False, "preco_compra": 0, "qtd": 0, "preco_maximo": 0
            }

    notifier.enviar_discord("✅ SISTEMA V1.0 (PROD)", f"Modo: {'REAL' if ESTADO['modo_producao'] else 'SIMULADO'}\nAtivos: {ESTADO['ativos_ativos']}", 0x00ff00)
    
    # 5. INICIA MOTORES
    from modules.notifier import agendador_relatorio
    await asyncio.gather(
        vigilante_multi_preco(exchange), 
        estrategista_cerebro(exchange),
        sincronizar_configs(exchange),
        agendador_relatorio()
    )
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())