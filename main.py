import asyncio
import json
import os
import logging
from datetime import datetime
import ccxt.async_support as ccxt 
import websockets
from dotenv import load_dotenv

# Módulos Locais
from modules.database import criar_tabelas, salvar_trade, atualizar_status_ia, salvar_estado, carregar_estado
from modules.backtest import otimizar_estrategia 
import modules.brain as brain
import modules.notifier as notifier

# --- CONFIGURAÇÃO ---
logging.basicConfig(
    filename='bot.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
load_dotenv()

# Parâmetros de Seleção de Elite
CANDIDATOS = os.getenv('TRADING_PAIRS', 'BTC/BRL,ETH/BRL,SOL/BRL,BNB/BRL,ADA/BRL').split(',')
LIMITE_ELITE = 3  
STOP_LOSS = 1.5      
TRAILING_DROP = 0.5  
TAXA_TOTAL = 0.2
TEMPO_PAUSA = 30 

# Estado Global V5.2
ESTADO = {
    "ativos_ativos": [], # Símbolos selecionados para o dia
    "ativos_data": {},
    "precos_live": {},
    "configs": {} 
}

print(f"🔍 SISTEMA DE RANKING: Analisando {len(CANDIDATOS)} ativos candidatos...")
criar_tabelas() 

# --- FUNÇÕES DE OPERAÇÃO ---

async def executar_venda(symbol, motivo):
    global ESTADO
    dados = ESTADO["ativos_data"][symbol]
    preco = ESTADO["precos_live"][symbol]
    
    valor_bruto = dados["qtd"] * preco
    lucro_reais = (valor_bruto - (dados["qtd"] * dados["preco_compra"])) * (1 - (TAXA_TOTAL/100))
    
    dados["saldo"] = valor_bruto * (1 - (TAXA_TOTAL/100))
    dados["posicao"] = False
    
    salvar_estado(symbol, dados["saldo"], False, 0, 0, 0)
    salvar_trade(symbol, "VENDA", preco, 0, lucro_reais)
    notifier.enviar_discord(f"🚨 VENDA: {symbol}", f"Motivo: {motivo}\nLucro: R$ {lucro_reais:.2f}", 0xff0000)

async def executar_compra(symbol, analise):
    global ESTADO
    dados = ESTADO["ativos_data"][symbol]
    preco = ESTADO["precos_live"][symbol]
    
    dados["preco_compra"] = preco
    dados["qtd"] = dados["saldo"] / preco
    dados["posicao"] = True
    dados["preco_maximo"] = preco
    
    salvar_estado(symbol, dados["saldo"], True, preco, dados["qtd"], preco)
    salvar_trade(symbol, "COMPRA", preco, dados["qtd"], 0)
    notifier.enviar_discord(f"🚀 COMPRA: {symbol}", f"Score IA: {analise['score']}/10", 0x00ff00)
    atualizar_status_ia(symbol, analise['rsi'], analise['score'], "COMPRA")

# --- CORE: VIGILANTE E ESTRATEGISTA ---

async def vigilante_multi_preco():
    if not ESTADO["ativos_ativos"]: return
    
    streams = "/".join([f"{s.replace('/', '').lower()}@miniTicker" for s in ESTADO["ativos_ativos"]])
    url = f"wss://stream.binance.com:9443/ws/{streams}"
    
    async with websockets.connect(url) as ws:
        while True:
            try:
                data = await ws.recv()
                msg = json.loads(data)
                symbol_raw = msg['s'] 
                
                for sym in ESTADO["ativos_ativos"]:
                    if sym.replace('/', '') == symbol_raw:
                        price = float(msg['c'])
                        ESTADO["precos_live"][sym] = price
                        
                        dados = ESTADO["ativos_data"][sym]
                        if dados["posicao"]:
                            if price > dados["preco_maximo"]: dados["preco_maximo"] = price
                            recuo = ((price - dados["preco_maximo"]) / dados["preco_maximo"]) * 100
                            lucro = ((price - dados["preco_compra"]) / dados["preco_compra"]) * 100
                            
                            if (lucro - TAXA_TOTAL) > 0.2 and recuo <= -TRAILING_DROP:
                                await executar_venda(sym, "Trailing Stop")
                            elif lucro <= -STOP_LOSS:
                                await executar_venda(sym, "Stop Loss")
                
                print(f"⚡ Live: " + " | ".join([f"{k}:{v:.0f}" for k,v in ESTADO["precos_live"].items()]), end='\r')
            except:
                await asyncio.sleep(5)

async def estrategista_cerebro(exchange):
    while True:
        try:
            for sym in ESTADO["ativos_ativos"]:
                dados = ESTADO["ativos_data"][sym]
                if not dados["posicao"]:
                    c1m = await exchange.fetch_ohlcv(sym, timeframe='1m', limit=100)
                    c15m = await exchange.fetch_ohlcv(sym, timeframe='15m', limit=100)
                    
                    config = ESTADO["configs"].get(sym)
                    analise = brain.analisar_multitimeframe(c1m, c15m, config=config)
                    atualizar_status_ia(sym, analise['rsi'], analise['score'], analise['decisao'])
                    
                    if analise['decisao'] == "COMPRA":
                        await executar_compra(sym, analise)
            await asyncio.sleep(10)
        except Exception as e:
            logging.error(f"Erro Estrategista: {e}")
            await asyncio.sleep(5)

ESTADO_RELATORIO = {"ultimo_envio": None}
async def agendador_relatorio():
    """Verifica a cada minuto se é hora de enviar o resumo diário"""
    while True:
        agora = datetime.now()
        
        # Define o envio para as 23:59
        if agora.hour == 23 and agora.minute == 59:
            hoje = agora.strftime('%Y-%m-%d')
            
            if ESTADO_RELATORIO["ultimo_envio"] != hoje:
                print("\n📊 Gerando relatório de fecho de dia...")
                from modules.database import obter_resumo_diario
                resumo = obter_resumo_diario()
                notifier.enviar_relatorio_diario(resumo)
                
                ESTADO_RELATORIO["ultimo_envio"] = hoje
        
        await asyncio.sleep(60) # Verifica a cada minuto
# --- FASE DE SELEÇÃO DE ELITE ---

async def main():
    # Instancia a exchange apenas uma vez
    exchange = ccxt.binance({'enableRateLimit': True})
    
    # LOOP DE CALIBRAÇÃO INFINITO
    while True:
        ranking = []
        print(f"\n🔍 [CALIBRAÇÃO] Analisando {len(CANDIDATOS)} candidatos...")
        
        # Faz o backtest de todos
        for sym in CANDIDATOS:
            config, lucro = await otimizar_estrategia(exchange, sym)
            # Salva o resultado para o Dashboard mostrar o relatório
            atualizar_status_ia(sym, 0, lucro, "OBSERVAÇÃO" if lucro <= 0 else "ELITE")
            
            if lucro > 0:
                ranking.append({'symbol': sym, 'config': config, 'lucro': lucro})
        
        # Tenta selecionar a Elite
        elite_data = sorted(ranking, key=lambda x: x['lucro'], reverse=True)[:LIMITE_ELITE]
        ESTADO["ativos_ativos"] = [item['symbol'] for item in elite_data]

        # SE NÃO ACHOU NADA LUCRATIVO:
        if not ESTADO["ativos_ativos"]:
            print("⚠️ Nenhuma moeda lucrativa no momento. Aguardando 15 minutos para re-calibrar...")
            # Avisa no Discord uma vez a cada ciclo de espera
            notifier.enviar_discord("😴 MODO ESPERA", "Nenhuma oportunidade real detectada. Vou tentar novamente em 15 min.", 0x71717a)
            
            # Dorme por 15 minutos antes de tentar o Ranking de novo
            await asyncio.sleep(900) 
            continue # Volta para o topo do 'while True' para tentar de novo
        
        # SE ACHOU ELITE: Sai do loop de calibração inicial para começar o trade
        break

    # --- INICIALIZAÇÃO DA ELITE (IGUAL AO ANTERIOR) ---
    print(f"🏆 ELITE DO DIA SELECIONADA: {ESTADO['ativos_ativos']}")
    
    for sym in ESTADO["ativos_ativos"]:
        memoria = carregar_estado(sym)
        ESTADO["configs"][sym] = next(item['config'] for item in elite_data if item['symbol'] == sym)
        ESTADO["precos_live"][sym] = 0.0
        
        if memoria:
            ESTADO["ativos_data"][sym] = {
                "saldo": memoria['saldo'], "posicao": memoria['posicao'],
                "preco_compra": memoria['preco_compra'], "qtd": memoria['qtd_btc'],
                "preco_maximo": memoria['preco_maximo']
            }
        else:
            ESTADO["ativos_data"][sym] = {
                "saldo": 100.0, "posicao": False, "preco_compra": 0.0, "qtd": 0.0, "preco_maximo": 0.0
            }

    notifier.enviar_discord("✅ ELITE ATIVADA", f"Bot operando: {', '.join(ESTADO['ativos_ativos'])}", 0x00ff00)
    
    # Inicia os motores
    await asyncio.gather(vigilante_multi_preco(), estrategista_cerebro(exchange),agendador_relatorio())
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())