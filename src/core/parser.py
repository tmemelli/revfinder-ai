"""
================================================================================
MÓDULO: parser.py - Extrator de Dados de NF-e (Nota Fiscal Eletrônica)
================================================================================

Este módulo é responsável por ler e extrair dados estruturados de arquivos
XML de Notas Fiscais Eletrônicas (NF-e) no padrão brasileiro.

CONTEXTO TÉCNICO:
-----------------
A Nota Fiscal Eletrônica (NF-e) é um documento digital brasileiro que substitui
a nota fiscal em papel. O arquivo XML segue um padrão definido pela SEFAZ
(Secretaria da Fazenda) e contém:

    - Dados do emitente (quem vendeu)
    - Dados do destinatário (quem comprou)
    - Itens da nota (produtos/serviços)
    - Impostos calculados (ICMS, PIS, COFINS, IPI, etc.)
    - Informações de transporte
    - Assinatura digital

ESTRUTURA DO XML DE NF-e:
-------------------------
O XML usa namespace específico e tem estrutura hierárquica:

    <nfeProc>
        <NFe>
            <infNFe Id="NFe...">
                <ide>...</ide>           # Identificação da NF-e
                <emit>...</emit>         # Dados do emitente
                <dest>...</dest>         # Dados do destinatário
                <det nItem="1">          # Primeiro item
                    <prod>               # Dados do produto
                        <xProd>Nome</xProd>
                        <NCM>12345678</NCM>
                        <vProd>100.00</vProd>
                    </prod>
                    <imposto>            # Impostos do item
                        <PIS>...</PIS>
                        <COFINS>...</COFINS>
                    </imposto>
                </det>
                <det nItem="2">...</det> # Segundo item
            </infNFe>
        </NFe>
    </nfeProc>

CAMPOS EXTRAÍDOS (v2.1):
------------------------
Para cada item da nota, extraímos:

    DADOS DA NOTA (novos na v2.1):
    - chave_acesso: Chave de 44 dígitos que identifica a nota
    - numero_nota: Número da nota fiscal
    - serie_nota: Série da nota
    - data_emissao: Data e hora de emissão
    - cnpj_emitente: CNPJ de quem emitiu (formatado)
    - nome_emitente: Nome/Razão social do emitente

    DADOS DO ITEM:
    - numero_item: Sequencial do item na nota
    - produto: Nome/descrição do produto
    - ncm: Código NCM (Nomenclatura Comum do Mercosul)
    - valor_total: Valor total do item (quantidade × preço)
    - pis_pago: Valor de PIS recolhido
    - cofins_pago: Valor de COFINS recolhido
    - imposto_total: Soma de PIS + COFINS

DEPENDÊNCIAS:
-------------
    - xml.etree.ElementTree: Biblioteca padrão Python para parsing XML

USO:
----
    from core.parser import NFeParser
    
    parser = NFeParser()
    itens = parser.parse("nota_fiscal.xml")
    
    for item in itens:
        print(f"{item['produto']}: R$ {item['valor_total']}")
        print(f"Nota: {item['numero_nota']} - {item['data_emissao']}")

Autor: Grande Mestre
Versão: 2.1
Data: Dezembro/2025
================================================================================
"""

# =============================================================================
# IMPORTS
# =============================================================================

import xml.etree.ElementTree as ET  # Parser XML da biblioteca padrão Python
from typing import List, Dict, Any, Optional  # Type hints para documentação


# =============================================================================
# CONSTANTES
# =============================================================================

# Namespace padrão usado nos XMLs de NF-e
# Todos os elementos do XML usam este namespace como prefixo
# Sem isso, o ElementTree não consegue encontrar os elementos
NFE_NAMESPACE = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class NFeParser:
    """
    Parser de arquivos XML de Nota Fiscal Eletrônica (NF-e).
    
    Esta classe encapsula toda a lógica de extração de dados de XMLs de NF-e,
    fornecendo uma interface simples para obter os itens da nota com seus
    respectivos impostos.
    
    O parser lida automaticamente com:
        - Namespace XML do portal fiscal
        - Campos opcionais (não quebra se faltar algo)
        - Conversão de tipos (string → float)
        - Cálculo de totais de impostos
        - Extração de dados da nota (chave, número, emitente) [v2.1]
    
    Attributes:
        ns (dict): Dicionário de namespaces para queries XPath.
    
    Example:
        >>> parser = NFeParser()
        >>> itens = parser.parse("nota_fiscal.xml")
        >>> 
        >>> # Listar todos os produtos
        >>> for item in itens:
        ...     print(f"{item['produto']}: NCM {item['ncm']}")
        ...
        CERVEJA HEINEKEN 355ML: NCM 22030000
        REFRIGERANTE COCA-COLA 2L: NCM 22021000
        
        >>> # Calcular total de impostos pagos
        >>> total_impostos = sum(item['imposto_total'] for item in itens)
        >>> print(f"Total PIS/COFINS: R$ {total_impostos:.2f}")
        Total PIS/COFINS: R$ 25.50
        
        >>> # Acessar dados da nota (v2.1)
        >>> print(f"Nota: {itens[0]['numero_nota']}")
        >>> print(f"Emitente: {itens[0]['nome_emitente']}")
    
    Note:
        O parser foi desenvolvido para XMLs no padrão NF-e 4.0.
        Versões anteriores podem ter estrutura ligeiramente diferente.
    """
    
    def __init__(self):
        """
        Inicializa o parser com o namespace padrão de NF-e.
        
        O namespace é necessário porque o XML de NF-e usa qualified names.
        Sem ele, queries XPath como ".//det" não encontram os elementos.
        
        Example:
            >>> parser = NFeParser()
            >>> print(parser.ns)
            {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        """
        # Namespace do portal fiscal - obrigatório para queries XPath
        self.ns = NFE_NAMESPACE
    
    def _safe_find_text(
        self, 
        element: ET.Element, 
        path: str, 
        default: str = ""
    ) -> str:
        """
        Busca texto de um elemento XML de forma segura (sem exceções).
        
        Esta é uma função auxiliar que evita o problema comum de
        NoneType quando um elemento opcional não existe no XML.
        
        Args:
            element (ET.Element): Elemento pai onde buscar.
            path (str): Caminho XPath do elemento filho (com prefixo 'nfe:').
            default (str): Valor retornado se elemento não existir.
        
        Returns:
            str: Texto do elemento ou valor default.
        
        Example:
            >>> # Se o elemento existe
            >>> texto = self._safe_find_text(prod, "nfe:xProd", "SEM NOME")
            >>> print(texto)
            'CERVEJA HEINEKEN 355ML'
            
            >>> # Se o elemento não existe
            >>> texto = self._safe_find_text(prod, "nfe:xCampoInexistente", "N/A")
            >>> print(texto)
            'N/A'
        """
        found = element.find(path, self.ns)
        if found is not None and found.text:
            return found.text
        return default
    
    def _safe_find_float(
        self, 
        element: ET.Element, 
        path: str, 
        default: float = 0.0
    ) -> float:
        """
        Busca valor numérico de um elemento XML de forma segura.
        
        Além de tratar elementos inexistentes, também trata erros
        de conversão de string para float.
        
        Args:
            element (ET.Element): Elemento pai onde buscar.
            path (str): Caminho XPath do elemento filho.
            default (float): Valor retornado se elemento não existir ou inválido.
        
        Returns:
            float: Valor numérico do elemento ou valor default.
        
        Example:
            >>> valor = self._safe_find_float(prod, "nfe:vProd", 0.0)
            >>> print(valor)
            15.99
        """
        found = element.find(path, self.ns)
        if found is not None and found.text:
            try:
                return float(found.text)
            except ValueError:
                return default
        return default
    
    def _format_cnpj(self, cnpj: str) -> str:
        """
        Formata CNPJ de 14 dígitos para formato padrão brasileiro.
        
        Args:
            cnpj (str): CNPJ sem formatação (14 dígitos)
        
        Returns:
            str: CNPJ formatado (XX.XXX.XXX/XXXX-XX) ou original se inválido
        
        Example:
            >>> self._format_cnpj("12345678000199")
            '12.345.678/0001-99'
        """
        if len(cnpj) == 14 and cnpj.isdigit():
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return cnpj
    
    def _extract_dados_nota(self, root: ET.Element) -> Dict[str, str]:
        """
        Extrai dados gerais da nota fiscal (cabeçalho).
        
        Esta função busca informações que identificam a nota como um todo,
        não os itens individuais. Esses dados são importantes para:
            - Identificar a nota na Receita Federal (chave de acesso)
            - Saber quem emitiu (CNPJ/nome)
            - Rastrear quando foi emitida (data)
        
        Args:
            root (ET.Element): Elemento raiz do XML parseado.
        
        Returns:
            Dict[str, str]: Dicionário com dados da nota:
                - chave_acesso: 44 dígitos que identificam a nota
                - numero_nota: Número da NF-e
                - serie_nota: Série da NF-e
                - data_emissao: Data/hora formatada
                - cnpj_emitente: CNPJ formatado
                - nome_emitente: Razão social
        
        Example:
            >>> dados = self._extract_dados_nota(root)
            >>> print(dados['chave_acesso'])
            '32251228129260000423652020001192491613641729'
            >>> print(dados['nome_emitente'])
            'DRIFT COM DE ALIMENTOS SA'
        """
        dados = {
            'chave_acesso': '',
            'numero_nota': '',
            'serie_nota': '',
            'data_emissao': '',
            'cnpj_emitente': '',
            'nome_emitente': ''
        }
        
        # -----------------------------------------------------------------
        # Extrai chave de acesso do atributo Id do elemento infNFe
        # Formato: "NFe" + 44 dígitos
        # -----------------------------------------------------------------
        inf_nfe = root.find(".//nfe:infNFe", self.ns)
        if inf_nfe is not None:
            nfe_id = inf_nfe.get("Id", "")
            # Remove o prefixo "NFe" se existir
            if nfe_id.startswith("NFe"):
                dados['chave_acesso'] = nfe_id[3:]
            else:
                dados['chave_acesso'] = nfe_id
        
        # -----------------------------------------------------------------
        # Extrai dados de identificação da nota (ide)
        # -----------------------------------------------------------------
        ide = root.find(".//nfe:ide", self.ns)
        if ide is not None:
            dados['numero_nota'] = self._safe_find_text(ide, "nfe:nNF", "")
            dados['serie_nota'] = self._safe_find_text(ide, "nfe:serie", "")
            
            # Data de emissão - formato ISO: 2025-12-29T18:03:19-03:00
            data_str = self._safe_find_text(ide, "nfe:dhEmi", "")
            if data_str:
                # Converte para formato legível: 2025-12-29 18:03:19
                try:
                    dados['data_emissao'] = data_str[:19].replace("T", " ")
                except:
                    dados['data_emissao'] = data_str
        
        # -----------------------------------------------------------------
        # Extrai dados do emitente (emit)
        # -----------------------------------------------------------------
        emit = root.find(".//nfe:emit", self.ns)
        if emit is not None:
            cnpj_raw = self._safe_find_text(emit, "nfe:CNPJ", "")
            dados['cnpj_emitente'] = self._format_cnpj(cnpj_raw)
            dados['nome_emitente'] = self._safe_find_text(emit, "nfe:xNome", "")
        
        return dados
    
    def _extract_pis(self, imposto: ET.Element) -> float:
        """
        Extrai o valor de PIS pago de um elemento <imposto>.
        
        O PIS pode estar em diferentes subelementos dependendo do CST:
            - PISAliq: PIS com alíquota (CST 01, 02)
            - PISNT: PIS não tributado (CST 04, 05, 06)
            - PISOutr: Outras situações (CST 49, 50, etc)
        
        Args:
            imposto (ET.Element): Elemento <imposto> do item.
        
        Returns:
            float: Valor de PIS pago ou 0.0 se não tributado.
        
        Example:
            >>> pis = self._extract_pis(imposto_element)
            >>> print(f"PIS: R$ {pis:.2f}")
            PIS: R$ 0.15
        """
        # Tenta PISAliq (tributado com alíquota)
        vPIS = imposto.find("nfe:PIS/nfe:PISAliq/nfe:vPIS", self.ns)
        if vPIS is not None and vPIS.text:
            try:
                return float(vPIS.text)
            except ValueError:
                pass
        
        # Tenta PISOutr (outras situações)
        vPIS = imposto.find("nfe:PIS/nfe:PISOutr/nfe:vPIS", self.ns)
        if vPIS is not None and vPIS.text:
            try:
                return float(vPIS.text)
            except ValueError:
                pass
        
        # PISNT = não tributado = 0
        pisnt = imposto.find("nfe:PIS/nfe:PISNT", self.ns)
        if pisnt is not None:
            return 0.0
        
        return 0.0
    
    def _extract_cofins(self, imposto: ET.Element) -> float:
        """
        Extrai o valor de COFINS pago de um elemento <imposto>.
        
        Similar ao PIS, COFINS pode estar em diferentes subelementos:
            - COFINSAliq: COFINS com alíquota
            - COFINSNT: COFINS não tributado
            - COFINSOutr: Outras situações
        
        Args:
            imposto (ET.Element): Elemento <imposto> do item.
        
        Returns:
            float: Valor de COFINS pago ou 0.0 se não tributado.
        
        Example:
            >>> cofins = self._extract_cofins(imposto_element)
            >>> print(f"COFINS: R$ {cofins:.2f}")
            COFINS: R$ 0.70
        """
        # Tenta COFINSAliq (tributado com alíquota)
        vCOFINS = imposto.find("nfe:COFINS/nfe:COFINSAliq/nfe:vCOFINS", self.ns)
        if vCOFINS is not None and vCOFINS.text:
            try:
                return float(vCOFINS.text)
            except ValueError:
                pass
        
        # Tenta COFINSOutr (outras situações)
        vCOFINS = imposto.find("nfe:COFINS/nfe:COFINSOutr/nfe:vCOFINS", self.ns)
        if vCOFINS is not None and vCOFINS.text:
            try:
                return float(vCOFINS.text)
            except ValueError:
                pass
        
        # COFINSNT = não tributado = 0
        cofinsnt = imposto.find("nfe:COFINS/nfe:COFINSNT", self.ns)
        if cofinsnt is not None:
            return 0.0
        
        return 0.0
    
    def _extract_item(
        self, 
        det_element: ET.Element, 
        dados_nota: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai todos os dados de um item (<det>) da nota fiscal.
        
        Esta função processa um elemento <det> (detalhe) completo,
        extraindo dados do produto e seus impostos.
        
        Na versão 2.1, também inclui os dados da nota para que cada
        item possa ser rastreado até sua nota de origem.
        
        Args:
            det_element (ET.Element): Elemento <det> do XML.
            dados_nota (Dict[str, str]): Dados da nota (chave, número, etc).
        
        Returns:
            Dict[str, Any] | None: Dicionário com dados do item ou None se erro.
            
            Estrutura do dicionário retornado:
            {
                # Dados da nota (v2.1)
                'chave_acesso': str,     # Chave de 44 dígitos
                'numero_nota': str,      # Número da nota
                'serie_nota': str,       # Série
                'data_emissao': str,     # Data/hora emissão
                'cnpj_emitente': str,    # CNPJ formatado
                'nome_emitente': str,    # Razão social
                
                # Dados do item
                'numero_item': str,      # Sequencial do item (1, 2, 3...)
                'produto': str,          # Nome/descrição do produto
                'ncm': str,              # Código NCM (8 dígitos)
                'valor_total': float,    # Valor total do item em R$
                'pis_pago': float,       # Valor PIS pago em R$
                'cofins_pago': float,    # Valor COFINS pago em R$
                'imposto_total': float   # Soma PIS + COFINS em R$
            }
        
        Example:
            >>> item = self._extract_item(det_element, dados_nota)
            >>> print(item)
            {
                'chave_acesso': '3225122812926...',
                'numero_nota': '119249',
                'nome_emitente': 'DRIFT COM DE ALIMENTOS SA',
                'produto': 'CERVEJA HEINEKEN 355ML',
                'ncm': '22030000',
                'imposto_total': 0.85
            }
        """
        try:
            # Localiza subelementos principais
            prod = det_element.find("nfe:prod", self.ns)
            imposto = det_element.find("nfe:imposto", self.ns)
            
            # Se não tem produto, não tem o que extrair
            if prod is None:
                return None
            
            # -----------------------------------------------------------------
            # Extrai dados do produto + dados da nota
            # -----------------------------------------------------------------
            item = {
                # Dados da nota (v2.1)
                'chave_acesso': dados_nota.get('chave_acesso', ''),
                'numero_nota': dados_nota.get('numero_nota', ''),
                'serie_nota': dados_nota.get('serie_nota', ''),
                'data_emissao': dados_nota.get('data_emissao', ''),
                'cnpj_emitente': dados_nota.get('cnpj_emitente', ''),
                'nome_emitente': dados_nota.get('nome_emitente', ''),
                
                # Dados do item
                'numero_item': det_element.get("nItem", "0"),
                'produto': self._safe_find_text(prod, "nfe:xProd", "PRODUTO SEM NOME"),
                'ncm': self._safe_find_text(prod, "nfe:NCM", "00000000"),
                'valor_total': self._safe_find_float(prod, "nfe:vProd", 0.0),
                'pis_pago': 0.0,
                'cofins_pago': 0.0,
                'imposto_total': 0.0
            }
            
            # -----------------------------------------------------------------
            # Extrai dados de impostos (se existirem)
            # -----------------------------------------------------------------
            if imposto is not None:
                item['pis_pago'] = self._extract_pis(imposto)
                item['cofins_pago'] = self._extract_cofins(imposto)
                item['imposto_total'] = item['pis_pago'] + item['cofins_pago']
            
            return item
            
        except Exception as e:
            # Log do erro mas não interrompe o processamento
            print(f"   ⚠️  Erro ao extrair item: {e}")
            return None
    
    def parse(self, xml_path: str) -> List[Dict[str, Any]]:
        """
        Lê um arquivo XML de NF-e e retorna lista de itens estruturados.
        
        Esta é a função principal do parser. Ela:
        1. Abre e parseia o arquivo XML
        2. Extrai dados da nota (chave, número, emitente) [v2.1]
        3. Itera sobre todos os itens (<det>)
        4. Extrai dados de cada item
        5. Retorna lista consolidada
        
        Args:
            xml_path (str): Caminho completo para o arquivo XML da NF-e.
        
        Returns:
            List[Dict[str, Any]]: Lista de dicionários, um por item da nota.
            Retorna lista vazia se houver erro ou arquivo inválido.
        
        Raises:
            Não levanta exceções - erros são tratados internamente.
        
        Example:
            >>> parser = NFeParser()
            >>> itens = parser.parse("/path/to/nota_fiscal.xml")
            >>> 
            >>> print(f"Total de itens: {len(itens)}")
            Total de itens: 15
            >>> 
            >>> # Filtrar itens com imposto pago
            >>> com_imposto = [i for i in itens if i['imposto_total'] > 0]
            >>> print(f"Itens com PIS/COFINS: {len(com_imposto)}")
            Itens com PIS/COFINS: 12
            >>> 
            >>> # Calcular total de impostos
            >>> total = sum(i['imposto_total'] for i in itens)
            >>> print(f"Total PIS/COFINS: R$ {total:.2f}")
            Total PIS/COFINS: R$ 45.30
            >>> 
            >>> # Acessar dados da nota (v2.1)
            >>> print(f"Nota: {itens[0]['numero_nota']}")
            >>> print(f"Emitente: {itens[0]['nome_emitente']}")
        
        Note:
            - O arquivo deve ser um XML válido no padrão NF-e
            - Arquivos corrompidos ou em outro formato retornam []
            - Encoding esperado: UTF-8 (padrão NF-e)
        """
        try:
            # =================================================================
            # ETAPA 1: Parsing do arquivo XML
            # =================================================================
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # =================================================================
            # ETAPA 2: Extração dos dados da nota (v2.1)
            # =================================================================
            dados_nota = self._extract_dados_nota(root)
            
            # =================================================================
            # ETAPA 3: Extração dos itens
            # =================================================================
            itens = []
            
            # Busca todos os elementos <det> (detalhe/item)
            # Cada <det> representa um produto na nota
            for det in root.findall(".//nfe:det", self.ns):
                
                # Extrai dados do item (agora inclui dados da nota)
                item = self._extract_item(det, dados_nota)
                
                # Adiciona à lista se extração foi bem sucedida
                if item is not None:
                    itens.append(item)
            
            return itens
            
        except ET.ParseError as e:
            # Erro de parsing XML (arquivo malformado)
            print(f"   ❌ Erro de parsing XML em {xml_path}: {e}")
            return []
            
        except FileNotFoundError:
            # Arquivo não existe
            print(f"   ❌ Arquivo não encontrado: {xml_path}")
            return []
            
        except Exception as e:
            # Qualquer outro erro inesperado
            print(f"   ❌ Erro inesperado ao processar {xml_path}: {e}")
            return []


# =============================================================================
# EXEMPLO DE USO (para testes)
# =============================================================================

if __name__ == "__main__":
    """
    Exemplo de uso do parser quando executado diretamente.
    
    Uso:
        $ python parser.py caminho/para/nota.xml
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python parser.py <arquivo.xml>")
        print("\nExemplo:")
        print("  python parser.py nota_fiscal.xml")
        sys.exit(1)
    
    # Testa o parser com o arquivo fornecido
    parser = NFeParser()
    itens = parser.parse(sys.argv[1])
    
    # Mostra dados da nota (v2.1)
    if itens:
        print(f"\n📋 DADOS DA NOTA:")
        print(f"   Chave: {itens[0]['chave_acesso']}")
        print(f"   Número: {itens[0]['numero_nota']} | Série: {itens[0]['serie_nota']}")
        print(f"   Data: {itens[0]['data_emissao']}")
        print(f"   Emitente: {itens[0]['nome_emitente']}")
        print(f"   CNPJ: {itens[0]['cnpj_emitente']}")
    
    print(f"\n📦 Total de itens encontrados: {len(itens)}\n")
    
    for item in itens:
        print(f"  Item {item['numero_item']}: {item['produto']}")
        print(f"    NCM: {item['ncm']}")
        print(f"    Valor: R$ {item['valor_total']:.2f}")
        print(f"    PIS/COFINS: R$ {item['imposto_total']:.2f}")
        print()
