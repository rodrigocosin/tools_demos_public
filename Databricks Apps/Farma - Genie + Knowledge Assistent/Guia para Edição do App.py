# Databricks notebook source
# MAGIC %md
# MAGIC # Guia de Edição do App Dexco - Genie + Knowledge Assistant
# MAGIC
# MAGIC ## Estrutura do Projeto
# MAGIC
# MAGIC O app está localizado em:
# MAGIC ```
# MAGIC /Workspace/Users/rodrigo.cosin@databricks.com/Apps/Multi Agent App/Dexco - Genie + Knowledge Assistent/files
# MAGIC ```
# MAGIC
# MAGIC ### Arquivos Principais para Editar:
# MAGIC
# MAGIC #### 1. **Tela Inicial (Greeting)**
# MAGIC * **Arquivo:** `/client/src/components/greeting.tsx`
# MAGIC * Exibe a mensagem "Hello there!" e "How can I help you today?" na tela inicial
# MAGIC
# MAGIC #### 2. **Sidebar (com título do app)**
# MAGIC * **Arquivo:** `/client/src/components/app-sidebar.tsx`
# MAGIC * Contém o título "Chatbot" no cabeçalho da sidebar
# MAGIC
# MAGIC #### 3. **Título da Página**
# MAGIC * **Arquivo:** `/client/index.html`
# MAGIC * Contém o título "Databricks Chat" na tag `<title>`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Passo 0: Configurar o Endpoint do Agente Multi-Agent
# MAGIC
# MAGIC ### 0.1 Localize o arquivo `databricks.yml`
# MAGIC
# MAGIC O arquivo de configuração principal do app está localizado em:
# MAGIC ```
# MAGIC /files/databricks.yml
# MAGIC ```
# MAGIC
# MAGIC ### 0.2 Altere o endpoint do agente
# MAGIC
# MAGIC Abra o arquivo `databricks.yml` e localize a seção `variables` no início do arquivo:
# MAGIC
# MAGIC ```yaml
# MAGIC variables:
# MAGIC   serving_endpoint_name:
# MAGIC     description: "Name of the model serving endpoint to be used by the app"
# MAGIC     default: "mas-89b880c6-endpoint"
# MAGIC ```
# MAGIC
# MAGIC **Exemplo:**
# MAGIC ```yaml
# MAGIC default: "meu-agente-dexco-endpoint"
# MAGIC ```
# MAGIC
# MAGIC ### 0.3 Adicionar o endpoint como recurso do App (via UI durante a criação)
# MAGIC
# MAGIC **IMPORTANTE:** No momento da criação do App via UI, você precisa adicionar o endpoint como um recurso.
# MAGIC
# MAGIC **Passos na UI:**
# MAGIC
# MAGIC 1. **Durante a criação do App**, na tela de configuração, localize a seção **"Resources"** ou **"Recursos"**
# MAGIC
# MAGIC 2. Clique em **"Add Resource"** ou **"Adicionar Recurso"**
# MAGIC
# MAGIC 3. Selecione o tipo de recurso: **"Serving Endpoint"**
# MAGIC
# MAGIC 4. **Escolha o endpoint** do Multi-Agent na lista (ex: `meu-agente-dexco-endpoint`)
# MAGIC
# MAGIC 5. Defina o nível de permissão: **"CAN_QUERY"**
# MAGIC
# MAGIC 6. Clique em **"Add"** ou **"Adicionar"**
# MAGIC
# MAGIC **Por que isso é necessário:**
# MAGIC * O App precisa de permissão explícita para consultar o endpoint
# MAGIC * Adicionar como recurso via UI garante que o App tenha acesso `CAN_QUERY` automaticamente
# MAGIC * Sem essa configuração, o App não conseguirá se comunicar com o agente
# MAGIC * A configuração via UI é mais simples e evita erros de sintaxe no YAML
# MAGIC
# MAGIC **Observação:** Se você esquecer de adicionar o recurso durante a criação, será necessário recriar o App ou adicionar a permissão manualmente nas configurações do endpoint.
# MAGIC
# MAGIC ### 0.4 Informações importantes
# MAGIC
# MAGIC * **Localização completa do arquivo:** `/Workspace/Users/rodrigo.cosin@databricks.com/Apps/Multi Agent App/Dexco - Genie + Knowledge Assistent/files/databricks.yml`
# MAGIC * **Permissões necessárias:** O app precisa ter permissão `CAN_QUERY` no endpoint de serving
# MAGIC * **Multi-Agent Supervisor:** Se você estiver usando um Multi-Agent Supervisor (MAS), também precisa conceder permissão `CAN_QUERY` nos agentes subjacentes que o MAS orquestra
# MAGIC * **Após alterar o databricks.yml:** É necessário fazer o redeploy do app para que as mudanças tenham efeito
# MAGIC
# MAGIC ### 0.5 (Opcional) Configurar múltiplos ambientes
# MAGIC
# MAGIC O arquivo `databricks.yml` suporta diferentes ambientes (dev, staging, prod). Você pode especificar endpoints diferentes para cada ambiente na seção `targets`:
# MAGIC
# MAGIC ```yaml
# MAGIC targets:
# MAGIC   dev:
# MAGIC     mode: development
# MAGIC     default: true
# MAGIC     variables:
# MAGIC       serving_endpoint_name: "endpoint-dev"
# MAGIC       resource_name_suffix: dev-${workspace.current_user.domain_friendly_name}
# MAGIC
# MAGIC   prod:
# MAGIC     mode: production
# MAGIC     variables:
# MAGIC       serving_endpoint_name: "endpoint-prod"
# MAGIC       resource_name_suffix: "prod"
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Passo 1: Personalizar a Tela Inicial (Greeting)
# MAGIC
# MAGIC ### 1.1 Edite o arquivo `greeting.tsx`
# MAGIC
# MAGIC Abra o arquivo:
# MAGIC ```
# MAGIC /client/src/components/greeting.tsx
# MAGIC ```
# MAGIC
# MAGIC ### 1.2 Personalize as mensagens
# MAGIC
# MAGIC Substitua o conteúdo por:
# MAGIC
# MAGIC ```tsx
# MAGIC import { motion } from 'framer-motion';
# MAGIC
# MAGIC export const Greeting = () => {
# MAGIC   return (
# MAGIC     <div
# MAGIC       key="overview"
# MAGIC       className="mx-auto mt-4 flex size-full max-w-3xl flex-col justify-center px-4 md:mt-16 md:px-8"
# MAGIC     >
# MAGIC       <motion.div
# MAGIC         initial={{ opacity: 0, y: 10 }}
# MAGIC         animate={{ opacity: 1, y: 0 }}
# MAGIC         exit={{ opacity: 0, y: 10 }}
# MAGIC         transition={{ delay: 0.5 }}
# MAGIC         className="font-semibold text-xl md:text-2xl"
# MAGIC       >
# MAGIC         Bem-vindo ao Assistente Dexco!
# MAGIC       </motion.div>
# MAGIC       <motion.div
# MAGIC         initial={{ opacity: 0, y: 10 }}
# MAGIC         animate={{ opacity: 1, y: 0 }}
# MAGIC         exit={{ opacity: 0, y: 10 }}
# MAGIC         transition={{ delay: 0.6 }}
# MAGIC         className="text-xl text-zinc-500 md:text-2xl"
# MAGIC       >
# MAGIC         Como posso ajudá-lo hoje?
# MAGIC       </motion.div>
# MAGIC     </div>
# MAGIC   );
# MAGIC };
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Passo 2: Atualizar o Título da Página
# MAGIC
# MAGIC ### 2.1 Edite o arquivo `index.html`
# MAGIC
# MAGIC Abra o arquivo:
# MAGIC ```
# MAGIC /client/index.html
# MAGIC ```
# MAGIC
# MAGIC ### 2.2 Altere o título
# MAGIC
# MAGIC Substitua a linha com `<title>` por:
# MAGIC
# MAGIC ```html
# MAGIC <title>Dexco - Genie + Knowledge Assistant</title>
# MAGIC ```
# MAGIC
# MAGIC ### 2.3 (Opcional) Adicione um favicon personalizado
# MAGIC
# MAGIC Se você tiver um favicon (ícone que aparece na aba do navegador):
# MAGIC
# MAGIC 1. Adicione o arquivo `favicon.ico` em `/client/public/`
# MAGIC 2. A linha já está configurada no HTML:
# MAGIC ```html
# MAGIC <link rel="icon" type="image/x-icon" href="/favicon.ico" />
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Passo 3: (Opcional) Adicionar Logotipo na Tela Inicial
# MAGIC
# MAGIC Se você quiser adicionar o logotipo também na tela de boas-vindas:
# MAGIC
# MAGIC ### 3.1 Edite o `greeting.tsx` novamente
# MAGIC
# MAGIC Adicione o logotipo antes das mensagens:
# MAGIC
# MAGIC ```tsx
# MAGIC import { motion } from 'framer-motion';
# MAGIC
# MAGIC export const Greeting = () => {
# MAGIC   return (
# MAGIC     <div
# MAGIC       key="overview"
# MAGIC       className="mx-auto mt-4 flex size-full max-w-3xl flex-col items-center justify-center px-4 md:mt-16 md:px-8"
# MAGIC     >
# MAGIC       <motion.div
# MAGIC         initial={{ opacity: 0, scale: 0.8 }}
# MAGIC         animate={{ opacity: 1, scale: 1 }}
# MAGIC         exit={{ opacity: 0, scale: 0.8 }}
# MAGIC         transition={{ delay: 0.3 }}
# MAGIC         className="mb-8"
# MAGIC       >
# MAGIC         <img src="/logo-dexco.png" alt="Dexco Logo" className="h-20 w-auto" />
# MAGIC       </motion.div>
# MAGIC       
# MAGIC       <motion.div
# MAGIC         initial={{ opacity: 0, y: 10 }}
# MAGIC         animate={{ opacity: 1, y: 0 }}
# MAGIC         exit={{ opacity: 0, y: 10 }}
# MAGIC         transition={{ delay: 0.5 }}
# MAGIC         className="font-semibold text-xl md:text-2xl"
# MAGIC       >
# MAGIC         Bem-vindo ao Assistente Dexco!
# MAGIC       </motion.div>
# MAGIC       
# MAGIC       <motion.div
# MAGIC         initial={{ opacity: 0, y: 10 }}
# MAGIC         animate={{ opacity: 1, y: 0 }}
# MAGIC         exit={{ opacity: 0, y: 10 }}
# MAGIC         transition={{ delay: 0.6 }}
# MAGIC         className="text-xl text-zinc-500 md:text-2xl"
# MAGIC       >
# MAGIC         Como posso ajudá-lo hoje?
# MAGIC       </motion.div>
# MAGIC     </div>
# MAGIC   );
# MAGIC };
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Passo 4: Traduzir as Sugestões de Perguntas para Português
# MAGIC
# MAGIC As mensagens de sugestão que aparecem na tela inicial estão no arquivo `suggested-actions.tsx`.
# MAGIC
# MAGIC ### 4.1 Edite o arquivo `suggested-actions.tsx`
# MAGIC
# MAGIC Abra o arquivo:
# MAGIC ```
# MAGIC /client/src/components/suggested-actions.tsx
# MAGIC ```
# MAGIC
# MAGIC ### 4.2 Localize o array `suggestedActions`
# MAGIC
# MAGIC Procure pelas linhas 18-21 que contêm:
# MAGIC
# MAGIC ```tsx
# MAGIC const suggestedActions = [
# MAGIC   'How can you help me?',
# MAGIC   'Tell me something I might not know',
# MAGIC ];
# MAGIC ```
# MAGIC
# MAGIC ### 4.3 Substitua pelas mensagens em português
# MAGIC
# MAGIC Altere para:
# MAGIC
# MAGIC ```tsx
# MAGIC const suggestedActions = [
# MAGIC   'Como você pode me ajudar?',
# MAGIC   'Me conte algo que eu possa não saber',
# MAGIC ];
# MAGIC ```
# MAGIC
# MAGIC ### 4.4 Exemplo completo da função
# MAGIC
# MAGIC O trecho completo ficará assim:
# MAGIC
# MAGIC ```tsx
# MAGIC function PureSuggestedActions({ chatId, sendMessage }: SuggestedActionsProps) {
# MAGIC   const { chatHistoryEnabled } = useAppConfig();
# MAGIC   const suggestedActions = [
# MAGIC     'Como você pode me ajudar?',
# MAGIC     'Me conte algo que eu possa não saber',
# MAGIC   ];
# MAGIC
# MAGIC   return (
# MAGIC     <div
# MAGIC       data-testid="suggested-actions"
# MAGIC       className="grid w-full gap-2 sm:grid-cols-2"
# MAGIC     >
# MAGIC       {/* ... resto do código ... */}
# MAGIC     </div>
# MAGIC   );
# MAGIC }
# MAGIC ```
# MAGIC
# MAGIC **Nota:** Você pode personalizar essas sugestões com perguntas mais específicas para o contexto Dexco, como:
# MAGIC * `'Quais dados estão disponíveis?'`
# MAGIC * `'Como posso analisar as vendas?'`
# MAGIC * `'Mostre-me um exemplo de consulta'`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Passo 5: Traduzir o Placeholder da Caixa de Texto
# MAGIC
# MAGIC O texto "Send a message..." que aparece na caixa de entrada está no arquivo `multimodal-input.tsx`.
# MAGIC
# MAGIC ### 5.1 Edite o arquivo `multimodal-input.tsx`
# MAGIC
# MAGIC Abra o arquivo:
# MAGIC ```
# MAGIC /client/src/components/multimodal-input.tsx
# MAGIC ```
# MAGIC
# MAGIC ### 5.2 Localize o componente `PromptInputTextarea`
# MAGIC
# MAGIC Procure pela linha 283 que contém o atributo `placeholder`:
# MAGIC
# MAGIC ```tsx
# MAGIC <PromptInputTextarea
# MAGIC   data-testid="multimodal-input"
# MAGIC   ref={textareaRef}
# MAGIC   placeholder="Send a message..."
# MAGIC   value={input}
# MAGIC   onChange={handleInput}
# MAGIC   minHeight={44}
# MAGIC   maxHeight={200}
# MAGIC   // ... resto das propriedades
# MAGIC />
# MAGIC ```
# MAGIC
# MAGIC ### 5.3 Substitua o placeholder para português
# MAGIC
# MAGIC Altere a linha do `placeholder` para:
# MAGIC
# MAGIC ```tsx
# MAGIC <PromptInputTextarea
# MAGIC   data-testid="multimodal-input"
# MAGIC   ref={textareaRef}
# MAGIC   placeholder="Envie uma mensagem..."
# MAGIC   value={input}
# MAGIC   onChange={handleInput}
# MAGIC   minHeight={44}
# MAGIC   maxHeight={200}
# MAGIC   // ... resto das propriedades
# MAGIC />
# MAGIC ```
# MAGIC
# MAGIC ### Sugestões alternativas de placeholder:
# MAGIC
# MAGIC * `"Digite sua pergunta..."`
# MAGIC * `"Como posso ajudar?"`
# MAGIC * `"Faça uma pergunta..."`
# MAGIC * `"Escreva sua mensagem aqui..."`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resumo das Alterações
# MAGIC
# MAGIC ### Arquivos a serem editados:
# MAGIC
# MAGIC 1. ✅ `/client/src/components/greeting.tsx` - Personalizar mensagens de boas-vindas
# MAGIC 2. ✅ `/client/index.html` - Atualizar título da página
# MAGIC 3. ✅ `/client/public/` - (Opcional) Adicionar arquivo do logotipo para tela inicial
# MAGIC 4. ✅ `/client/src/components/suggested-actions.tsx` - Traduzir sugestões de perguntas
# MAGIC 5. ✅ `/client/src/components/multimodal-input.tsx` - Traduzir placeholder da caixa de texto
# MAGIC
# MAGIC ### Após fazer as alterações:
# MAGIC
# MAGIC 1. **Rebuild do app**: O app precisará ser reconstruído para aplicar as mudanças
# MAGIC 2. **Teste**: Verifique se as alterações estão sendo exibidas corretamente
# MAGIC 3. **Ajuste de tamanho**: Se adicionar logotipo, ajuste as classes CSS (`h-20`, etc.) para o tamanho ideal
# MAGIC
# MAGIC ### Dicas:
# MAGIC
# MAGIC * Use imagens PNG com fundo transparente para melhor resultado do logotipo
# MAGIC * Tamanhos recomendados: 
# MAGIC   * Tela inicial: ~80-100px de altura
# MAGIC   * Favicon: 32x32px ou 64x64px
# MAGIC * Personalize as sugestões de perguntas de acordo com o contexto do seu negócio
# MAGIC * Mantenha consistência na linguagem (português) em todos os textos da interface
# MAGIC * Mantenha backup dos arquivos originais antes de editar

# COMMAND ----------


