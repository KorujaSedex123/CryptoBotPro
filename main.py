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

# --- CONFIGURAÇÃO ---
logging.basicConfig(
    filename='bot.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
load_dotenv()

# --- DEFINIÇÃO DE PERFIS DE RISCO ---
PERFIS = {
    "conservador": {
        "STOP_LOSS": 1.0,
        "TRAILING_DROP": 0.2,
        "LUCRO_MINIMO": 0.1,
        "SCORE_MINIMO": 8,
        "RSI_COMPRA": 30
    },
    "moderado": {
        "STOP_LOSS": 1.5,
        "TRAILING_DROP": 0.5,
        "LUCRO_MINIMO": 0.2,
        "SCORE_MINIMO": 6,
        "RSI_COMPRA": 35
    },
    "agressivo": {
        "STOP_LOSS": 3.0,
        "TRAILING_DROP": 1.0,
        "LUCRO_MINIMO": 0.4,
        "SCORE_MINIMO": 5,
        "RSI_COMPRA": 45
    }
}

# Parâmetros Iniciais
CANDIDATOS = os.getenv('TRADING_PAIRS', 'BTC/BRL,ETH/BRL,SOL/BRL,BNB/BRL,ADA/BRL').split(',')
LIMITE_ELITE = 3  
TAXA_TOTAL = 0.2

# Estado Global de Operação
ESTADO = {
    "ativos_ativos": [],
    "ativos_data": {},
    "precos_live": {},
    "configs_ia": {},
    "bot_rodando": True,
    "modo_producao": False,
    "perfil_ativo": "moderado"
}

# --- FUNÇÃO DE SINCRONIZAÇÃO DE CONFIGURAÇÕES ---

async def sincronizar_configs():
    """Lê o banco de dados a cada 10s para atualizar o comportamento do bot"""
    global ESTADO
    while True:
        try:
            db_configs = carregar_configs_globais()
            ESTADO["bot_rodando"] = db_configs.get('bot_rodando') == 'true'
            ESTADO["modo_producao"] = db_configs.get('modo_producao') == 'true'
            ESTADO["perfil_ativo"] = db_configs.get('perfil_risco', 'moderado')
            
            # Verificar Comando de Venda Total (Botão de Pânico)
            if db_configs.get('comando_venda_total') == 'true':
                print("\n🚨 COMANDO DE EMERGÊNCIA: Vendendo todos os ativos!")
                for sym in ESTADO["ativos_ativos"]:
                    if ESTADO["ativos_data"][sym]["posicao"]:
                        await executar_venda(sym, "Venda Manual (Dashboard)")
                resetar_comando_venda() # Volta o comando para 'false' no banco e evita loop
                
        except Exception as e:
            logging.error(f"Erro ao sincronizar configs: {e}")
        await asyncio.sleep(10)

# --- FUNÇÕES DE OPERAÇÃO ---

async def executar_venda(symbol, motivo):
    dados = ESTADO["ativos_data"][symbol]
    preco = ESTADO["precos_live"][symbol]
    
    valor_bruto = dados["qtd"] * preco
    lucro_reais = (valor_bruto - (dados["qtd"] * dados["preco_compra"])) * (1 - (TAXA_TOTAL/100))
    
    dados["saldo"] = valor_bruto * (1 - (TAXA_TOTAL/100))
    dados["posicao"] = False
    
    # Se estivesse em Produção Real, aqui iria a chamada exchange.create_order(...)
    
    salvar_estado(symbol, dados["saldo"], False, 0, 0, 0)
    salvar_trade(symbol, "VENDA", preco, 0, lucro_reais)
    
    cor = 0x00ff00 if lucro_reais > 0 else 0xff0000
    notifier.enviar_discord(f"🚨 VENDA: {symbol}", f"Motivo: {motivo}\nLucro: R$ {lucro_reais:.2f}", cor)

async def executar_compra(symbol, analise):
    dados = ESTADO["ativos_data"][symbol]
    preco = ESTADO["precos_live"][symbol]
    
    dados["preco_compra"] = preco
    dados["qtd"] = dados["saldo"] / preco
    dados["posicao"] = True
    dados["preco_maximo"] = preco
    
    # Se estivesse em Produção Real, aqui iria a chamada exchange.create_order(...)
    
    salvar_estado(symbol, dados["saldo"], True, preco, dados["qtd"], preco)
    salvar_trade(symbol, "COMPRA", preco, dados["qtd"], 0)
    
    notifier.enviar_discord(f"🚀 COMPRA: {symbol}", f"Score IA: {analise['score']}/10\nPerfil: {ESTADO['perfil_ativo'].upper()}", 0x00ff00)
    atualizar_status_ia(symbol, analise['rsi'], analise['score'], "COMPRA")

# --- CORE: VIGILANTE E ESTRATEGISTA ---

async def vigilante_multi_preco():
    if not ESTADO["ativos_ativos"]: return
    
    streams = "/".join([f"{s.replace('/', '').lower()}@miniTicker" for s in ESTADO["ativos_ativos"]])
    url = f"wss://stream.binance.com:9443/ws/{streams}"
    
    async with websockets.connect(url) as ws:
        while True:
            try:
                # Se o bot estiver pausado, ele ignora o processamento
                if not ESTADO["bot_rodando"]:
                    await asyncio.sleep(1)
                    continue

                data = await ws.recv()
                msg = json.loads(data)
                symbol_raw = msg['s'] 
                
                for sym in ESTADO["ativos_ativos"]:
                    if sym.replace('/', '') == symbol_raw:
                        price = float(msg['c'])
                        ESTADO["precos_live"][sym] = price
                        
                        dados = ESTADO["ativos_data"][sym]
                        if dados["posicao"]:
                            if price > dados["preco_maximo"]: 
                                dados["preco_maximo"] = price
                                salvar_estado(sym, dados["saldo"], True, dados["preco_compra"], dados["qtd"], price)

                            # Carrega as regras do Perfil Ativo Dinamicamente
                            regra = PERFIS[ESTADO["perfil_ativo"]]
                            
                            recuo = ((price - dados["preco_maximo"]) / dados["preco_maximo"]) * 100
                            lucro = ((price - dados["preco_compra"]) / dados["preco_compra"]) * 100
                            
                            if (lucro - TAXA_TOTAL) > regra["LUCRO_MINIMO"] and recuo <= -regra["TRAILING_DROP"]:
                                await executar_venda(sym, "Trailing Stop")
                            elif lucro <= -regra["STOP_LOSS"]:
                                await executar_venda(sym, "Stop Loss")
                
                status_bot = "🟢 RODANDO" if ESTADO["bot_rodando"] else "🔴 PAUSADO"
                print(f"[{status_bot}] Perfil: {ESTADO['perfil_ativo'].upper()} | " + " | ".join([f"{k}:{v:.0f}" for k,v in ESTADO["precos_live"].items()]), end='\r')
            except:
                await asyncio.sleep(5)

async def estrategista_cerebro(exchange):
    while True:
        try:
            if not ESTADO["bot_rodando"]:
                await asyncio.sleep(5)
                continue

            for sym in ESTADO["ativos_ativos"]:
                dados = ESTADO["ativos_data"][sym]
                if not dados["posicao"]:
                    c1m = await exchange.fetch_ohlcv(sym, timeframe='1m', limit=100)
                    c15m = await exchange.fetch_ohlcv(sym, timeframe='15m', limit=100)
                    
                    config = ESTADO["configs_ia"].get(sym)
                    analise = brain.analisar_multitimeframe(c1m, c15m, config=config)
                    atualizar_status_ia(sym, analise['rsi'], analise['score'], analise['decisao'])
                    
                    # Filtro de Perfil de Risco para Compra
                    regra = PERFIS[ESTADO["perfil_ativo"]]
                    
                    if analise['decisao'] == "COMPRA" and analise['score'] >= regra["SCORE_MINIMO"]:
                        await executar_compra(sym, analise)
            
            await asyncio.sleep(10)
        except Exception as e:
            logging.error(f"Erro Estrategista: {e}")
            await asyncio.sleep(5)

# --- AGENDADOR DE RELATÓRIO DIÁRIO ---
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
        
        await asyncio.sleep(60)

async def main():
    criar_tabelas()
    criar_tabela_configs()
    exchange = ccxt.binance({'enableRateLimit': True})
    
    # 1. LOOP DE CALIBRAÇÃO INICIAL
    while True:
        ranking = []
        print(f"\n🔍 [CALIBRAÇÃO] Analisando {len(CANDIDATOS)} candidatos...")
        for sym in CANDIDATOS:
            config, lucro = await otimizar_estrategia(exchange, sym)
            atualizar_status_ia(sym, 0, lucro, "OBSERVAÇÃO" if lucro <= 0 else "ELITE")
            if lucro > 0:
                ranking.append({'symbol': sym, 'config': config, 'lucro': lucro})
        
        elite_data = sorted(ranking, key=lambda x: x['lucro'], reverse=True)[:LIMITE_ELITE]
        ESTADO["ativos_ativos"] = [item['symbol'] for item in elite_data]

        if not ESTADO["ativos_ativos"]:
            print("⚠️ Nenhuma moeda lucrativa. Aguardando 15 min...")
            await asyncio.sleep(900)
            continue
        break

    # 2. INICIALIZAÇÃO DOS DADOS (CARTEIRA REAL)
    for sym in ESTADO["ativos_ativos"]:
        memoria = carregar_estado(sym)
        ESTADO["configs_ia"][sym] = next(item['config'] for item in elite_data if item['symbol'] == sym)
        ESTADO["precos_live"][sym] = 0.0
        
        if memoria:
            ESTADO["ativos_data"][sym] = {
                "saldo": memoria['saldo'], "posicao": memoria['posicao'],
                "preco_compra": memoria['preco_compra'], "qtd": memoria['qtd_btc'],
                "preco_maximo": memoria['preco_maximo']
            }
        else:
            # FIX: Carrega o último saldo acumulado do banco em vez de resetar para 100
            ultimo_saldo = obter_ultimo_saldo(sym)
            ESTADO["ativos_data"][sym] = {
                "saldo": ultimo_saldo, 
                "posicao": False, 
                "preco_compra": 0, 
                "qtd": 0, 
                "preco_maximo": 0
            }

    notifier.enviar_discord("✅ SISTEMA V6.0 ONLINE", f"Perfil: {ESTADO['perfil_ativo'].upper()}\nAtivos: {', '.join(ESTADO['ativos_ativos'])}", 0x00ff00)
    
    # 3. MOTORES
    await asyncio.gather(
        vigilante_multi_preco(), 
        estrategista_cerebro(exchange),
        sincronizar_configs(), # Monitoramento de Comandos (Pause/Panic)
        agendador_relatorio()  # Relatório Diário
    )
    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())