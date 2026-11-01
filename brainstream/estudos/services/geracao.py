"""Geração de conteúdo estruturado (Quiz e Speedrun): Gemini em JSON validado, com fallback simulado."""
import json
import logging

from . import tutor

logger = logging.getLogger(__name__)

IA = 'ia'
SIMULADA = 'simulada'


def gerar_estruturado(sistema, pedido, esquema, validar, simuladas, rotulo):
    """
    Pede ao Gemini um JSON no ``esquema`` e o confere com ``validar``. Sem IA configurada, com outro
    provedor, em falha da API ou com JSON inválido, devolve ``simuladas()``. Retorna ``(itens, origem)``.
    """
    if not tutor.simulacao_ativa():
        try:
            if tutor.provedor() == tutor.GEMINI:
                texto, _ = tutor.gerar_com_gemini(
                    sistema, [{'role': 'user', 'content': pedido}], tutor.modelo(tutor.GEMINI),
                    response_mime_type='application/json', response_json_schema=esquema,
                )
                return validar(json.loads(texto)), IA
        except tutor.TutorIndisponivel:
            pass  # o motivo já foi registrado no log
        except ValueError as erro:  # inclui JSON malformado
            logger.warning('%s gerado pela IA veio inválido (%s); usando conteúdo simulado.', rotulo, erro)
    return simuladas(), SIMULADA
