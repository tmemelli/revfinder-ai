<div align="center">

# 🚀 RevFinder AI

### Sistema Inteligente de Recuperação Tributária
**Identificação automática de PIS/COFINS pagos indevidamente em produtos monofásicos**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-green.svg)](https://openai.com)
[![License](https://img.shields.io/badge/License-Proprietary-yellow.svg)]()

<img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen" alt="Status">

---

**[Demonstração](#-demonstração) • [Funcionalidades](#-funcionalidades) • [Instalação](#-instalação) • [Como Usar](#-como-usar) • [Arquitetura](#-arquitetura)**

</div>

---

## 📋 Sobre o Projeto

O **RevFinder AI** é uma solução completa para identificação e recuperação de créditos tributários de **PIS/COFINS** em empresas do **Simples Nacional**.

Muitos estabelecimentos (restaurantes, bares, mercados) pagam impostos **indevidamente** sobre produtos com tributação **monofásica** - onde o imposto já foi recolhido na indústria.

### 💰 Potencial de Recuperação

| Faturamento Mensal | Recuperação Estimada (5 anos) |
|-------------------|------------------------------|
| R$ 50.000 | R$ 10.000 - R$ 15.000 |
| R$ 100.000 | R$ 20.000 - R$ 35.000 |
| R$ 200.000 | R$ 40.000 - R$ 70.000 |

> **Base Legal:** Lei nº 13.097/2015, arts. 14 a 36 | Decreto nº 8.442/2015

---

## ✨ Funcionalidades

### 🔍 Análise Inteligente
- **Upload múltiplo** de arquivos XML de NF-e
- **Parser robusto** que extrai produtos, NCMs e impostos
- **Identificação automática** de produtos monofásicos

### 🧠 IA com Cache Inteligente
- **3 camadas de identificação:** Banco de Dados → Keywords → IA
- **Cache de aprendizado:** Produto analisado uma vez, nunca mais consulta IA
- **Economia de até 95%** em chamadas de API

### 📊 Dashboard Interativo
- **Métricas em tempo real:** Total recuperável, notas analisadas, erros encontrados
- **Estatísticas de identificação:** Por fonte (BD, Keywords, Cache, IA)
- **Tabela detalhada** com todos os produtos identificados

### 📥 Relatório Profissional
- **Excel formatado** com 3 abas
- **Disclaimer legal** orientando sobre verificação com contador
- **Resumo executivo** para apresentação ao cliente

---

## 🖼️ Demonstração

<div align="center">

### Interface Principal
```
┌─────────────────────────────────────────────────────────────┐
│  🚀 REVFINDER AI - Recuperação Tributária Inteligente       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📁 Upload de Notas Fiscais                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         [  Arraste XMLs aqui  ]                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  📊 RESULTADO DA ANÁLISE                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ R$ 847   │  │ 15       │  │ 23       │  │ 95%      │    │
│  │ Total    │  │ Notas    │  │ Erros    │  │ Economia │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                                                             │
│  [ 📥 BAIXAR RELATÓRIO EXCEL ]                              │
└─────────────────────────────────────────────────────────────┘
```

</div>

---

## 🏗️ Arquitetura

```
revfinder-ai/
│
├── 📱 app.py                    # Aplicação Streamlit
├── 📋 requirements.txt          # Dependências
├── 🔐 .env                      # API Key (não versionado)
│
└── 📁 src/
    ├── 🤖 agents/
    │   └── auditor.py           # Agente IA (CrewAI + GPT-4)
    │
    ├── ⚙️ core/
    │   ├── parser.py            # Parser de XML NF-e
    │   └── ncm_database.py      # Banco de NCMs + Cache
    │
    ├── 💾 database/
    │   └── ncm_rules.json       # Regras + Keywords + Cache IA
    │
    └── 🛠️ utils/
        └── exporter.py          # Gerador de relatórios Excel
```

### 🔄 Fluxo de Processamento

```
XML Upload → Parser → Extrai Produtos
                          ↓
                    ┌─────────────┐
                    │ NCM Database │ ──→ Match? ──→ ✅ Identificado
                    └─────────────┘         │
                          ↓ Não             │
                    ┌─────────────┐         │
                    │  Keywords   │ ──→ Match? ──→ ✅ Identificado
                    └─────────────┘         │
                          ↓ Não             │
                    ┌─────────────┐         │
                    │  Cache IA   │ ──→ Match? ──→ ✅ Identificado
                    └─────────────┘         │
                          ↓ Não             │
                    ┌─────────────┐         │
                    │  GPT-4 IA   │ ──→ Analisa ──→ ✅ Aprende + Identifica
                    └─────────────┘
```

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.11+
- Conta OpenAI com API Key

### Passo a Passo

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/revfinder-ai.git
cd revfinder-ai

# 2. Crie o ambiente virtual
python -m venv venv

# 3. Ative o ambiente
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Configure a API Key
# Crie um arquivo .env na raiz:
echo "OPENAI_API_KEY=sk-sua-chave-aqui" > .env

# 6. Execute!
streamlit run app.py
```

---

## 📖 Como Usar

### 1️⃣ Upload das Notas
- Arraste os arquivos **XML de NF-e** para a área de upload
- Suporta múltiplos arquivos simultaneamente

### 2️⃣ Análise Automática
- Clique em **"Analisar Notas Fiscais"**
- Aguarde o processamento (geralmente < 5 segundos)

### 3️⃣ Visualize os Resultados
- **Total Recuperável:** Valor potencial de restituição
- **Estatísticas:** Como cada produto foi identificado
- **Tabela:** Detalhamento de todos os erros

### 4️⃣ Exporte o Relatório
- Clique em **"Baixar Relatório Excel"**
- Arquivo com 3 abas: Dados, Disclaimer, Resumo

---

## 🧠 Produtos Monofásicos

### ✅ Identificados pelo Sistema

| Categoria | NCM | Exemplos |
|-----------|-----|----------|
| Água Mineral | 22011000 | Crystal, Bonafont, Minalba |
| Refrigerantes | 22021000 | Coca-Cola, Pepsi, Guaraná |
| Cervejas | 22030000 | Heineken, Brahma, Corona |
| Energéticos | 22029900 | Red Bull, Monster |
| Isotônicos | 22029900 | Gatorade, Powerade |
| Chopp | 22030000 | Chopp artesanal, Pilsen |

### ❌ NÃO São Monofásicos

| Categoria | Por quê? |
|-----------|----------|
| Vinhos | Tributação normal |
| Espumantes | Tributação normal |
| Destilados | Tributação normal |
| Drinks | Preparações, não bebidas industrializadas |

---

## ⚙️ Configuração Avançada

### Adicionar Novos Produtos

Edite o arquivo `src/database/ncm_rules.json`:

```json
"_keywords_produtos": {
    "cerveja": [
        "HEINEKEN",
        "SUA_NOVA_MARCA"  // Adicione aqui
    ]
}
```

### Cache de IA

O sistema aprende automaticamente! Quando a IA analisa um produto novo, ele é salvo no cache:

```json
"_aprendizado_ia": {
    "produtos": {
        "NOVO PRODUTO XYZ": {
            "is_monofasico": true,
            "ncm_sugerido": "22030000",
            "motivo": "Cerveja identificada"
        }
    }
}
```

---

## 📊 Performance

| Métrica | Valor |
|---------|-------|
| Tempo médio por nota | < 0.5s |
| Economia em chamadas IA | 95%+ |
| Precisão de identificação | 98%+ |
| Notas processadas/minuto | 100+ |

---

## 🔒 Segurança

- ✅ API Key armazenada em variável de ambiente
- ✅ Arquivos XML processados em memória
- ✅ Nenhum dado enviado para servidores externos (exceto IA)
- ✅ Relatórios gerados localmente

---

## 🤝 Contribuição

Este é um projeto proprietário. Para sugestões ou parcerias:

📧 **Contato:** [seu-email@exemplo.com]

---

## 📜 Licença

Copyright © 2025 **Grande Mestre**. Todos os direitos reservados.

Este software é proprietário e confidencial. Uso não autorizado é proibido.

---

<div align="center">

### Desenvolvido com 💜 por Grande Mestre

**Python** • **Streamlit** • **CrewAI** • **OpenAI GPT-4**

</div>
