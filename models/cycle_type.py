# -*- coding: utf-8 -*-
"""Extensão do tipo de ciclo: texto padrão de informações complementares para relatório ETO."""
from odoo import models, fields

# Texto sugerido para novos tipos de ciclo ETO (liberação paramétrica / indicadores biológicos).
_DEFAULT_INFORMACOES_COMPLEMENTARES = (
    "Valores limites para liberação paramétrica: 1) Massa ETO (kg) = 5,2 a 14,7; "
    "2) Concentração ETO (mg/L) = 450 a 1200; 3) Temperatura fase esterilização (°C) = 41 a 61; "
    "4) Umidade Relativa fase esterilização (%) = 30 a 80.\n"
    "São colocados 15 indicadores biológicos espalhados em diversos pontos do esterilizador e o "
    "resultado de todos eles após período de incubação de 48 horas deve ser negativo."
)


class CycleTypeEto(models.Model):
    _inherit = 'afr.cycle.type'

    informacoes_complementares = fields.Text(
        default=_DEFAULT_INFORMACOES_COMPLEMENTARES,
    )
