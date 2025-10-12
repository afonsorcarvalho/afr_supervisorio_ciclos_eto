from odoo import models, fields, api
import logging
from datetime import datetime, timedelta,time
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)   
import pytz
class SupervisorioCiclosEto(models.Model):
    _inherit = 'afr.supervisorio.ciclos'

    # Campo computado para verificar se é equipamento ETO
    is_eto_equipment = fields.Boolean(
        string='É Equipamento ETO',
        compute='_compute_is_eto_equipment',
        store=True,
        help='Indica se o equipamento é da categoria ETO'
    )
    
    @api.depends('equipment_category_id', 'equipment_category_id.name')
    def _compute_is_eto_equipment(self):
        """
        Verifica se o equipamento é da categoria ETO.
        """
        for record in self:
            if record.equipment_category_id and record.equipment_category_id.name:
                record.is_eto_equipment = 'ETO' in record.equipment_category_id.name.upper()
            else:
                record.is_eto_equipment = False

    # Campos específicos para ETO
    # Massa de gás ETO admitida (em Kg)
    massa_gas_eto = fields.Float(
        string='Massa de Gás ETO (Kg)',
        tracking=True,
        help='Quantidade de gás ETO admitida em Kg'
    )
    
    # Concentração de ETO em porcentagem (padrão 90%)
    concentracao_eto_porcentagem = fields.Float(
        string='Porcentagem ETO (%)',
        default=90.0,
        tracking=True,
        help='Porcentagem de ETO no gás (padrão 90%)'
    )
    
    # Massa de ETO calculada (massa_gas_eto * concentracao_eto_porcentagem / 100)
    massa_eto = fields.Float(
        string='Massa de ETO (Kg)',
        compute='_compute_massa_eto',
        store=True,
        
        tracking=True,
        help='Massa de ETO calculada automaticamente'
    )
    
    # Concentração de ETO na câmara (g/L)
    concentracao_eto_camara = fields.Float(
        string='Concentração na Câmara (mg/L)',
        compute='_compute_concentracao_eto_camara',
        store=True,
        tracking=True,
        help='Concentração de ETO na câmara, calculada automaticamente'
    )
    
    @api.depends('massa_gas_eto', 'concentracao_eto_porcentagem')
    def _compute_massa_eto(self):
        """
        Calcula a massa de ETO: massa_gas_eto * concentracao_eto_porcentagem / 100
        """
        for record in self:
            if record.massa_gas_eto and record.concentracao_eto_porcentagem:
                record.massa_eto = (record.massa_gas_eto * record.concentracao_eto_porcentagem) / 100
            else:
                record.massa_eto = 0.0
    
    @api.depends('massa_eto', 'equipment_id')
    def _compute_concentracao_eto_camara(self):
        """
        Calcula a concentração de ETO na câmara: massa_eto (Kg) / chamber_size (L) * 1000
        Converte Kg para gramas multiplicando por 1000
        """
        for record in self:
            if record.massa_eto and record.equipment_id and hasattr(record.equipment_id, 'chamber_size') and record.equipment_id.chamber_size:
                # massa_eto em Kg, chamber_size em L, resultado em mg/L
                record.concentracao_eto_camara = (record.massa_eto*1000000 ) / record.equipment_id.chamber_size
            else:
                record.concentracao_eto_camara = 0.0

    @api.model
    def process_cycle_data_eto_v1(self,header,body,values):
        """
        Cria ou atualiza os dados do ciclo de ETO a partir do cabeçalho e corpo recebidos.
        
        Este método é chamado dinamicamente pelo método create_new_cycle da classe SupervisorioCiclos,
        que por sua vez é chamado pelo método action_ler_diretorio_ciclos.
        
        Args:
            header (dict): Dicionário com parâmetros do cabeçalho do ciclo
                Exemplo: {
                    'Data:': '13-4-2024',
                    'Hora:': '17:21:17', 
                    'Equipamento:': 'ETO01',
                    'Operador:': 'FLAVIOR',
                    'Cod. ciclo:': '7819',
                    'Ciclo Selecionado:': 'CICLO 01'
                }
            body (dict): Dicionário com dados do corpo do ciclo
            values (dict): Valores iniciais a serem mesclados
            create (bool): Se True, cria novo ciclo. Se False, atualiza existente
            id_ciclo (int): ID do ciclo para atualização (necessário se create=False)
            
        Returns:
            record: Registro do ciclo criado/atualizado
            
        Raises:
            UserError: Se id_ciclo não informado ao tentar atualizar
        """
        # self.ensure_one()
        _logger.debug(f"Header do ciclo: {header}")
        _logger.debug(f"Body do ciclo: {body}")
        

        novos_valores = {
            'name': header['file_name'],
            'start_date': self.data_hora_to_datetime(header['Data:'],header['Hora:']),
            'batch_number': header['Cod. ciclo:'],
          
            
            
        }
        _logger.debug(f"Novos valores: {novos_valores}")
        values.update(novos_valores)
       
        _logger.debug(f"base_values: {values}")
        
        #ciclo não existe, cria novo ciclo
        if not self.id:
            ciclo = self.create(values)
            _logger.debug(f"Ciclo não existe, criando novo ciclo. Ciclo criado: {ciclo.name}")
            return ciclo
        
        #ciclo existe, atualiza ciclo
        _logger.debug(f"Ciclo existe, atualizando ciclo {self.name}")

        values['state'] = 'em_andamento'
        if body['state'] == 'concluido':
            
            values['state'] = 'concluido'
        if body['state'] == 'abortado':

            values['state'] = 'abortado'
        # Obtém a data de finalização do ciclo e adiciona 3 horas para compensar o fuso horário
        if body['state'] == 'em_andamento':
            _logger.debug(f"Ciclo em andamento, atualizando ciclo {self.name}: values: {values}")
            return self.write(values)
        
        
        # Busca a tag de finalização configurada no tipo de ciclo
        end_tag = self.cycle_type_id.end_datetime_tag if self.cycle_type_id else None
        data_fim = None
        _logger.debug(f"end_tag: {end_tag}")
        _logger.debug(f"body['fase']: {body['fase']}")
        if end_tag and 'fase' in body:
            # Procura a fase que corresponde à tag de finalização
            for fase in body['fase']:
                if len(fase) > 1 and fase[1] == end_tag:
                    data_fim = fase[0]
                    break
        # Se não encontrou pela tag, usa o último registro do body['data']
        if not data_fim:
            data_fim = body['data'][-1][0]
        _logger.debug(f"data_fim: {data_fim}")
        data_fim_ajustada = data_fim + timedelta(hours=3)
        _logger.debug(f"data_fim_ajustada: {data_fim_ajustada}")
        values['end_date'] = data_fim_ajustada   
        _logger.debug(f"Ciclo finalizado, atualizando ciclo {self.name}: values: {values}")
        
        return self.write(values)

    @api.model
    def process_cycle_data_eto_v2(self,header,body,values):
        """
        Cria ou atualiza os dados do ciclo de ETO a partir do cabeçalho e corpo recebidos.
        
        Este método é chamado dinamicamente pelo método create_new_cycle da classe SupervisorioCiclos,
        que por sua vez é chamado pelo método action_ler_diretorio_ciclos.
        
        Args:
            header (dict): Dicionário com parâmetros do cabeçalho do ciclo
                Exemplo: {
                    'Data:': '13-4-2024',
                    'Hora:': '17:21:17', 
                    'Equipamento:': 'ETO01',
                    'Operador:': 'FLAVIOR',
                    'Cod. ciclo:': '7819',
                    'Ciclo Selecionado:': 'CICLO 01'
                }
            body (dict): Dicionário com dados do corpo do ciclo
            values (dict): Valores iniciais a serem mesclados
            create (bool): Se True, cria novo ciclo. Se False, atualiza existente
            id_ciclo (int): ID do ciclo para atualização (necessário se create=False)
            
        Returns:
            record: Registro do ciclo criado/atualizado
            
        Raises:
            UserError: Se id_ciclo não informado ao tentar atualizar
        """

        # self.ensure_one()

        _logger.debug(f"Header do ciclo: {header}")


        # procurando o ciclo selecionado no dicionário header
        ciclo_selecionado = header['Ciclo Selecionado:']
        cycle_type = self.cycle_type_id or self.equipment_id.cycle_type_id
        cycle_features_id = cycle_type.cycle_features_id.filtered(lambda x: x.name == ciclo_selecionado)
        _logger.debug(f"achado o cycle_features_id: {cycle_features_id.name}")
      
      
        hora_str = header['Hora:']
        data_obj = header['Data:']
        # Extraindo horas, minutos e segundos da string de hora
        data_completa = self.data_hora_to_datetime(data_obj,hora_str)
       

        
        novos_valores = {
            'name': header['file_name'],
            'start_date': data_completa,  # Remove timezone antes de salvar
            'batch_number': header['Cod. ciclo:'],
            'cycle_features_id': cycle_features_id.id,
        }
        _logger.debug(f"Novos valores: {novos_valores}")
        values.update(novos_valores)
       
        _logger.debug(f"valores atualizados: {values}")
        #ciclo não existe, cria novo ciclo
        _logger.debug(f"self.id: {self.id}")
        if not self.id:
            ciclo = self.create(values)
            _logger.debug(f"Ciclo não existe, criando novo ciclo. Ciclo criado: {ciclo.name}")
            return ciclo
        #ciclo existe, atualiza ciclo
        #verificando se ciclo finalizou
        # procurando no body o valor de 'CICLO FINALIZADO'
        
        values['state'] = 'em_andamento'
        if body['state'] == 'concluido':           
            values['state'] = 'concluido'
        if body['state'] == 'abortado':

            values['state'] = 'abortado'
        # Obtém a data de finalização do ciclo e adiciona 3 horas para compensar o fuso horário
        if body['state'] == 'em_andamento':
            
            return self.write(values)
        
        # Verifica se body['data'] existe e não está vazio antes de acessar o último elemento
        _logger.debug(f"body['fase']: {body.get('fase')}")
        if body.get('data') and len(body['data']) > 0:
            # Busca a configuração da tag de fim de ciclo no tipo de ciclo
            tag_fim = self.cycle_type_id.end_datetime_tag if self.cycle_type_id else None
            data_fim = None

            if tag_fim:
                # Procura a tag de fim de ciclo em body['fase']
                fases = body.get('fase', [])
                for fase in fases:
                    # fase[1] é o nome da fase, fase[0] é o datetime
                    if len(fase) > 1 and fase[1] == tag_fim:
                        data_fim = fase[0]
                        _logger.debug(f"Encontrou tag de fim de ciclo '{tag_fim}' em body['fase']: {data_fim}")
                        break

            if not data_fim:
                # Se não encontrou a tag ou não está configurada, usa o último item de body['data']
                _logger.debug(f"Tag de fim de ciclo não encontrada ou não configurada. Usando último item de body['data']")
                data_fim = body['data'][-1][0]

            data_fim_ajustada = data_fim + timedelta(hours=3)
            values['end_date'] = data_fim_ajustada
        else:
            _logger.warning("body['data'] está vazio ou não existe. Não foi possível definir 'end_date'.")

            
        return self.write(values)
        
    def data_hora_to_datetime(self, data, hora):
        """
        Converte strings de data e hora em um objeto datetime.
        
        Args:
            data: Objeto de data
            hora: String no formato 'HH:MM:SS'
            
        Returns:
            datetime: Objeto datetime com a data e hora combinadas e ajustadas para o fuso horário
        """
        # Extraindo horas, minutos e segundos da string
        horas, minutos, segundos = map(int, hora.split(':'))
        
        # Combinando o objeto data com a hora extraída
        data_completa = datetime.combine(data, time(horas, minutos, segundos))
        
        
        # Convertendo para o formato compatível com fields.Datetime do Odoo
        
        
        # Adicionando 3 horas ao horário para compensar diferença de fuso
        _logger.debug(f"data_completa: {data_completa}")
        data_completa = data_completa + timedelta(hours=3)
        _logger.debug(f"data_completa + 3 horas: {data_completa}")
        return data_completa
    

    
class SupervisorioCiclosEtoDetalhes(models.Model):
    _name = 'afr.supervisorio.ciclos.eto.detalhes'
    _description = 'Detalhes do Ciclo de Esterilização por ETO'

    eto_temperature = fields.Float('Temperatura de Esterilização (°C)', help='Temperatura alvo para esterilização')
    eto_pressure = fields.Float('Pressão de Esterilização (Bar)', help='Pressão alvo para esterilização')
    eto_phases = fields.Integer('Número de Fases de Vácuo', help='Número de fases de vácuo do ciclo')
    eto_drying_time = fields.Float('Tempo de Secagem (min)', help='Duração da fase de secagem') 