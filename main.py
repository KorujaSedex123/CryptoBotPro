import time
import schedule
import ccxt
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Módulos Locais
from modules.database import criar_tabelas, salvar_trade, atualizar_status_ia, salvar_estado, carregar_estado
import modules.brain as brain
import modules.notifier as notifier

# --- CONFIGURAÇÃO DE LOG E ENV ---
logging.basicConfig(
    filename='bot.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
load_dotenv()

# --- PARÂMETROS ---
SYMBOL = os.getenv('TRADING_PAIR', 'BTC/BRL') 
STOP_LOSS = 1.5      
TRAILING_DROP = 0.5  
LUCRO_MINIMO = 0.2   
TEMPO_PAUSA = 30 # Minutos de Cooldown

# Variáveis de Estado
SALDO = 100.00       
POSICAO = False
PRECO_COMPRA = 0.0
QTD_BTC = 0.0
PRECO_MAXIMO = 0.0   
EM_COOLDOWN = False
HORA_STOP = None

print("🤖 TRADERBOT V3 ROBUST - DISCORD EDITION")
logging.info("Sistema Iniciado")
criar_tabelas() 

# --- CARREGAR MEMÓRIA ---
memoria = carregar_estado()
if memoria:
    SALDO = memoria['saldo']
    POSICAO = bool(memoria['posicao'])
    PRECO_COMPRA = memoria['preco_compra']
    QTD_BTC = memoria['qtd_btc']
    PRECO_MAXIMO = memoria['preco_maximo']
    print(f"💾 Memória Restaurada | Saldo: R$ {SALDO:.2f}")

def get_dados_robustos():
    """Busca dados de 1m E 15m para análise completa"""
    try:
        exchange = ccxt.binance({'enableRateLimit': True}) 
        # Pega 100 velas para a TA-Lib calcular com precisão
        candles_1m = exchange.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
        candles_15m = exchange.fetch_ohlcv(SYMBOL, timeframe='15m', limit=100)
        
        if not candles_1m or not candles_15m: return None, None, None
        
        preco_atual = candles_1m[-1][4]
        return candles_1m, candles_15m, preco_atual
    except Exception as e:
        logging.error(f"Erro API Binance: {e}")
        return None, None, None

def vender(preco, motivo):
    global SALDO, POSICAO, QTD_BTC, PRECO_COMPRA, PRECO_MAXIMO, EM_COOLDOWN, HORA_STOP
    
    valor_venda = QTD_BTC * preco
    lucro_reais = valor_venda - (QTD_BTC * PRECO_COMPRA)
    lucro_pct = (lucro_reais / (QTD_BTC * PRECO_COMPRA)) * 100
    
    SALDO = valor_venda
    POSICAO = False
    
    salvar_estado(SALDO, POSICAO, 0, 0, 0)
    salvar_trade(SYMBOL, "VENDA", preco, 0, lucro_reais)
    
    # Notificação Discord
    cor = 0x00ff00 if lucro_pct > 0 else 0xff0000
    msg = f"**Motivo:** {motivo}\n**Lucro:** {lucro_pct:.2f}%\n**Novo Saldo:** R$ {SALDO:.2f}"
    notifier.enviar_discord("🚨 VENDA EXECUTADA", msg, cor)
    
    print(f"\n🚨 VENDA: {lucro_pct:.2f}% ({motivo})")
    logging.info(f"Venda: {lucro_pct:.2f}% | {motivo}")

    # Cooldown se houver prejuízo
    if lucro_pct < 0:
        print(f"❄️ Entrando em Cooldown por {TEMPO_PAUSA}min")
        notifier.enviar_discord("❄️ COOLDOWN ATIVADO", f"Pausando operações por {TEMPO_PAUSA} minutos devido a prejuízo.", 0x0000ff)
        EM_COOLDOWN = True
        HORA_STOP = datetime.now()

def job():
    global SALDO, POSICAO, PRECO_COMPRA, QTD_BTC, PRECO_MAXIMO, EM_COOLDOWN, HORA_STOP
    
    c_1m, c_15m, preco = get_dados_robustos()
    if not preco: return
    
    # Analisa com Brain V3
    analise = brain.analisar_multitimeframe(c_1m, c_15m)
    
    status = "POSICIONADO" if POSICAO else f"SCORE: {analise['score']}/10"
    if EM_COOLDOWN: status = "❄️ COOLDOWN"
    
    print(f"⏱️ {datetime.now().strftime('%H:%M:%S')} | {status} | Tendência 15m: {analise['tendencia_macro']} | Decisão: {analise['decisao']}", end='\r')
    
    # --- GESTÃO DE POSIÇÃO ---
    if POSICAO:
        if preco > PRECO_MAXIMO:
            PRECO_MAXIMO = preco
            salvar_estado(SALDO, POSICAO, PRECO_COMPRA, QTD_BTC, PRECO_MAXIMO)

        recuo_pct = ((preco - PRECO_MAXIMO) / PRECO_MAXIMO) * 100
        lucro_pct = ((preco - PRECO_COMPRA) / PRECO_COMPRA) * 100

        if lucro_pct > LUCRO_MINIMO and recuo_pct <= -TRAILING_DROP:
            vender(preco, "Trailing Stop")
        elif lucro_pct <= -STOP_LOSS:
            vender(preco, "Stop Loss")
            
    else:
        # Verifica Cooldown
        if EM_COOLDOWN:
            if (datetime.now() - HORA_STOP).total_seconds() / 60 >= TEMPO_PAUSA:
                EM_COOLDOWN = False
                notifier.enviar_discord("🔥 VOLTANDO AO JOGO", "Cooldown finalizado. Retomando análises.", 0xffff00)
            return

        # SINAL DE COMPRA
        if analise['decisao'] == "COMPRA":
            msg = f"**Preço:** R$ {preco:.2f}\n**Score:** {analise['score']}\n**Motivos:** {', '.join(analise['motivos'])}"
            notifier.enviar_discord("🚀 COMPRA DETECTADA", msg, 0x00ff00)
            
            print(f"\n🚀 COMPRA: {msg}")
            logging.info(f"Compra: {preco}")
            
            PRECO_COMPRA = preco
            QTD_BTC = SALDO / preco
            POSICAO = True
            PRECO_MAXIMO = preco
            
            salvar_estado(SALDO, POSICAO, PRECO_COMPRA, QTD_BTC, PRECO_MAXIMO)
            salvar_trade(SYMBOL, "COMPRA", preco, QTD_BTC, 0)
            
        # Atualiza Dashboard
        atualizar_status_ia(analise['rsi'], analise['score'], analise['decisao'])

# Roda a cada 10s
schedule.every(10).seconds.do(job)

print("🚀 Executando primeira análise agora...")
job()

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        logging.error(f"Erro Fatal: {e}")
        time.sleep(5)