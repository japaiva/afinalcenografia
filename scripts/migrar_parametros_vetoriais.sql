-- Atualizar a categoria 'pinecone' para 'connection'
UPDATE parametros_indexacao
SET categoria = 'connection'
WHERE categoria = 'pinecone';

-- Atualizar os nomes dos parâmetros para refletir a nova nomenclatura agnóstica
UPDATE parametros_indexacao
SET nome = 'VECTOR_DB_API_KEY'
WHERE nome = 'PINECONE_API_KEY';

UPDATE parametros_indexacao
SET nome = 'VECTOR_DB_ENVIRONMENT'
WHERE nome = 'PINECONE_ENVIRONMENT';

UPDATE parametros_indexacao
SET nome = 'VECTOR_DB_INDEX_NAME'
WHERE nome = 'PINECONE_INDEX_NAME';

UPDATE parametros_indexacao
SET nome = 'VECTOR_DB_METRIC'
WHERE nome = 'PINECONE_METRIC';

-- Adicionar parâmetro para indicar o provedor
INSERT INTO parametros_indexacao (nome, descricao, valor, tipo, categoria)
VALUES ('VECTOR_DB_PROVIDER', 'Provedor do banco de dados vetorial (ex: pinecone, chroma)', 'pinecone', 'str', 'connection');