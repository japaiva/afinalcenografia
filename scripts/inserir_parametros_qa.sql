-- Script SQL para inserir os parâmetros padrão de QA
-- Executar no shell do Django com: python manage.py dbshell < inserir_parametros_qa.sql

-- QA_ENABLED: Ativar/desativar geração automática de QA
INSERT INTO parametros_indexacao (nome, descricao, valor, tipo, categoria)
VALUES (
    'QA_ENABLED',
    'Ativar/desativar geração automática de perguntas e respostas ao processar manual',
    'true',
    'bool',
    'qa'
) ON CONFLICT (nome) DO UPDATE SET
    valor = 'true',
    descricao = 'Ativar/desativar geração automática de perguntas e respostas ao processar manual',
    tipo = 'bool',
    categoria = 'qa';

-- QA_PROVIDER: Provedor de IA para geração de QA
INSERT INTO parametros_indexacao (nome, descricao, valor, tipo, categoria)
VALUES (
    'QA_PROVIDER',
    'Provedor de IA para geração de perguntas e respostas (openai ou anthropic)',
    'openai',
    'str',
    'qa'
) ON CONFLICT (nome) DO UPDATE SET
    valor = 'openai',
    descricao = 'Provedor de IA para geração de perguntas e respostas (openai ou anthropic)',
    tipo = 'str',
    categoria = 'qa';

-- QA_MODEL: Modelo específico a ser usado
INSERT INTO parametros_indexacao (nome, descricao, valor, tipo, categoria)
VALUES (
    'QA_MODEL',
    'Modelo específico a ser usado para geração de QA (gpt-4o, gpt-3.5-turbo, claude-3-opus-20240229, etc.)',
    'gpt-4o',
    'str',
    'qa'
) ON CONFLICT (nome) DO UPDATE SET
    valor = 'gpt-4o',
    descricao = 'Modelo específico a ser usado para geração de QA (gpt-4o, gpt-3.5-turbo, claude-3-opus-20240229, etc.)',
    tipo = 'str',
    categoria = 'qa';

-- QA_MAX_PAIRS_PER_CHUNK: Número máximo de pares QA por chunk
INSERT INTO parametros_indexacao (nome, descricao, valor, tipo, categoria)
VALUES (
    'QA_MAX_PAIRS_PER_CHUNK',
    'Número máximo de pares pergunta-resposta a serem gerados a partir de cada chunk',
    '5',
    'int',
    'qa'
) ON CONFLICT (nome) DO UPDATE SET
    valor = '5',
    descricao = 'Número máximo de pares pergunta-resposta a serem gerados a partir de cada chunk',
    tipo = 'int',
    categoria = 'qa';

-- QA_MIN_CONFIDENCE: Pontuação mínima de confiança para incluir um par QA
INSERT INTO parametros_indexacao (nome, descricao, valor, tipo, categoria)
VALUES (
    'QA_MIN_CONFIDENCE',
    'Pontuação mínima de confiança para incluir um par pergunta-resposta nos resultados (0.0 a 1.0)',
    '0.7',
    'float',
    'qa'
) ON CONFLICT (nome) DO UPDATE SET
    valor = '0.7',
    descricao = 'Pontuação mínima de confiança para incluir um par pergunta-resposta nos resultados (0.0 a 1.0)',
    tipo = 'float',
    categoria = 'qa';

-- QA_DELAY: Atraso entre chamadas à API
INSERT INTO parametros_indexacao (nome, descricao, valor, tipo, categoria)
VALUES (
    'QA_DELAY',
    'Atraso em segundos entre chamadas à API durante geração de QA para evitar limites de taxa',
    '2',
    'int',
    'qa'
) ON CONFLICT (nome) DO UPDATE SET
    valor = '2',
    descricao = 'Atraso em segundos entre chamadas à API durante geração de QA para evitar limites de taxa',
    tipo = 'int',
    categoria = 'qa';

-- QA_TEMPERATURE: Temperatura para geração de QA
INSERT INTO parametros_indexacao (nome, descricao, valor, tipo, categoria)
VALUES (
    'QA_TEMPERATURE',
    'Temperatura (aleatoriedade) para geração de QA (0.0 a 1.0)',
    '0.3',
    'float',
    'qa'
) ON CONFLICT (nome) DO UPDATE SET
    valor = '0.3',
    descricao = 'Temperatura (aleatoriedade) para geração de QA (0.0 a 1.0)',
    tipo = 'float',
    categoria = 'qa';