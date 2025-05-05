# scripts/init_campo_perguntas.py

from core.models import CampoPergunta

def criar_campo_perguntas():
    """
    Cria as perguntas padrão para campos específicos do cadastro da feira.
    """
    perguntas = [
        # Nome da feira
        ('nome', 'Qual é o nome oficial da feira?', 3),
        ('nome', 'Como se chama esta feira ou evento?', 2),
        ('nome', 'Qual é o título do evento?', 1),
        
        # Local
        ('local', 'Qual é o endereço completo da feira?', 3),
        ('local', 'Onde será realizada a feira?', 2),
        ('local', 'Em que local acontecerá o evento?', 1),
        
        # Data e horário
        ('data_horario', 'Quais são os dias e horários de funcionamento da feira?', 3),
        ('data_horario', 'Qual o período e horário de funcionamento do evento?', 2),
        ('data_horario', 'Em quais datas e horários o evento estará aberto?', 1),
        
        # Público-alvo
        ('publico_alvo', 'Qual é o público-alvo da feira?', 3),
        ('publico_alvo', 'A quem se destina este evento?', 2),
        ('publico_alvo', 'Esta feira é aberta ao público geral ou exclusiva para profissionais?', 1),
        
        # Eventos Simultâneos
        ('eventos_simultaneos', 'Existem eventos simultâneos ou paralelos durante a feira?', 3),
        ('eventos_simultaneos', 'Quais eventos ocorrem simultaneamente com esta feira?', 2),
        
        # Promotora
        ('promotora', 'Qual empresa é a organizadora ou promotora da feira?', 3),
        ('promotora', 'Quem está organizando este evento?', 2),
        ('promotora', 'Qual é a empresa responsável pela organização da feira?', 1),
        
        # Período montagem
        ('periodo_montagem', 'Qual é o período de montagem dos estandes?', 3),
        ('periodo_montagem', 'Quais são as datas e horários para montagem?', 2),
        ('periodo_montagem', 'Quando será permitida a montagem dos estandes?', 1),
        
        # Portão de acesso
        ('portao_acesso', 'Qual é o portão de acesso para montagem dos estandes?', 3),
        ('portao_acesso', 'Por onde deve ser feito o acesso para a montagem?', 2),
        
        # Período desmontagem
        ('periodo_desmontagem', 'Qual é o período de desmontagem dos estandes?', 3),
        ('periodo_desmontagem', 'Quais são as datas e horários para desmontagem?', 2),
        ('periodo_desmontagem', 'Quando deve ser realizada a desmontagem dos estandes?', 1),
        
        # Altura estande
        ('altura_estande', 'Qual é a altura máxima permitida para os estandes?', 3),
        ('altura_estande', 'Quais são os limites de altura para os estandes?', 2),
        ('altura_estande', 'Qual a altura máxima que um estande pode ter nesta feira?', 1),
        
        # Palcos
        ('palcos', 'Quais são as regras para montagem de palcos nos estandes?', 3),
        ('palcos', 'Existem normas específicas para palcos?', 2),
        
        # Piso elevado
        ('piso_elevado', 'Quais são as regras para piso elevado nos estandes?', 3),
        ('piso_elevado', 'Existem normas para piso elevado?', 2),
        
        # Mezanino
        ('mezanino', 'É permitido construir mezanino nos estandes? Quais as regras?', 3),
        ('mezanino', 'Quais são as normas para mezanino?', 2),
        
        # Iluminação
        ('iluminacao', 'Quais são as regras para iluminação dos estandes?', 3),
        ('iluminacao', 'Existem restrições para a iluminação dos estandes?', 2),
        
        # Outros
        ('outros', 'Quais outras regras importantes existem para montagem de estandes?', 3),
        ('outros', 'Há outras normas ou restrições não cobertas em outras categorias?', 2),
        
        # Materiais
        ('materiais', 'Quais materiais são permitidos ou proibidos na montagem dos estandes?', 3),
        ('materiais', 'Existem restrições sobre materiais que podem ser utilizados?', 2),
        ('materiais', 'Quais materiais são proibidos na construção dos estandes?', 1),
        
        # Credenciamento
        ('credenciamento', 'Quais são as datas e procedimentos para credenciamento?', 3),
        ('credenciamento', 'Como funciona o credenciamento para esta feira?', 2),
        ('credenciamento', 'Quando deve ser feito o credenciamento para a feira?', 1),
    ]
    
    # Limpar registros anteriores (opcional)
    # CampoPergunta.objects.all().delete()
    
    # Criar registros
    for campo, pergunta, prioridade in perguntas:
        CampoPergunta.objects.get_or_create(
            campo=campo,
            pergunta=pergunta,
            defaults={
                'prioridade': prioridade,
                'ativa': True
            }
        )
    
    print(f"Criadas {len(perguntas)} perguntas para campos.")

if __name__ == "__main__":
    criar_campo_perguntas()