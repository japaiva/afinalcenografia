# Base de Conhecimento - Projeto Afinal Cenografia

## Visão Geral do Projeto
O projeto consiste em uma solução de briefing digital para a Afinal Cenografia, desenvolvida em Python/Django. O objetivo é criar um sistema que permita que clientes preencham briefings de projetos cenográficos, com validação por IA e gerenciamento de arquivos.

## Estrutura do Sistema

### Arquitetura Base
- **Linguagem/Framework**: Python e Django
- **Banco de Dados**: PostgreSQL
- **Armazenamento de Arquivos**: MinIO
- **Processamento de IA**: LangChain (com OpenAI ou Anthropic)
- **Infraestrutura**: Docker Swarm na VPS

### Níveis de Usuário
- Administrador: Acesso a todos os cadastros e funcionalidades
- Gestor: Gerenciamento de projetos e acompanhamento
- Projetista: Acesso aos briefings aprovados
- Cliente: Criação e edição de briefings

### Modelo de Dados
- Utilizaremos o modelo de usuário padrão do Django (não customizado)
- Criação de um modelo `PerfilUsuario` vinculado ao usuário padrão para associar à empresa
- O cliente estará vinculado a uma empresa
- Os projetos (briefings) serão vinculados a uma empresa

## Funcionalidades Principais

### Portal do Cliente
- Login seguro
- Inclusão, alteração e exclusão de projetos/briefings
- Upload de arquivos anexos categorizados
- Aprovação de briefings para envio ao projetista
- Interação com IA para esclarecimentos e validações

### Sistema de Briefing
- Interface dividida em duas partes:
  1. Formulário com perguntas e campos para preenchimento
  2. Área de interação com a IA para perguntas e feedback
- Sistema de validação visual (verde: aprovado, vermelho: erro, branco: não validado)
- Navegação entre páginas (avançar/voltar)
- Envio apenas quando todas as seções estiverem validadas

### Validação por IA
- Análise de consistência entre orçamento e especificações
- Verificação de realismo de prazos
- Detecção de informações incompletas ou contraditórias
- Sugestões de melhorias para o briefing
- Interface de chat para perguntas e respostas

### Gerenciamento de Arquivos
- Upload via botão e/ou drag-and-drop
- Categorização de arquivos (referências, plantas, renders, etc.)
- Armazenamento no MinIO
- Metadados e rastreamento de arquivos
- Controle de acesso

### Comunicação e Notificações
- Futura implementação de notificações via WhatsApp
- Integração planejada com Trello para pipeline de projetos ou outro
- Sistema de mensagens entre projetista e cliente na etapa de validação

## Decisões Técnicas

### Autenticação e Usuários
- Usar o modelo de usuário padrão do Django
- Criar um modelo de perfil vinculado com `OneToOneField`
- Associar usuários a empresas através do perfil

### Interação com IA
- Utilizar LangChain para estruturar prompts e validações
- Inicialmente focar na engenharia de prompts
- Implementar streaming de respostas via Server-Sent Events (SSE)
- RAG (Retrieval-Augmented Generation)

### Armazenamento de Arquivos
- Usar MinIO para armazenamento de arquivos (compatível com S3)
- Criar serviço dedicado para gerenciar upload/download
- Rastrear metadados dos arquivos no banco de dados

### Estrutura de Apps Django
- **core**: Modelos centrais como Empresa
- **accounts**: Gerenciamento de perfis de usuário
- **projetos**: Modelos para projetos e briefings
- **storage**: Gerenciamento de arquivos
- **cliente**: Portal do cliente
- **projetista**: Portal do projetista
- **gestor**: Portal do gestor
- **admin_portal**: Portal administrativo
- **api**: Endpoints da API

## Regras de Negócio

### Validação de Briefing
- Orçamento deve ser compatível com o escopo e complexidade
- Prazos devem ser realistas para o tipo de projeto
- Informações técnicas devem ser suficientes e consistentes
- A IA deve alertar sobre incompatibilidades entre requisitos e viabilidade

### Fluxo de Aprovação
- Cliente preenche briefing com auxílio da IA
- Cada seção precisa ser validada (status verde)
- Cliente aprova o briefing completo
- Briefing fica disponível para o projetista
- Projetista pode solicitar esclarecimentos via sistema de mensagens

## Considerações para a IA

A IA deve atuar como um projetista experiente, considerando:

1. **Consistência de Orçamento:**
   - Verificar se o orçamento proposto é realista para o tipo e escala do projeto
   - Alertar sobre inconsistências entre expectativas e recursos disponíveis

2. **Viabilidade Técnica:**
   - Validar se as especificações técnicas são coerentes entre si
   - Verificar se dimensões, materiais e efeitos especiais propostos são compatíveis

3. **Prazos Realistas:**
   - Analisar se o cronograma é viável considerando a complexidade do projeto
   - Sugerir ajustes quando detectar prazos irrealistas

4. **Completude de Informações:**
   - Identificar informações essenciais que estejam faltando no briefing
   - Sugerir campos adicionais baseados no contexto do projeto

5. **Linguagem Adequada:**
   - Comunicar-se de forma clara e profissional
   - Fazer perguntas direcionadas para esclarecer pontos ambíguos