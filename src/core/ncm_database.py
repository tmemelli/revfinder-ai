"""
================================================================================
MÓDULO: ncm_database.py - Banco de Dados Inteligente de NCMs Monofásicos
================================================================================

Este módulo gerencia o banco de dados de NCMs monofásicos, oferecendo:
    - Verificação rápida se um NCM é monofásico
    - Identificação de produtos por palavras-chave (sem depender de IA)
    - Sugestão de NCM correto baseado no nome do produto
    - Informações de base legal para relatórios
    - CACHE INTELIGENTE COM APRENDIZADO (v2.1)

VANTAGENS DESTE MÓDULO:
-----------------------
1. ECONOMIA: Identifica produtos sem chamar IA (reduz custo de API)
2. VELOCIDADE: Busca local é instantânea vs 1-3s da IA
3. PRECISÃO: Base de dados oficial da Receita Federal
4. DOCUMENTAÇÃO: Inclui base legal para relatórios profissionais
5. APRENDIZADO: Cache de respostas da IA para economizar em consultas futuras

================================================================================
SISTEMA DE CACHE INTELIGENTE COM APRENDIZADO (v2.1)
================================================================================

O sistema agora possui um cache inteligente que "aprende" com as respostas da IA.

COMO FUNCIONA:
--------------
1. Quando um produto NÃO é encontrado no banco de dados ou keywords,
   o sistema consulta a IA (chamada paga).

2. Após receber a resposta da IA, o sistema SALVA automaticamente no JSON
   em uma seção especial chamada "_aprendizado_ia".

3. Na próxima vez que o MESMO PRODUTO aparecer, o sistema encontra no cache
   e NÃO precisa chamar a IA novamente (economia de dinheiro!).

ECONOMIA REAL:
--------------
    Exemplo: Processando 100 notas fiscais de um restaurante
    
    SEM CACHE:
        - 50 produtos únicos não reconhecidos
        - 100 notas × 50 produtos = 5.000 chamadas de IA 💸💸💸
    
    COM CACHE:
        - 50 produtos únicos não reconhecidos
        - Primeira nota: 50 chamadas (salva no cache)
        - Notas 2-100: 0 chamadas (usa cache)
        - Total: 50 chamadas de IA ✅
        - ECONOMIA: 99% de redução em chamadas!

ESTRUTURA DO CACHE NO JSON:
---------------------------
    {
        "_aprendizado_ia": {
            "_comentario": "Cache de respostas da IA - NÃO EDITAR MANUALMENTE",
            "_total_economizado": 42,
            "produtos": {
                "VH BCO POR CASAL GARCIA SWEET 750ML": {
                    "is_monofasico": false,
                    "ncm_sugerido": "22042100",
                    "motivo": "Not a monophasic product - Wine",
                    "data_aprendizado": "2025-12-30T09:15:00"
                },
                "BATATA INGLESA KG": {
                    "is_monofasico": false,
                    "ncm_sugerido": "07019000",
                    "motivo": "Not a monophasic product - Potato",
                    "data_aprendizado": "2025-12-30T09:15:01"
                }
            }
        }
    }

ESTRUTURA DO JSON COMPLETO:
---------------------------
    {
        "_metadata": { ... },           # Informações sobre a tabela
        "_ncm_simples": { "lista": [] }, # Lista rápida de NCMs
        "_keywords_produtos": { ... },   # Palavras-chave por categoria
        "_aprendizado_ia": { ... },      # NOVO: Cache de respostas da IA
        "2201": {                        # Grupo de NCMs
            "descricao_grupo": "...",
            "ncms": { ... }
        }
    }

EXEMPLO DE USO:
---------------
    from core.ncm_database import NCMDatabase
    
    db = NCMDatabase("caminho/ncm_rules.json")
    
    # Verificar se NCM é monofásico
    if db.is_monofasico("22030000"):
        print("É monofásico!")
    
    # Identificar produto pelo nome
    resultado = db.identificar_por_nome("HEINEKEN LONG NECK 355ML")
    
    # Buscar no cache de aprendizado
    cache = db.buscar_cache_ia("VH BCO POR CASAL GARCIA")
    if cache:
        print("Encontrado no cache! Não precisa chamar IA.")
    
    # Salvar aprendizado da IA (após consulta)
    db.salvar_aprendizado_ia(
        nome_produto="VINHO TINTO SECO",
        is_monofasico=False,
        ncm_sugerido="22042100",
        motivo="Wine is not monophasic"
    )

Autor: Grande Mestre
Versão: 2.1
Data: Dezembro/2025
================================================================================
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from colorama import Fore


class NCMDatabase:
    """
    Banco de dados inteligente de NCMs monofásicos com cache de aprendizado.
    
    Esta classe carrega e gerencia o arquivo JSON com as regras de NCM,
    oferecendo métodos para verificação e identificação de produtos.
    
    NOVO NA v2.1: Sistema de cache inteligente que salva respostas da IA
    para evitar consultas repetidas ao mesmo produto.
    
    Attributes:
        data (dict): Dados completos do JSON
        ncm_lista (list): Lista simples de NCMs monofásicos
        keywords (dict): Dicionário de palavras-chave por categoria
        ncm_detalhes (dict): Mapeamento NCM -> detalhes (descrição, exemplos, etc)
        cache_ia (dict): Cache de respostas da IA (aprendizado)
    
    Example:
        >>> db = NCMDatabase("ncm_rules.json")
        >>> db.is_monofasico("22030000")
        True
        >>> 
        >>> # Buscar no cache antes de chamar IA
        >>> cache = db.buscar_cache_ia("VINHO TINTO")
        >>> if cache:
        ...     print("Economizou uma chamada de IA!")
        >>> 
        >>> # Salvar aprendizado após consultar IA
        >>> db.salvar_aprendizado_ia("VINHO TINTO", False, "22042100", "Wine")
    """
    
    def __init__(self, json_path: str):
        """
        Inicializa o banco de dados carregando o arquivo JSON.
        
        Args:
            json_path (str): Caminho para o arquivo ncm_rules.json
        
        Raises:
            FileNotFoundError: Se o arquivo não existir
            json.JSONDecodeError: Se o JSON estiver malformado
        """
        self.json_path = json_path
        self.data = {}
        self.ncm_lista = []
        self.keywords = {}
        self.ncm_detalhes = {}
        self.metadata = {}
        self.cache_ia = {}  # NOVO: Cache de aprendizado da IA
        
        # Carrega e processa o JSON
        self._load_database()
        self._process_database()
    
    def _load_database(self) -> None:
        """
        Carrega o arquivo JSON do disco.
        
        Raises:
            FileNotFoundError: Se arquivo não existir
            json.JSONDecodeError: Se JSON inválido
        """
        if not os.path.exists(self.json_path):
            print(Fore.YELLOW + f"⚠️  Arquivo {self.json_path} não encontrado.")
            print(Fore.YELLOW + "   Criando banco de dados vazio...")
            self.data = {}
            return
        
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(Fore.GREEN + f"✅ Banco de NCMs carregado: {self.json_path}")
        except json.JSONDecodeError as e:
            print(Fore.RED + f"❌ Erro ao ler JSON: {e}")
            self.data = {}
    
    def _process_database(self) -> None:
        """
        Processa o JSON carregado, extraindo:
        - Lista simples de NCMs
        - Keywords por categoria
        - Detalhes de cada NCM
        - Cache de aprendizado da IA (NOVO v2.1)
        """
        if not self.data:
            return
        
        # Extrai metadata
        self.metadata = self.data.get("_metadata", {})
        
        # Extrai lista simples de NCMs
        ncm_simples = self.data.get("_ncm_simples", {})
        self.ncm_lista = ncm_simples.get("lista", [])
        
        # Extrai keywords
        self.keywords = self.data.get("_keywords_produtos", {})
        
        # NOVO: Extrai cache de aprendizado da IA
        aprendizado = self.data.get("_aprendizado_ia", {})
        self.cache_ia = aprendizado.get("produtos", {})
        total_cache = len(self.cache_ia)
        
        # Processa cada grupo de NCMs para extrair detalhes
        for chave, valor in self.data.items():
            # Ignora chaves especiais (começam com _)
            if chave.startswith("_"):
                continue
            
            # Se tem "ncms", é um grupo de NCMs
            if isinstance(valor, dict) and "ncms" in valor:
                grupo_desc = valor.get("descricao_grupo", "")
                
                for ncm_code, ncm_info in valor["ncms"].items():
                    # Remove sufixos como _EX01, _EX02 para verificação
                    ncm_base = ncm_code.split("_")[0]
                    
                    self.ncm_detalhes[ncm_code] = {
                        "ncm_base": ncm_base,
                        "grupo": grupo_desc,
                        "descricao": ncm_info.get("descricao", ""),
                        "exemplos": ncm_info.get("exemplos", []),
                        "monofasico": ncm_info.get("monofasico", False),
                        "excecoes": ncm_info.get("excecoes", []),
                        "observacao": ncm_info.get("observacao", ""),
                        "base_legal": self.metadata.get("base_legal", "")
                    }
        
        # Calcula total de keywords
        total_keywords = sum(
            len(kw_list) 
            for cat, kw_list in self.keywords.items() 
            if not cat.startswith("_")
        )
        
        print(Fore.BLUE + f"   📊 {len(self.ncm_lista)} NCMs carregados")
        print(Fore.BLUE + f"   🔍 {len(self.keywords)} categorias de keywords ({total_keywords} keywords)")
        
        # NOVO: Mostra estatísticas do cache
        if total_cache > 0:
            print(Fore.CYAN + f"   🧠 {total_cache} produtos no cache de aprendizado")
    
    # =========================================================================
    # NOVO v2.1: SISTEMA DE CACHE INTELIGENTE COM APRENDIZADO
    # =========================================================================
    
    def buscar_cache_ia(self, nome_produto: str) -> Optional[Dict[str, Any]]:
        """
        Busca um produto no cache de aprendizado da IA.
        
        Esta função é chamada ANTES de consultar a IA. Se o produto já foi
        consultado anteriormente, retorna o resultado do cache, economizando
        uma chamada de API.
        
        A busca é feita de forma flexível:
        1. Busca exata pelo nome completo
        2. Busca parcial (nome do produto contém chave do cache)
        3. Busca reversa (chave do cache contém nome do produto)
        
        Args:
            nome_produto (str): Nome/descrição do produto a buscar
        
        Returns:
            dict | None: Dados do cache ou None se não encontrado
            
            Se encontrado, retorna:
            {
                "is_monofasico": bool,
                "ncm_sugerido": str,
                "motivo": str,
                "data_aprendizado": str,
                "fonte": "cache_ia"
            }
        
        Example:
            >>> cache = db.buscar_cache_ia("VH BCO POR CASAL GARCIA SWEET 750ML")
            >>> if cache:
            ...     print(f"Cache hit! Monofásico: {cache['is_monofasico']}")
            ...     print("Economizou uma chamada de IA!")
            ... else:
            ...     print("Cache miss. Precisa consultar IA.")
        
        Note:
            Esta função é O(n) onde n é o tamanho do cache. Para bases muito
            grandes (>10.000 produtos), considerar usar índice invertido.
        """
        if not self.cache_ia:
            return None
        
        nome_upper = nome_produto.upper().strip()
        
        # Busca exata primeiro (mais rápido)
        if nome_upper in self.cache_ia:
            resultado = self.cache_ia[nome_upper].copy()
            resultado["fonte"] = "cache_ia"
            return resultado
        
        # Busca flexível: nome contém chave ou chave contém nome
        for chave_cache, dados in self.cache_ia.items():
            chave_upper = chave_cache.upper()
            
            # Verifica se nome do produto contém a chave do cache
            # Ex: "VH BCO POR CASAL GARCIA SWEET 750ML" contém "CASAL GARCIA"
            if chave_upper in nome_upper or nome_upper in chave_upper:
                resultado = dados.copy()
                resultado["fonte"] = "cache_ia"
                return resultado
        
        return None
    
    def salvar_aprendizado_ia(
        self, 
        nome_produto: str, 
        is_monofasico: bool, 
        ncm_sugerido: str, 
        motivo: str
    ) -> bool:
        """
        Salva o resultado de uma consulta à IA no cache de aprendizado.
        
        Esta função deve ser chamada APÓS receber uma resposta da IA.
        O resultado é salvo no JSON para que consultas futuras ao mesmo
        produto não precisem chamar a IA novamente.
        
        O APRENDIZADO É PERSISTENTE:
        O cache é salvo no arquivo JSON, então mesmo se o programa for
        reiniciado, o aprendizado anterior é mantido.
        
        Args:
            nome_produto (str): Nome/descrição do produto consultado
            is_monofasico (bool): Se a IA identificou como monofásico
            ncm_sugerido (str): NCM sugerido pela IA
            motivo (str): Explicação/motivo retornado pela IA
        
        Returns:
            bool: True se salvou com sucesso, False se erro
        
        Example:
            >>> # Após receber resposta da IA
            >>> resultado_ia = [False, "22042100", "Wine is not monophasic"]
            >>> 
            >>> db.salvar_aprendizado_ia(
            ...     nome_produto="VINHO TINTO SECO 750ML",
            ...     is_monofasico=resultado_ia[0],
            ...     ncm_sugerido=resultado_ia[1],
            ...     motivo=resultado_ia[2]
            ... )
            >>> 
            >>> # Próxima vez que "VINHO TINTO" aparecer, não precisa chamar IA
            >>> cache = db.buscar_cache_ia("VINHO TINTO SECO")
            >>> print(cache)  # Retorna o resultado salvo
        
        Note:
            - O nome do produto é normalizado (uppercase, sem espaços extras)
            - Produtos já existentes no cache são atualizados
            - O arquivo JSON é reescrito a cada salvamento
        """
        try:
            nome_normalizado = nome_produto.upper().strip()
            
            # Prepara os dados do aprendizado
            dados_aprendizado = {
                "is_monofasico": is_monofasico,
                "ncm_sugerido": ncm_sugerido,
                "motivo": motivo,
                "data_aprendizado": datetime.now().isoformat()
            }
            
            # Atualiza cache em memória
            self.cache_ia[nome_normalizado] = dados_aprendizado
            
            # Prepara estrutura para salvar no JSON
            if "_aprendizado_ia" not in self.data:
                self.data["_aprendizado_ia"] = {
                    "_comentario": "Cache de respostas da IA - Gerado automaticamente pelo sistema",
                    "_total_economizado": 0,
                    "produtos": {}
                }
            
            # Adiciona produto ao cache
            self.data["_aprendizado_ia"]["produtos"][nome_normalizado] = dados_aprendizado
            
            # Salva no arquivo JSON
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            
            print(Fore.CYAN + f"   🧠 Aprendizado salvo: {nome_produto[:30]}...")
            
            return True
            
        except Exception as e:
            print(Fore.RED + f"   ❌ Erro ao salvar aprendizado: {e}")
            return False
    
    def incrementar_economia(self) -> None:
        """
        Incrementa o contador de chamadas de IA economizadas.
        
        Chamado toda vez que um produto é encontrado no cache,
        evitando uma chamada à IA.
        """
        try:
            if "_aprendizado_ia" not in self.data:
                return
            
            self.data["_aprendizado_ia"]["_total_economizado"] = \
                self.data["_aprendizado_ia"].get("_total_economizado", 0) + 1
            
            # Salva no arquivo
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
                
        except Exception:
            pass  # Não é crítico
    
    def get_estatisticas_cache(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache de aprendizado.
        
        Útil para monitorar a eficiência do sistema de cache e
        calcular economia em chamadas de IA.
        
        Returns:
            dict: Estatísticas do cache:
                - total_produtos: Quantidade de produtos no cache
                - total_economizado: Chamadas de IA economizadas
                - produtos_monofasicos: Quantos são monofásicos
                - produtos_nao_monofasicos: Quantos não são
        
        Example:
            >>> stats = db.get_estatisticas_cache()
            >>> print(f"Produtos em cache: {stats['total_produtos']}")
            >>> print(f"Chamadas economizadas: {stats['total_economizado']}")
        """
        total = len(self.cache_ia)
        monofasicos = sum(1 for p in self.cache_ia.values() if p.get("is_monofasico"))
        
        economizado = self.data.get("_aprendizado_ia", {}).get("_total_economizado", 0)
        
        return {
            "total_produtos": total,
            "total_economizado": economizado,
            "produtos_monofasicos": monofasicos,
            "produtos_nao_monofasicos": total - monofasicos
        }
    
    # =========================================================================
    # MÉTODOS ORIGINAIS (mantidos da v2.0)
    # =========================================================================
    
    def is_monofasico(self, ncm: str) -> bool:
        """
        Verifica se um NCM é monofásico.
        
        Faz verificação em duas etapas:
        1. Busca exata na lista simples
        2. Busca pelo prefixo (ex: 2203 encontra 22030000)
        
        Args:
            ncm (str): Código NCM a verificar (com ou sem pontos)
        
        Returns:
            bool: True se o NCM é monofásico
        
        Example:
            >>> db.is_monofasico("22030000")
            True
            >>> db.is_monofasico("2203.00.00")
            True
            >>> db.is_monofasico("12345678")
            False
        """
        # Remove pontos e espaços
        ncm_limpo = ncm.replace(".", "").replace(" ", "").strip()
        
        # Busca exata
        if ncm_limpo in self.ncm_lista:
            return True
        
        # Busca por prefixo (4 primeiros dígitos)
        prefixo = ncm_limpo[:4]
        for ncm_cadastrado in self.ncm_lista:
            if ncm_cadastrado.startswith(prefixo):
                return True
        
        return False
    
    def get_descricao(self, ncm: str) -> str:
        """
        Retorna a descrição de um NCM.
        
        Args:
            ncm (str): Código NCM
        
        Returns:
            str: Descrição do NCM ou string vazia se não encontrado
        """
        ncm_limpo = ncm.replace(".", "").replace(" ", "").strip()
        
        # Busca direta
        if ncm_limpo in self.ncm_detalhes:
            return self.ncm_detalhes[ncm_limpo].get("descricao", "")
        
        # Busca por prefixo
        for ncm_key, info in self.ncm_detalhes.items():
            if info.get("ncm_base") == ncm_limpo:
                return info.get("descricao", "")
        
        return ""
    
    def get_base_legal(self) -> str:
        """
        Retorna a base legal para produtos monofásicos.
        
        Returns:
            str: Texto da base legal (Lei, Decreto, etc)
        """
        return self.metadata.get("base_legal", "Lei nº 13.097/2015")
    
    def identificar_por_nome(self, nome_produto: str) -> Optional[Dict[str, Any]]:
        """
        Tenta identificar um produto monofásico pelo nome/descrição.
        
        Esta função usa palavras-chave para identificar produtos que
        são monofásicos, mesmo quando o NCM está errado ou genérico.
        
        Args:
            nome_produto (str): Nome ou descrição do produto
        
        Returns:
            dict | None: Dicionário com informações ou None se não identificado
            
            Se encontrado, retorna:
            {
                "categoria": "cerveja",
                "ncm_sugerido": "22030000",
                "descricao": "Cervejas de malte (com álcool)",
                "confianca": "alta",  # alta, media, baixa
                "keyword_encontrada": "HEINEKEN",
                "base_legal": "Lei nº 13.097/2015..."
            }
        
        Example:
            >>> resultado = db.identificar_por_nome("HEINEKEN LONG NECK 355ML")
            >>> print(resultado)
            {
                'categoria': 'cerveja',
                'ncm_sugerido': '22030000',
                'descricao': 'Cervejas de malte',
                'confianca': 'alta',
                'keyword_encontrada': 'HEINEKEN'
            }
        """
        nome_upper = nome_produto.upper()
        
        # Mapeamento de categoria -> NCM sugerido
        categoria_ncm = {
            "cerveja": "22030000",
            "refrigerante": "22021000",
            "agua": "22011000",
            "energetico": "22029900",
            "isotonico": "22029900",
            "cha_pronto": "22029900",
            "suco_pronto": "22029900",
            "cerveja_sem_alcool": "22029100"
        }
        
        # Keywords que devem ser buscadas como palavra completa (evita falsos positivos)
        # Ex: "CHA" não deve bater em "CHANDON"
        keywords_palavra_completa = ["CHA", "CHÁ", "ALE", "ZERO"]
        
        # Busca em cada categoria
        for categoria, keywords_lista in self.keywords.items():
            # Ignora campos de comentário
            if categoria.startswith("_"):
                continue
            
            for keyword in keywords_lista:
                keyword_upper = keyword.upper()
                
                # Para keywords curtas/ambíguas, busca palavra completa
                if keyword_upper in keywords_palavra_completa:
                    # Adiciona espaços para garantir palavra completa
                    # " CHA " encontra "CHA GELADO" mas não "CHANDON"
                    nome_com_espacos = f" {nome_upper} "
                    keyword_com_espacos = f" {keyword_upper} "
                    
                    if keyword_com_espacos in nome_com_espacos:
                        ncm_sugerido = categoria_ncm.get(categoria, "")
                        if ncm_sugerido:
                            return {
                                "categoria": categoria,
                                "ncm_sugerido": ncm_sugerido,
                                "descricao": self.get_descricao(ncm_sugerido),
                                "confianca": self._calcular_confianca(keyword, nome_produto),
                                "keyword_encontrada": keyword,
                                "base_legal": self.get_base_legal()
                            }
                else:
                    # Busca normal (substring)
                    if keyword_upper in nome_upper:
                        ncm_sugerido = categoria_ncm.get(categoria, "")
                        
                        if ncm_sugerido:
                            return {
                                "categoria": categoria,
                                "ncm_sugerido": ncm_sugerido,
                                "descricao": self.get_descricao(ncm_sugerido),
                                "confianca": self._calcular_confianca(keyword, nome_produto),
                                "keyword_encontrada": keyword,
                                "base_legal": self.get_base_legal()
                            }
        
        return None
    
    def _calcular_confianca(self, keyword: str, nome_produto: str) -> str:
        """
        Calcula o nível de confiança da identificação.
        
        Args:
            keyword (str): Palavra-chave encontrada
            nome_produto (str): Nome completo do produto
        
        Returns:
            str: "alta", "media" ou "baixa"
        """
        # Keywords muito específicas = alta confiança
        keywords_alta = [
            "HEINEKEN", "BRAHMA", "SKOL", "ANTARCTICA", "BUDWEISER",
            "COCA-COLA", "COCA", "PEPSI", "FANTA", "SPRITE",
            "RED BULL", "MONSTER", "GATORADE", "POWERADE"
        ]
        
        # Keywords genéricas = média confiança
        keywords_media = [
            "CERVEJA", "REFRIGERANTE", "AGUA", "ÁGUA", "SUCO",
            "ENERGETICO", "ISOTONICO", "CHÁ"
        ]
        
        keyword_upper = keyword.upper()
        
        if keyword_upper in keywords_alta:
            return "alta"
        elif keyword_upper in keywords_media:
            return "media"
        else:
            return "baixa"
    
    def verificar_item(self, ncm: str, nome_produto: str) -> Dict[str, Any]:
        """
        Verificação completa de um item: NCM + Nome do produto.
        
        Combina verificação de NCM com identificação por nome para
        detectar erros de classificação.
        
        FLUXO DE VERIFICAÇÃO (v2.1):
        ----------------------------
        1. Verifica se NCM atual é monofásico (banco de dados)
        2. Tenta identificar pelo nome (keywords)
        3. Busca no cache de aprendizado da IA (NOVO!)
        4. Se não encontrou em nenhum, retorna não-monofásico
           (main.py vai consultar a IA e depois chamar salvar_aprendizado_ia)
        
        Args:
            ncm (str): NCM atual do produto
            nome_produto (str): Nome/descrição do produto
        
        Returns:
            dict: Resultado da verificação com campos:
                - is_monofasico (bool): Se o produto é monofásico
                - ncm_correto (str): NCM que deveria ser usado
                - ncm_atual_correto (bool): Se o NCM atual está correto
                - fonte (str): "banco_dados", "identificacao_nome" ou "cache_ia"
                - descricao (str): Descrição do NCM
                - base_legal (str): Base legal
                - confianca (str): Nível de confiança
        
        Example:
            >>> resultado = db.verificar_item("99999999", "HEINEKEN 355ML")
            >>> print(resultado)
            {
                'is_monofasico': True,
                'ncm_correto': '22030000',
                'ncm_atual_correto': False,
                'fonte': 'identificacao_nome',
                'descricao': 'Cervejas de malte',
                'confianca': 'alta'
            }
        """
        ncm_limpo = ncm.replace(".", "").replace(" ", "").strip()
        resultado = {
            "is_monofasico": False,
            "ncm_correto": ncm_limpo,
            "ncm_atual_correto": True,
            "fonte": "",
            "descricao": "",
            "base_legal": self.get_base_legal(),
            "confianca": "alta"
        }
        
        # ETAPA 1: Verifica se o NCM atual já é monofásico
        if self.is_monofasico(ncm_limpo):
            resultado["is_monofasico"] = True
            resultado["ncm_correto"] = ncm_limpo
            resultado["fonte"] = "banco_dados"
            resultado["descricao"] = self.get_descricao(ncm_limpo)
            return resultado
        
        # ETAPA 2: Se NCM não é monofásico, tenta identificar pelo nome
        identificacao = self.identificar_por_nome(nome_produto)
        
        if identificacao:
            resultado["is_monofasico"] = True
            resultado["ncm_correto"] = identificacao["ncm_sugerido"]
            resultado["ncm_atual_correto"] = False  # NCM atual está ERRADO
            resultado["fonte"] = "identificacao_nome"
            resultado["descricao"] = identificacao["descricao"]
            resultado["confianca"] = identificacao["confianca"]
            resultado["keyword_encontrada"] = identificacao["keyword_encontrada"]
            return resultado
        
        # ETAPA 3 (NOVO v2.1): Busca no cache de aprendizado da IA
        cache = self.buscar_cache_ia(nome_produto)
        
        if cache:
            # Incrementa contador de economia
            self.incrementar_economia()
            
            resultado["is_monofasico"] = cache["is_monofasico"]
            resultado["ncm_correto"] = cache["ncm_sugerido"]
            resultado["ncm_atual_correto"] = (ncm_limpo == cache["ncm_sugerido"])
            resultado["fonte"] = "cache_ia"
            resultado["descricao"] = cache.get("motivo", "")
            resultado["confianca"] = "alta"  # Cache é confiável (veio da IA)
            return resultado
        
        # Não encontrou em nenhum lugar
        # main.py vai consultar a IA e depois chamar salvar_aprendizado_ia()
        return resultado
    
    def get_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do banco de dados.
        
        Agora inclui estatísticas do cache de aprendizado (v2.1).
        
        Returns:
            dict: Estatísticas com total de NCMs, categorias, cache, etc.
        """
        total_keywords = sum(
            len(kw_list) 
            for cat, kw_list in self.keywords.items() 
            if not cat.startswith("_")
        )
        
        # Estatísticas do cache
        cache_stats = self.get_estatisticas_cache()
        
        return {
            "total_ncms": len(self.ncm_lista),
            "total_categorias": len([k for k in self.keywords.keys() if not k.startswith("_")]),
            "total_keywords": total_keywords,
            "base_legal": self.get_base_legal(),
            "atualizado_em": self.metadata.get("atualizado_em", "N/A"),
            # NOVO v2.1: Estatísticas do cache
            "cache_produtos": cache_stats["total_produtos"],
            "cache_economizado": cache_stats["total_economizado"]
        }


# =============================================================================
# EXEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    """
    Teste do módulo quando executado diretamente.
    """
    print("=" * 60)
    print("🗄️  TESTE DO BANCO DE DADOS DE NCMs v2.1")
    print("    (Com Sistema de Cache Inteligente)")
    print("=" * 60)
    
    # Tenta carregar o banco
    db = NCMDatabase("ncm_rules.json")
    
    # Mostra estatísticas
    stats = db.get_estatisticas()
    print(f"\n📊 Estatísticas:")
    print(f"   NCMs cadastrados: {stats['total_ncms']}")
    print(f"   Categorias: {stats['total_categorias']}")
    print(f"   Keywords: {stats['total_keywords']}")
    print(f"   Produtos em cache: {stats['cache_produtos']}")
    print(f"   Chamadas IA economizadas: {stats['cache_economizado']}")
    
    # Testes de verificação
    print(f"\n🧪 Testes de verificação:")
    
    testes = [
        ("22030000", "CERVEJA QUALQUER"),
        ("99999999", "HEINEKEN LONG NECK 355ML"),
        ("99999999", "COCA-COLA 2L"),
        ("99999999", "ARROZ TIPO 1 5KG"),
        ("22021000", "REFRIGERANTE FANTA"),
    ]
    
    for ncm, nome in testes:
        resultado = db.verificar_item(ncm, nome)
        status = "✅" if resultado["is_monofasico"] else "❌"
        correto = "✅" if resultado["ncm_atual_correto"] else "⚠️ ERRO"
        
        print(f"\n   {nome}")
        print(f"   NCM: {ncm} → {correto}")
        print(f"   Monofásico: {status}")
        print(f"   Fonte: {resultado['fonte']}")
        if not resultado["ncm_atual_correto"]:
            print(f"   NCM correto: {resultado['ncm_correto']}")
