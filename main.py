import asyncio
import json
import os
import logging
from datetime import datetime
import ccxt.async_support as ccxt  # Versão Assíncrona (Turbo)
import websockets
from dotenv import load_dotenv

# Módulos Locais
from modules.database import criar_tabelas, salvar_trade, atualizar_status_ia, salvar_estado, carregar_estado
import modules.brain as brain
import modules.notifier as notifier

# --- CONFIGURAÇÃO ---
logging.basicConfig(
    filename='bot.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
load_dotenv()

# Parâmetros
SYMBOL = os.getenv('TRADING_PAIR', 'BTC/BRL') 
STOP_LOSS = 1.5      
TRAILING_DROP = 0.5  
LUCRO_MINIMO = 0.2   
TAXA_TOTAL = 0.2
TEMPO_PAUSA = 30 # Minutos

# Variáveis de Estado (Globais)
ESTADO = {
    "saldo": 100.00,
    "posicao": False,
    "preco_compra": 0.0,
    "qtd": 0.0,
    "preco_maximo": 0.0,
    "cooldown": False,
    "hora_stop": None,
    "preco_atual": 0.0  # Atualizado via WebSocket
}

print("⚡ TRADERBOT V4 - REAL-TIME WEBSOCKETS INICIADO")
logging.info("Sistema Async Iniciado")
criar_tabelas() 

# --- NOTIFICAÇÃO DE INÍCIO ---
notifier.enviar_discord(
    "🟢 SISTEMA ONLINE", 
    f"O TraderBot V4 iniciou com sucesso!\n**Par:** {SYMBOL}\n**Modo:** WebSockets Real-Time", 
    0x00ff00
)

# Carregar Memória
memoria = carregar_estado()
if memoria:
    ESTADO["saldo"] = memoria['saldo']
    ESTADO["posicao"] = bool(memoria['posicao'])
    ESTADO["preco_compra"] = memoria['preco_compra']
    ESTADO["qtd"] = memoria['qtd_btc']
    ESTADO["preco_maximo"] = memoria['preco_maximo']
    print(f"💾 Memória Restaurada | Saldo: R$ {ESTADO['saldo']:.2f}")

# --- FUNÇÕES DE OPERAÇÃO (ASSÍNCRONAS) ---

async def executar_venda(exchange, motivo):
    """Executa venda imediatamente e notifica"""
    global ESTADO
    preco = ESTADO["preco_atual"]
    
    # Cálculos
    valor_bruto = ESTADO["qtd"] * preco
    lucro_bruto_reais = valor_bruto - (ESTADO["qtd"] * ESTADO["preco_compra"])
    lucro_bruto_pct = (lucro_bruto_reais / (ESTADO["qtd"] * ESTADO["preco_compra"])) * 100
    lucro_liquido_pct = lucro_bruto_pct - TAXA_TOTAL
    
    # Atualiza Estado
    ESTADO["saldo"] = valor_bruto * (1 - (TAXA_TOTAL/100))
    ESTADO["posicao"] = False
    ESTADO["qtd"] = 0.0
    ESTADO["preco_compra"] = 0.0
    ESTADO["preco_maximo"] = 0.0
    
    # Salva
    salvar_estado(ESTADO["saldo"], False, 0, 0, 0)
    salvar_trade(SYMBOL, "VENDA", preco, 0, lucro_bruto_reais * (1 - (TAXA_TOTAL/100)))

    # Log e Notificação
    msg = f"**Motivo:** {motivo}\n**Lucro Líquido:** {lucro_liquido_pct:.2f}%\n**Saldo:** R$ {ESTADO['saldo']:.2f}"
    print(f"\n🚨 VENDA FLASH: {lucro_liquido_pct:.2f}% ({motivo})")
    notifier.enviar_discord("🚨 VENDA REAL-TIME", msg, 0x00ff00 if lucro_liquido_pct > 0 else 0xff0000)

    # Cooldown
    if lucro_liquido_pct < 0:
        print(f"❄️ Entrando em Cooldown de {TEMPO_PAUSA}min")
        ESTADO["cooldown"] = True
        ESTADO["hora_stop"] = datetime.now()
        notifier.enviar_discord("❄️ COOLDOWN ATIVADO", f"Pausando por {TEMPO_PAUSA} min.", 0x0000ff)

async def executar_compra(exchange, analise):
    """Executa compra"""
    global ESTADO
    preco = ESTADO["preco_atual"]
    
    ESTADO["preco_compra"] = preco
    ESTADO["qtd"] = ESTADO["saldo"] / preco
    ESTADO["posicao"] = True
    ESTADO["preco_maximo"] = preco
    
    salvar_estado(ESTADO["saldo"], True, preco, ESTADO["qtd"], preco)
    salvar_trade(SYMBOL, "COMPRA", preco, ESTADO["qtd"], 0)
    
    msg = f"**Preço:** R$ {preco:.2f}\n**Score:** {analise['score']}\n**Motivos:** {', '.join(analise['motivos'])}"
    print(f"\n🚀 COMPRA: {msg}")
    notifier.enviar_discord("🚀 COMPRA DETECTADA", msg, 0x00ff00)
    
    atualizar_status_ia(analise['rsi'], analise['score'], "COMPRA")

# --- CORE 1: O VIGILANTE (WEBSOCKET) ---
async def vigilante_preco(exchange):
    """Ouve o preço em tempo real e aciona Stops instantaneamente"""
    symbol_lower = SYMBOL.replace('/', '').lower()
    stream_url = f"wss://stream.binance.com:9443/ws/{symbol_lower}@miniTicker"
    
    print(f"👂 Conectando ao fluxo real-time: {stream_url}")
    
    async with websockets.connect(stream_url) as ws:
        while True:
            try:
                data = await ws.recv()
                json_data = json.loads(data)
                
                # Atualiza Preço Global (C = Close Price do miniTicker)
                price = float(json_data['c'])
                ESTADO["preco_atual"] = price
                
                # --- VERIFICAÇÃO DE SEGURANÇA (A CADA TICK) ---
                if ESTADO["posicao"]:
                    # Atualiza Topo (Trailing)
                    if price > ESTADO["preco_maximo"]:
                        ESTADO["preco_maximo"] = price
                    
                    # Cálculos
                    recuo = ((price - ESTADO["preco_maximo"]) / ESTADO["preco_maximo"]) * 100
                    lucro_bruto = ((price - ESTADO["preco_compra"]) / ESTADO["preco_compra"]) * 100
                    lucro_liq = lucro_bruto - TAXA_TOTAL

                    # CHECAGEM DE SAÍDA IMEDIATA
                    if lucro_liq > LUCRO_MINIMO and recuo <= -TRAILING_DROP:
                        await executar_venda(exchange, f"Trailing Stop (Tick)")
                    elif lucro_bruto <= -STOP_LOSS:
                        await executar_venda(exchange, f"Stop Loss (Tick)")
                
                # Log visual minimalista na mesma linha
                print(f"⚡ {price:.2f} | P: {ESTADO['posicao']} | Saldo: {ESTADO['saldo']:.2f}", end='\r')

            except Exception as e:
                print(f"Erro no WebSocket: {e}")
                await asyncio.sleep(5) # Tenta reconectar

# --- CORE 2: O ESTRATEGISTA (LOOP PERIÓDICO) ---
async def estrategista_cerebro(exchange):
    """A cada 10s, baixa velas históricas e roda o Brain V3"""
    while True:
        try:
            # Se já está posicionado, o Vigilante cuida da venda.
            if not ESTADO["posicao"]:
                
                # 1. Verifica Cooldown
                if ESTADO["cooldown"]:
                    tempo = (datetime.now() - ESTADO["hora_stop"]).total_seconds() / 60
                    if tempo >= TEMPO_PAUSA:
                        ESTADO["cooldown"] = False
                        notifier.enviar_discord("🔥 RETORNO", "Cooldown finalizado.", 0xffff00)
                    else:
                        atualizar_status_ia(0, 0, "GELADEIRA")
                        await asyncio.sleep(10)
                        continue

                # 2. Busca Dados (IO Assíncrono)
                candles_1m = await exchange.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
                candles_15m = await exchange.fetch_ohlcv(SYMBOL, timeframe='15m', limit=100)
                
                if candles_1m and candles_15m:
                    # 3. Analisa (Brain é síncrono/CPU, mas é rápido)
                    analise = brain.analisar_multitimeframe(candles_1m, candles_15m)
                    
                    # Atualiza Dashboard
                    atualizar_status_ia(analise['rsi'], analise['score'], analise['decisao'])
                    
                    # 4. Decide
                    if analise['decisao'] == "COMPRA":
                        await executar_compra(exchange, analise)

            await asyncio.sleep(10) 

        except Exception as e:
            logging.error(f"Erro Estrategista: {e}")
            print(f"\n❌ Erro Strategy: {e}")
            await asyncio.sleep(5)

# --- ORQUESTRAÇÃO ---
async def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    
    tarefa_vigilante = asyncio.create_task(vigilante_preco(exchange))
    tarefa_estrategista = asyncio.create_task(estrategista_cerebro(exchange))
    
    await asyncio.gather(tarefa_vigilante, tarefa_estrategista)
    
    await exchange.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot encerrado.")