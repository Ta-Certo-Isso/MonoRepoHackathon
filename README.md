# 🇧🇷 Tá Certo Isso? - Hackathon Devs de Impacto

> **Missão:** Quebrar a barreira da apatia política transformando o "juridiquês" em papo reto no WhatsApp, gerando engajamento cívico real e ouvidoria inteligente.

## 🎯 O Problema

O brasileiro médio não confia na política, não entende as leis e se sente impotente. A informação chega distorcida (fake news) ou complexa demais (Diário Oficial).

## 💡 A Solução

Uma plataforma integrada que **Ativa** o cidadão com notícias traduzidas, **Assiste** através de um chat interativo com IA no WhatsApp e **Ouve** o sentimento popular para gerar relatórios de impacto.

---

## 🏗 Arquitetura do MonoRepo

O projeto está dividido em 3 módulos interconectados, operando sobre uma base comum de dados e infraestrutura.

```mermaid
graph TD
    subgraph "Módulo 1: Ativação (Montoya)"
        A[Fontes de Dados<br/>API Câmara/News] -->|Coleta| B(Agente Editor IA)
        B -->|Gera Conteúdo| C{Validação Humana}
        C -->|Aprovado| D[Redes Sociais &<br/>Broadcast WhatsApp]
    end

    subgraph "Módulo 2: Assistente (Nichols)"
        D -->|Call to Action| E[Usuário no WhatsApp]
        E <-->|Áudio/Texto| F(Agente Assistente RAG)
        F <-->|Consulta| G[(Vector DB<br/>Leis & Constitução)]
        F <-->|Function Calling| H[Checagem Fatos]
    end

    subgraph "Módulo 3: Ouvidoria (Leli)"
        F -->|Logs de Conversa| I(Agente Analista Sentimento)
        I -->|Classificação| J[(Banco de Dados<br/>Insights)]
        J --> K[Dashboard React]
        K -->|Notificação Retorno| E
    end
```
