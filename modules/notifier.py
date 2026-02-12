import requests
import os
import json
from datetime import datetime

def enviar_discord(titulo, mensagem, cor=0x00ff00, marcar_usuario=True):
    """
    Envia notificação rica (Embed) para o Discord via Webhook.
    Se marcar_usuario=True, adiciona o ID do usuário para gerar notificação push.
    """
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    user_id = os.getenv('DISCORD_USER_ID') # Opcional: ID específico do usuário
    
    if not webhook_url:
        return

    # Define quem será marcado (Seu ID específico ou @everyone se não tiver ID)
    mencao = ""
    if marcar_usuario:
        if user_id:
            mencao = f"<@{user_id}>" 
        else:
            mencao = "@everyone"

    try:
        payload = {
            "content": mencao, # A marcação vai aqui fora do embed
            "embeds": [{
                "title": titulo,
                "description": mensagem,
                "color": cor,
                "footer": {"text": f"TraderBot Pro V5.3 • Elite Ranking Ativo • {datetime.now().strftime('%H:%M:%S')}"}
            }]
        }
        
        headers = {'Content-Type': 'application/json'}
        requests.post(webhook_url, data=json.dumps(payload), headers=headers, timeout=5)
    except Exception as e:
        print(f"Erro Discord: {e}")