# Dify Enterprise Observability Hub 🚀

Este diretório contém a estrutura e implementação de uma arquitetura de observabilidade tripla de nível enterprise para o **Dify**, integrando concorrentemente **Langfuse**, **Opik (by Comet ML)** e **Arize Phoenix**.

---

## 🗺️ 1. Arquitetura do Sistema e Fluxo de Telemetria

A arquitetura foi projetada para garantir visibilidade ponta a ponta sem redundância de dados. Cada componente possui responsabilidades claramente delineadas no ecossistema de LLMOps:

```
                         +-----------------------------------+
                         |         Usuário / Cliente         |
                         +-----------------+-----------------+
                                           |
                                           v
                         +-----------------+-----------------+
                         |      Dify AI Orchestrator         |
                         |  (Agents, Chatflows & Workflows)  |
                         +----+------------+------------+----+
                              |            |            |
         (Conexão Nativa)     |            |            | (Conexão Nativa)
      +-----------------------+            |            +-----------------------+
      |                                    |                                    |
      v                                    v (Webhook Events)                   v
+-----+---------------+          +---------+-----------+          +-------------+-----+
|   LANGFUSE (v3+)    |          |  Python OTel Gateway|          |    OPIK by COMET    |
|                     |          | (FastAPI Middleware)|          |                     |
| - Tracing de Nós    |          +---------+-----------+          | - Evals Contínuos   |
| - Latência de Fluxo |                    |                      | - Geração de Métricas|
| - Custos & Tokens   |                    | (OTel over gRPC)     | - Prompt Playground |
| - Prompt Management |                    v                      | - RAG Triad Guard   |
+---------------------+          +---------+-----------+          +---------------------+
                                 |    ARIZE PHOENIX    |
                                 |                     |
                                 | - Hallucination Det |
                                 | - Vector Drift      |
                                 | - UMAP / T-SNE      |
                                 | - OTel Traces       |
                                 +---------------------+
```

### 🔍 Divisão de Responsabilidades (Anti-Redundância)

Para evitar duplicidade no armazenamento e processamento de dados e otimizar custos com telemetria, as ferramentas atuam em camadas complementares:

1. **Langfuse (v3+)**:
   - **Foco principal**: Gestão de performance operacional em tempo real (APM), controle financeiro (FinOps) e controle de versão de prompts.
   - **Métricas**: Latência precisa no nível de nó (Node-level latency), consumo exato de tokens por modelo/provedor, e custo financeiro baseado em tabelas de preços customizáveis.
   - **Funcionalidade exclusiva**: Prompt Management Studio (versionamento dinâmico de prompts consumidos diretamente pelo Dify via SDK).

2. **Opik (by Comet ML)**:
   - **Foco principal**: Avaliação heurística e automatizada de qualidade de geração (LLM-as-a-Judge) e auditoria de guardrails pré-produção.
   - **Métricas**: Answer Relevance, Context Recall, Levenshtein Distance (para testar regressões de outputs estruturados/JSON) e alinhamento de diretrizes corporativas.
   - **Funcionalidade exclusiva**: Integração nativa com Dify enviando logs de workflow de ponta a ponta para rodar experimentos comparativos de prompts e hiperparâmetros (prompts playgrounds).

3. **Arize Phoenix**:
   - **Foco principal**: Detecção profunda de anomalias estatísticas, análise de distribuição de embeddings e prevenção de alucinação baseada em representações de alta dimensão.
   - **Métricas**: Vetores de drift geométrico, visualização UMAP tridimensional das consultas dos usuários comparadas com a base de conhecimento (para identificar "gaps" no RAG), e RAG Triad Evals.
   - **Funcionalidade exclusiva**: Suporte completo a OpenTelemetry (OTel), permitindo ingestão unificada e estruturação de gráficos de chamadas complexas com visualização em grafos acíclicos dirigidos (DAGs) de execução.

---

## 📂 Estrutura de Arquivos do Projeto

```
dify-observability-hub/
├── README.md                  # Documentação e Arquitetura do Sistema
├── DEPLOYMENT_GUIDE.md        # Passo a passo detalhado de implantação corporativa
├── docker-compose.yml         # Orquestração local unificada (Dify + Stack de Observabilidade)
├── .env.example               # Configurações globais e credenciais das plataformas
├── gateway.py                 # Middleware Python (FastAPI + OTel) para Arize Phoenix
├── evaluate_rag.py            # Script corporativo de avaliação automatizada (Opik + Phoenix)
└── tests/
    └── test_gateway.py        # Testes automatizados do Gateway de Telemetria
```
