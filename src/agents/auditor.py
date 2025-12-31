"""
================================================================================
MÓDULO: auditor.py - Agente de IA para Auditoria Fiscal
================================================================================

Este módulo implementa um agente de Inteligência Artificial especializado
em auditoria tributária, capaz de analisar produtos e identificar erros
de classificação fiscal (NCM incorreto).

CONTEXTO DE NEGÓCIO:
--------------------
Muitas empresas classificam produtos incorretamente no sistema fiscal.
Por exemplo, uma cerveja pode estar cadastrada com NCM genérico "99999999"
em vez do NCM correto "22030000" (Cerveja de malte).

Quando o NCM está errado, a empresa pode:
    1. Pagar impostos que não deveria (tributação monofásica)
    2. Deixar de aproveitar benefícios fiscais
    3. Ter problemas com a fiscalização

Este agente usa GPT para analisar a descrição do produto e sugerir
a classificação correta.

ARQUITETURA DO AGENTE:
----------------------
O agente usa o framework CrewAI com a seguinte estrutura:

    ┌─────────────────────────────────────────┐
    │           FiscalAuditorAgent            │
    ├─────────────────────────────────────────┤
    │  ┌─────────────────────────────────┐    │
    │  │         CrewAI Agent            │    │
    │  │  Role: Senior Tax Auditor       │    │
    │  │  LLM: GPT-3.5-turbo            │    │
    │  └─────────────────────────────────┘    │
    │                  │                      │
    │                  ▼                      │
    │  ┌─────────────────────────────────┐    │
    │  │           Task                  │    │
    │  │  Analyze item description       │    │
    │  │  Check if monophasic            │    │
    │  │  Return correct NCM             │    │
    │  └─────────────────────────────────┘    │
    │                  │                      │
    │                  ▼                      │
    │  ┌─────────────────────────────────┐    │
    │  │        Response Parser          │    │
    │  │  Extract [bool, ncm, reason]    │    │
    │  └─────────────────────────────────┘    │
    └─────────────────────────────────────────┘

FORMATO DE RESPOSTA:
--------------------
O agente retorna uma lista Python com 3 elementos:

    [is_monophasic, correct_ncm, reason]
    
    Onde:
    - is_monophasic (bool): True se produto é tributação monofásica
    - correct_ncm (str): Código NCM correto (8 dígitos)
    - reason (str): Explicação da análise

    Exemplos:
    - [True, "22030000", "Beer identified - Heineken brand"]
    - [False, "99999999", "Not a cold drink - appears to be food item"]

DEPENDÊNCIAS:
-------------
    - crewai: Framework de agentes de IA
    - langchain_openai: Integração com OpenAI
    - python-dotenv: Carregamento de variáveis de ambiente

CONFIGURAÇÃO:
-------------
Requer OPENAI_API_KEY configurada no arquivo .env:

    # .env
    OPENAI_API_KEY=sk-your-api-key-here

USO:
----
    from agents.auditor import FiscalAuditorAgent
    
    # Inicializa o agente
    auditor = FiscalAuditorAgent()
    
    # Analisa um item
    resultado = auditor.analyze_item(
        descricao="CERVEJA HEINEKEN LONG NECK 355ML",
        ncm_errado="99999999",
        valor_item=8.99
    )
    
    if resultado[0]:  # is_monophasic
        print(f"NCM correto: {resultado[1]}")
        print(f"Motivo: {resultado[2]}")

Autor: Grande Mestre
Versão: 2.0
Data: Dezembro/2025
================================================================================
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os  # Acesso a variáveis de ambiente
from typing import List, Any, Tuple  # Type hints

# Framework CrewAI para agentes de IA
from crewai import Agent, Task, Crew

# Integração com OpenAI via LangChain
from langchain_openai import ChatOpenAI

# Carregamento de variáveis de ambiente (.env)
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
# Isso disponibiliza OPENAI_API_KEY para o ChatOpenAI
load_dotenv()


# =============================================================================
# CONSTANTES
# =============================================================================

# Modelo de linguagem a ser usado
# GPT-3.5-turbo é mais barato e suficiente para esta tarefa
DEFAULT_MODEL = "gpt-3.5-turbo"

# Temperature 0 = respostas determinísticas (sem "criatividade")
# Importante para análise fiscal onde precisamos de precisão
DEFAULT_TEMPERATURE = 0

# NCMs comuns de produtos monofásicos (para fallback)
COMMON_MONOPHASIC_NCMS = {
    "cerveja": "22030000",
    "refrigerante": "22021000",
    "agua": "22011000",
    "energetico": "22029000"
}


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class FiscalAuditorAgent:
    """
    Agente de IA especializado em auditoria de classificação fiscal.
    
    Este agente utiliza o modelo GPT para analisar descrições de produtos
    e identificar se estão classificados corretamente para fins de
    tributação de PIS/COFINS monofásico.
    
    O agente é especialmente treinado (via prompt) para identificar:
        - Cervejas (NCM 2203.00.00)
        - Refrigerantes (NCM 2202.10.00)
        - Águas minerais (NCM 2201.10.00)
        - Energéticos (NCM 2202.90.00)
    
    Attributes:
        llm (ChatOpenAI): Instância do modelo de linguagem configurado.
    
    Example:
        >>> # Inicialização
        >>> auditor = FiscalAuditorAgent()
        >>> 
        >>> # Análise de item
        >>> resultado = auditor.analyze_item(
        ...     descricao="HEINEKEN LONG NECK 355ML",
        ...     ncm_errado="99999999",
        ...     valor_item=8.99
        ... )
        >>> 
        >>> print(f"É monofásico? {resultado[0]}")
        É monofásico? True
        >>> print(f"NCM correto: {resultado[1]}")
        NCM correto: 22030000
        >>> print(f"Motivo: {resultado[2]}")
        Motivo: Beer identified - Heineken brand
    
    Note:
        - Requer OPENAI_API_KEY configurada no ambiente
        - Custo aproximado: ~$0.001 por análise (GPT-3.5)
        - Latência típica: 1-3 segundos por análise
    
    Raises:
        Exception: Se OPENAI_API_KEY não estiver configurada.
    """
    
    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE):
        """
        Inicializa o agente de auditoria fiscal.
        
        Configura o modelo de linguagem (LLM) com parâmetros otimizados
        para análise fiscal precisa e determinística.
        
        Args:
            model (str): Nome do modelo OpenAI a usar. 
                        Default: "gpt-3.5-turbo"
            temperature (float): Controle de aleatoriedade (0-2).
                                0 = determinístico, 2 = muito criativo.
                                Default: 0 (máxima precisão)
        
        Raises:
            Exception: Se OPENAI_API_KEY não estiver no ambiente.
        
        Example:
            >>> # Inicialização padrão
            >>> auditor = FiscalAuditorAgent()
            >>> 
            >>> # Inicialização com GPT-4 (mais preciso, mais caro)
            >>> auditor_premium = FiscalAuditorAgent(
            ...     model="gpt-4",
            ...     temperature=0
            ... )
        
        Note:
            O modelo GPT-3.5-turbo é recomendado por ser:
            - Mais rápido (~1s vs ~3s do GPT-4)
            - Muito mais barato (~10x mais barato que GPT-4)
            - Suficientemente preciso para esta tarefa específica
        """
        # Verifica se a API key está configurada
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception(
                "OPENAI_API_KEY não encontrada no ambiente. "
                "Configure no arquivo .env"
            )
        
        # Inicializa o modelo de linguagem
        # temperature=0 garante respostas consistentes e determinísticas
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature
        )
        
        # Armazena configurações para referência
        self._model = model
        self._temperature = temperature
    
    def _build_analysis_prompt(
        self, 
        descricao: str, 
        ncm_errado: str, 
        valor_item: float
    ) -> str:
        """
        Constrói o prompt de análise para o agente de IA.
        
        O prompt é cuidadosamente estruturado para:
        1. Fornecer contexto claro sobre a tarefa
        2. Definir regras específicas de classificação
        3. Especificar formato exato de saída
        4. Incluir exemplos para guiar a resposta
        
        Args:
            descricao (str): Nome/descrição do produto a analisar.
            ncm_errado (str): Código NCM atual (possivelmente incorreto).
            valor_item (float): Valor do item em R$.
        
        Returns:
            str: Prompt formatado para envio ao LLM.
        
        Note:
            O prompt está em inglês porque modelos GPT têm melhor
            performance com prompts em inglês, especialmente para
            tarefas de classificação e análise estruturada.
        """
        prompt = f"""
Analyze this item from a Brazilian invoice (Nota Fiscal):

ITEM DATA:
- Description: '{descricao}'
- Current NCM code: '{ncm_errado}'
- Value (R$): {valor_item}

CLASSIFICATION RULES:
1. If item is BEER (Heineken, Brahma, Skol, Antarctica, etc):
   → Correct NCM is 22030000
   → Return: [True, "22030000", "Beer identified"]

2. If item is SODA/SOFT DRINK (Coca-Cola, Pepsi, Fanta, Sprite, Guaraná):
   → Correct NCM is 22021000
   → Return: [True, "22021000", "Soft drink identified"]

3. If item is WATER (mineral, sparkling, natural):
   → Correct NCM is 22011000
   → Return: [True, "22011000", "Water identified"]

4. If item is ENERGY DRINK (Red Bull, Monster, etc):
   → Correct NCM is 22029000
   → Return: [True, "22029000", "Energy drink identified"]

5. Any other item (food, non-beverages, etc):
   → Return: [False, "{ncm_errado}", "Not a monophasic product"]

CRITICAL OUTPUT FORMAT:
- Return ONLY a Python list
- NO text before the list
- NO text after the list
- NO markdown formatting
- NO explanations outside the list

Format: [Is_Monophasic_Boolean, "NCM_Code_String", "Reason_String"]

EXAMPLES OF CORRECT OUTPUT:
[True, "22030000", "Beer identified - Heineken brand"]
[True, "22021000", "Soft drink identified - Coca-Cola"]
[False, "99999999", "Not a cold drink - food item"]

YOUR OUTPUT:
"""
        return prompt
    
    def _create_auditor_agent(self) -> Agent:
        """
        Cria e configura o agente CrewAI para auditoria.
        
        O agente é configurado com:
        - Role: Senior Tax Auditor (define expertise)
        - Goal: Classificação fiscal precisa
        - Backstory: Contexto que orienta comportamento
        - verbose=False: Não imprime logs internos
        - allow_delegation=False: Não delega para outros agentes
        
        Returns:
            Agent: Instância configurada do agente CrewAI.
        
        Note:
            A backstory "You are a strict tax auditor bot" é importante
            para que o modelo entenda que deve ser preciso e conciso,
            não conversacional.
        """
        return Agent(
            role='Senior Tax Auditor',
            goal='Analyze beverage tax classification and identify correct NCM codes for Brazilian products.',
            backstory=(
                "You are a strict tax auditor bot specialized in Brazilian tax law. "
                "You DO NOT speak or explain. You ONLY output structured data. "
                "You are an expert in NCM codes and monophasic taxation of beverages."
            ),
            verbose=False,  # Não imprime logs internos
            allow_delegation=False,  # Não delega tarefas
            llm=self.llm
        )
    
    def _parse_response(self, response: Any, ncm_fallback: str, descricao: str) -> List[Any]:
        """
        Extrai e valida a resposta do agente de IA.
        
        O LLM pode retornar a resposta em diferentes formatos:
        - Objeto CrewOutput com atributo .raw
        - String direta
        - String com texto extra antes/depois da lista
        
        Esta função lida com todas essas variações e extrai
        a lista Python de forma segura.
        
        Args:
            response (Any): Resposta bruta do CrewAI.
            ncm_fallback (str): NCM a usar se parsing falhar.
            descricao (str): Descrição original (para fallback inteligente).
        
        Returns:
            List[Any]: Lista [is_monophasic, ncm, reason] ou fallback.
        
        Example:
            >>> # Resposta limpa
            >>> resp = '[True, "22030000", "Beer identified"]'
            >>> result = self._parse_response(resp, "99999999", "HEINEKEN")
            >>> print(result)
            [True, '22030000', 'Beer identified']
            
            >>> # Resposta com texto extra
            >>> resp = 'Based on analysis: [True, "22030000", "Beer"]'
            >>> result = self._parse_response(resp, "99999999", "HEINEKEN")
            >>> print(result)
            [True, '22030000', 'Beer']
        """
        # Extrai string da resposta (pode ser objeto CrewOutput)
        if hasattr(response, 'raw'):
            result_str = response.raw
        else:
            result_str = str(response)
        
        print(f"   (Retorno da IA): {result_str[:100]}...")  # Log truncado
        
        try:
            # =================================================================
            # Estratégia 1: Encontrar lista no texto
            # =================================================================
            # Procura o primeiro '[' e último ']' para extrair a lista
            start_idx = result_str.find('[')
            end_idx = result_str.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                # Extrai apenas a parte da lista
                clean_result = result_str[start_idx:end_idx]
                
                # Converte string para lista Python usando ast.literal_eval
                # (mais seguro que eval() pois só aceita literais)
                import ast
                parsed_list = ast.literal_eval(clean_result)
                
                # Valida estrutura da lista
                if isinstance(parsed_list, list) and len(parsed_list) >= 3:
                    return parsed_list
            
            # =================================================================
            # Estratégia 2: Fallback inteligente baseado no nome
            # =================================================================
            # Se a IA falhou no formato, tentamos identificar pelo nome
            descricao_upper = descricao.upper()
            
            # Verifica se é cerveja
            beer_keywords = ["HEINEKEN", "BRAHMA", "SKOL", "ANTARCTICA", "CERV", "BEER"]
            if any(kw in descricao_upper for kw in beer_keywords):
                print("   (Fallback: identificado como cerveja pelo nome)")
                return [True, "22030000", "Fallback: Beer identified by name"]
            
            # Verifica se é refrigerante
            soda_keywords = ["COCA", "PEPSI", "FANTA", "SPRITE", "GUARANA", "REFRI"]
            if any(kw in descricao_upper for kw in soda_keywords):
                print("   (Fallback: identificado como refrigerante pelo nome)")
                return [True, "22021000", "Fallback: Soft drink identified by name"]
            
            # Verifica se é água
            water_keywords = ["AGUA", "WATER", "MINERAL"]
            if any(kw in descricao_upper for kw in water_keywords):
                print("   (Fallback: identificado como água pelo nome)")
                return [True, "22011000", "Fallback: Water identified by name"]
            
            # =================================================================
            # Estratégia 3: Fallback seguro (não é monofásico)
            # =================================================================
            return [False, ncm_fallback, "IA respondeu em formato inválido"]
            
        except Exception as e:
            print(f"   (Erro no parsing): {e}")
            return [False, ncm_fallback, f"Erro no parse: {str(e)[:30]}"]
    
    def analyze_item(
        self, 
        descricao: str, 
        ncm_errado: str, 
        valor_item: float
    ) -> List[Any]:
        """
        Analisa um item e determina se é tributação monofásica.
        
        Esta é a função principal do agente. Ela:
        1. Constrói o prompt de análise
        2. Cria o agente e a tarefa
        3. Executa a análise via CrewAI
        4. Parseia e valida a resposta
        5. Retorna resultado estruturado
        
        Args:
            descricao (str): Nome/descrição do produto como aparece na NF-e.
                           Ex: "CERVEJA HEINEKEN LONG NECK 355ML"
            ncm_errado (str): Código NCM atual do produto (8 dígitos).
                            Ex: "99999999" ou "22030000"
            valor_item (float): Valor total do item em R$.
                              Ex: 8.99
        
        Returns:
            List[Any]: Lista com 3 elementos:
                - [0] bool: True se produto é monofásico
                - [1] str: NCM correto (pode ser igual ao atual se não houver erro)
                - [2] str: Motivo/explicação da análise
        
        Example:
            >>> auditor = FiscalAuditorAgent()
            >>> 
            >>> # Análise de cerveja com NCM errado
            >>> resultado = auditor.analyze_item(
            ...     descricao="HEINEKEN LN 355ML",
            ...     ncm_errado="99999999",
            ...     valor_item=8.99
            ... )
            >>> print(resultado)
            [True, '22030000', 'Beer identified - Heineken brand']
            >>> 
            >>> # Análise de item que não é monofásico
            >>> resultado = auditor.analyze_item(
            ...     descricao="ARROZ TIPO 1 TIOJOAO 5KG",
            ...     ncm_errado="10063021",
            ...     valor_item=25.90
            ... )
            >>> print(resultado)
            [False, '10063021', 'Not a monophasic product - food item']
        
        Note:
            - Cada chamada consome tokens da API OpenAI (~100 tokens)
            - Latência típica: 1-3 segundos
            - Em caso de erro, retorna resposta segura (não monofásico)
        
        Raises:
            Não levanta exceções - erros são tratados internamente.
        """
        print(f"   (Conectando à IA... analisando '{descricao[:30]}...')")
        
        try:
            # =================================================================
            # ETAPA 1: Criar agente
            # =================================================================
            auditor_agent = self._create_auditor_agent()
            
            # =================================================================
            # ETAPA 2: Criar tarefa com prompt
            # =================================================================
            prompt = self._build_analysis_prompt(descricao, ncm_errado, valor_item)
            
            task = Task(
                description=prompt,
                agent=auditor_agent,
                expected_output="A Python List like [True, '22030000', 'Reason']"
            )
            
            # =================================================================
            # ETAPA 3: Executar análise
            # =================================================================
            crew = Crew(
                agents=[auditor_agent],
                tasks=[task],
                verbose=False  # Desativa logs verbosos
            )
            
            # kickoff() executa a tarefa e retorna resultado
            resultado_bruto = crew.kickoff()
            
            # =================================================================
            # ETAPA 4: Parsear resposta
            # =================================================================
            return self._parse_response(resultado_bruto, ncm_errado, descricao)
            
        except Exception as e:
            # Em caso de erro (rede, API, etc.), retorna resposta segura
            print(f"   ❌ Erro na análise IA: {e}")
            return [False, ncm_errado, f"Erro na API: {str(e)[:30]}"]


# =============================================================================
# EXEMPLO DE USO (para testes)
# =============================================================================

if __name__ == "__main__":
    """
    Exemplo de uso do agente quando executado diretamente.
    
    Uso:
        $ python auditor.py
        
    Requer OPENAI_API_KEY configurada no .env
    """
    print("=" * 60)
    print("🤖 TESTE DO AGENTE DE AUDITORIA FISCAL")
    print("=" * 60)
    
    try:
        # Inicializa o agente
        auditor = FiscalAuditorAgent()
        print("✅ Agente inicializado com sucesso!\n")
        
        # Casos de teste
        test_cases = [
            ("CERVEJA HEINEKEN LONG NECK 355ML", "99999999", 8.99),
            ("COCA-COLA 2L", "99999999", 9.50),
            ("ARROZ TIPO 1 TIOJOAO 5KG", "10063021", 25.90),
            ("RED BULL ENERGY 250ML", "99999999", 12.00),
        ]
        
        for descricao, ncm, valor in test_cases:
            print(f"\n📋 Testando: {descricao}")
            print(f"   NCM atual: {ncm}")
            print(f"   Valor: R$ {valor}")
            
            resultado = auditor.analyze_item(descricao, ncm, valor)
            
            print(f"\n   📊 Resultado:")
            print(f"   - É monofásico? {resultado[0]}")
            print(f"   - NCM correto: {resultado[1]}")
            print(f"   - Motivo: {resultado[2]}")
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("\n💡 Dica: Configure OPENAI_API_KEY no arquivo .env")
