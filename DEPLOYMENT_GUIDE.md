# Guia de Implantação e Operação de Observabilidade Dify Enterprise 🛠️

Este guia fornece o passo a passo para inicializar o ambiente de infraestrutura, configurar a integração de telemetria diretamente no painel do **Dify**, conectar os componentes de monitoramento e aplicar as melhores práticas corporativas de segurança e controle financeiro (FinOps).

---

## 🚀 1. Inicialização do Ambiente (Docker Compose)

Antes de iniciar os contêineres, certifique-se de carregar e ajustar as variáveis de ambiente baseadas no template `.env.example`:

```bash
# 1. Copie o template de variáveis de ambiente
cp dify-observability-hub/.env.example dify-observability-hub/.env

# 2. Inicialize todos os serviços em segundo plano (background)
docker compose -f dify-observability-hub/docker-compose.yml up -d
```

### 🛰️ Portas e Serviços Expostos localmente:

| Serviço | Porta | Descrição |
| :--- | :--- | :--- |
| **Dify UI** | `http://localhost:3000` | Painel Web de gerenciamento de fluxos do Dify |
| **Dify API** | `http://localhost:5001` | Gateway API Backend Core do Dify |
| **Langfuse UI** | `http://localhost:3030` | Console de tracing de nós e controle de custos de tokens |
| **Opik UI** | `http://localhost:5151` | Console de avaliação de outputs, playground de prompts e Evals |
| **Arize Phoenix** | `http://localhost:6006` | Dashboard de detecção de alucinação e drift de embeddings |
| **Otel Collector** | `http://localhost:4317` | Receptor gRPC OpenTelemetry para Arize Phoenix |
| **Telemetry Gateway**| `http://localhost:8000` | FastAPI Webhook Receiver customizado para processamento e repasse de logs |

---

## ⚙️ 2. Guia de Configuração no Painel do Dify

### A. Integração com o **Langfuse (v3+)**
1. Acesse o **Dify** em `http://localhost:3000` e entre na sua aplicação desejada (Workflow ou Chatflow).
2. No menu lateral esquerdo, navegue até a seção **"Monitoring"**.
3. Localize e clique em **"Tracing app performance"** (Configurações de Tracing).
4. Selecione **Langfuse** como provedor de Tracing.
5. Insira as credenciais do Langfuse obtidas em `http://localhost:3030/project/settings`:
   - **Host**: `http://langfuse-server:3000` (ou `http://localhost:3030` se configurado externamente)
   - **Public Key**: `pk-lf-dify-enterprise-observability-2026`
   - **Secret Key**: `sk-lf-dify-enterprise-observability-2026`
6. Salve a configuração. O status deverá alterar para **"Started/Active"**.

---

### B. Integração com o **Opik (by Comet ML)**
1. No mesmo painel lateral de **"Monitoring"** em seu app Dify, clique para editar/adicionar um novo provedor de Tracing.
2. Selecione **Opik** na lista de integrações suportadas.
3. Insira as credenciais geradas na interface local do Opik em `http://localhost:5151`:
   - **API Key**: `opik-dify-enterprise-api-key-2026` (Ou deixe em branco caso o Opik Auth esteja desligado localmente em dev)
   - **Project Name**: `Dify-Production-RAG`
   - **Workspace**: `default`
4. Salve e valide se os Workflows executados agora geram traces visíveis na aba **"Traces"** do Opik.

---

### C. Integração do Webhook Customizado para **Arize Phoenix**
Para monitorar desvios de embeddings (embedding drift) e alimentar a telemetria do Phoenix via OpenTelemetry:
1. No console do Dify, acesse **"Settings"** (Configurações de Desenvolvedor do Aplicativo) ou vá na aba de **"Webhooks"** nas configurações de publicação do seu app/workflow.
2. Adicione uma nova URL de Webhook:
   - **URL**: `http://telemetry-gateway:8000/webhook` (no contexto de rede interna do docker-compose) ou `http://localhost:8000/webhook`
   - **Secret/Token**: `dify_enterprise_secure_token_abc123` (Enviado no header `Authorization: Bearer <token>`)
3. Marque os eventos que deseja capturar:
   - `message_end` (conclusão do chat com metadados de tokens e custos)
   - `workflow_finished` (conclusão de fluxos visuais complexos)
   - `ping` (para validação de rota)

---

## 🔒 3. Boas Práticas Corporativas (Produção, Custos e Segurança)

### 🛡️ A. Segurança de Credenciais (Secrets)
- **Nunca** envie chaves de API cruas em repositórios de código aberto. Sempre utilize gerenciadores de segredos enterprise (como *HashiCorp Vault*, *AWS Secrets Manager* ou *Azure Key Vault*) para injetar chaves em tempo de execução.
- O gateway FastAPI foi configurado para validar rigorosamente a assinatura de webhooks do Dify pelo header `Authorization: Bearer <DIFY_WEBHOOK_SECRET>`. Em produção, force o tráfego HTTPs/TLS entre as aplicações.

### 💰 B. Controle de Custos de Telemetria (FinOps)
- Tracing completo a nível de nó LLM pode gerar grandes volumes de dados de logs e chamadas de API, aumentando significativamente os custos de armazenamento e largura de banda de rede.
- **Estratégia de Amostragem (Sampling Rate)**: Configure taxas de amostragem (ex: gravar apenas 10% de traces bem-sucedidos e 100% de traces de erros/falhas).
- **TTL de dados**: Configure políticas automáticas de expiração de dados (Retention Policies) no PostgreSQL do Langfuse/Opik para expirar logs operacionais com mais de 30 dias.

### 📉 C. Redundância de Mapeamento
- **Langfuse** deve ser o ponto principal de telemetria geral de latência de infraestrutura e tokens.
- **Opik** deve ser ativado especificamente em pipelines de testes automatizados de CI/CD e auditoria offline de novos prompts.
- **Arize Phoenix** deve receber dados apenas de produção real, focando na telemetria de detecção de alucinações e avaliação do RAG Triad.
