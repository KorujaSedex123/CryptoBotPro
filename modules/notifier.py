import requests
import os
import json
from datetime import datetime

def enviar_discord(titulo, mensagem, cor=0x00ff00):
    """
    Envia notificação rica (Embed) para o Discord via Webhook.
    Cores: 0x00ff00 (Verde/Compra), 0xff0000 (Vermelho/Venda), 0xffff00 (Amarelo/Info)
    """
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    
    if not webhook_url:
        return

    try:
        payload = {
            "embeds": [{
                "title": titulo,
                "description": mensagem,
                "color": cor,
                "footer": {"text": f"TraderBot V3 • {datetime.now().strftime('%H:%M:%S')}"}
            }]
        }
        
        headers = {'Content-Type': 'application/json'}
        requests.post(webhook_url, data=json.dumps(payload), headers=headers, timeout=5)
    except Exception as e:
        print(f"Erro Discord: {e}")