"""
================================================================================
MÓDULO: exporter.py - Gerador de Relatórios de Recuperação Tributária
================================================================================

Este módulo é responsável por gerar relatórios profissionais em formato Excel
(.xlsx) contendo os resultados da auditoria tributária.

CONTEXTO DE NEGÓCIO:
--------------------
Após a análise das notas fiscais, o sistema identifica produtos que tiveram
PIS/COFINS pagos indevidamente (tributação monofásica não aplicada).

O relatório gerado serve para:
    1. Documentar os erros encontrados
    2. Embasar o pedido de restituição junto à Receita Federal
    3. Apresentar ao cliente o valor que pode ser recuperado
    4. Servir como prova em processos administrativos

ESTRUTURA DO RELATÓRIO:
-----------------------
O Excel gerado contém as seguintes colunas:

    | Produto | NCM Sistema | NCM Correto | Valor a Recuperar | Motivo | Auditoria |
    |---------|-------------|-------------|-------------------|--------|-----------|
    | HEINEKEN| 99999999    | 22030000    | R$ 1.50           | Cerveja| IA        |
    | COCA 2L | 99999999    | 22021000    | R$ 0.95           | Refri  | DB        |

NOMENCLATURA DOS ARQUIVOS:
--------------------------
Os arquivos são nomeados com timestamp para evitar sobrescrita:

    Relatorio_Recuperacao_20251229_143052.xlsx
                         │       │
                         │       └── Hora (HHMMSS)
                         └────────── Data (YYYYMMDD)

DEPENDÊNCIAS:
-------------
    - pandas: Manipulação de dados e exportação para Excel
    - openpyxl: Engine para escrita de arquivos .xlsx (instalado com pandas)

USO:
----
    from utils.exporter import ReportGenerator
    
    # Inicializa o gerador
    exporter = ReportGenerator(output_folder="meus_relatorios")
    
    # Lista de erros encontrados
    erros = [
        {
            "produto": "CERVEJA HEINEKEN 355ML",
            "ncm": "99999999",
            "ncm_correto": "22030000",
            "imposto_recuperavel": 1.50,
            "motivo": "Cerveja identificada",
            "origem_analise": "Agente AI"
        }
    ]
    
    # Gera o relatório
    exporter.gerar_excel(erros)

Autor: Grande Mestre
Versão: 2.0
Data: Dezembro/2025
================================================================================
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os  # Manipulação de caminhos e diretórios
from datetime import datetime  # Geração de timestamps
from typing import List, Dict, Any, Optional  # Type hints

# Pandas para manipulação de dados tabulares e exportação Excel
import pandas as pd

# Colorama para output colorido no terminal
from colorama import Fore


# =============================================================================
# CONSTANTES
# =============================================================================

# Diretório padrão para salvar os relatórios
DEFAULT_OUTPUT_FOLDER = "output_reports"

# Mapeamento de colunas internas para nomes amigáveis no Excel
# Chave: nome interno | Valor: nome exibido no Excel
COLUMN_MAPPING = {
    # Dados da nota (v2.1)
    "chave_acesso": "Chave de Acesso",
    "numero_nota": "Nº Nota",
    "data_emissao": "Data Emissão",
    "cnpj_emitente": "CNPJ Emitente",
    "nome_emitente": "Emitente",
    # Dados do item
    "produto": "Produto",
    "ncm": "NCM Sistema",
    "ncm_correto": "NCM Correto",
    "imposto_recuperavel": "Valor a Recuperar (R$)",
    "motivo": "Motivo",
    "origem_analise": "Auditoria Feita Por"
}

# Ordem das colunas no relatório final
COLUMN_ORDER = [
    # Dados da nota primeiro (v2.1)
    "chave_acesso",
    "numero_nota",
    "data_emissao",
    "cnpj_emitente",
    "nome_emitente",
    # Dados do item
    "produto",
    "ncm",
    "ncm_correto",
    "imposto_recuperavel",
    "motivo",
    "origem_analise"
]


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class ReportGenerator:
    """
    Gerador de relatórios Excel para recuperação tributária.
    
    Esta classe encapsula toda a lógica de geração de relatórios,
    incluindo criação de diretórios, formatação de dados e
    exportação para formato Excel.
    
    O relatório gerado é profissional e pode ser usado diretamente
    em processos de restituição junto à Receita Federal.
    
    Attributes:
        output_folder (str): Caminho do diretório onde os relatórios são salvos.
    
    Example:
        >>> # Uso básico
        >>> exporter = ReportGenerator()
        >>> exporter.gerar_excel(lista_de_erros)
        
        >>> # Com diretório personalizado
        >>> exporter = ReportGenerator(output_folder="relatorios/2025")
        >>> exporter.gerar_excel(lista_de_erros)
    
    Note:
        - O diretório de output é criado automaticamente se não existir
        - Arquivos existentes NÃO são sobrescritos (usa timestamp único)
        - Formato do arquivo: .xlsx (Excel 2007+)
    """
    
    def __init__(self, output_folder: str = DEFAULT_OUTPUT_FOLDER):
        """
        Inicializa o gerador de relatórios.
        
        Cria o diretório de output se não existir.
        
        Args:
            output_folder (str): Caminho para o diretório onde os relatórios
                               serão salvos. Default: "output_reports"
        
        Example:
            >>> # Diretório padrão
            >>> exporter = ReportGenerator()
            >>> print(exporter.output_folder)
            'output_reports'
            
            >>> # Diretório personalizado
            >>> exporter = ReportGenerator("meus_relatorios/fiscal")
            >>> print(exporter.output_folder)
            'meus_relatorios/fiscal'
        
        Note:
            O diretório é criado recursivamente, então
            "pasta1/pasta2/pasta3" funciona mesmo se nenhuma existir.
        """
        self.output_folder = output_folder
        
        # Cria o diretório se não existir
        # exist_ok=True evita erro se já existir
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)
            print(Fore.BLUE + f"📁 Diretório criado: {output_folder}")
    
    def _generate_filename(self) -> str:
        """
        Gera um nome de arquivo único baseado em timestamp.
        
        O formato garante que arquivos não sejam sobrescritos e
        que a ordenação alfabética corresponda à ordem cronológica.
        
        Returns:
            str: Nome do arquivo no formato "Relatorio_Recuperacao_YYYYMMDD_HHMMSS.xlsx"
        
        Example:
            >>> filename = self._generate_filename()
            >>> print(filename)
            'Relatorio_Recuperacao_20251229_143052.xlsx'
        
        Note:
            O timestamp usa horário local do sistema.
        """
        # Formato: YYYYMMDD_HHMMSS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"Relatorio_Recuperacao_{timestamp}.xlsx"
    
    def _prepare_dataframe(self, lista_auditoria: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Prepara o DataFrame para exportação.
        
        Esta função:
        1. Converte a lista de dicionários em DataFrame
        2. Garante que todas as colunas esperadas existam
        3. Reordena as colunas na ordem correta
        4. Renomeia colunas para nomes amigáveis
        
        Args:
            lista_auditoria (List[Dict]): Lista de erros encontrados.
                Cada dicionário deve conter as chaves definidas em COLUMN_ORDER.
        
        Returns:
            pd.DataFrame: DataFrame formatado e pronto para exportação.
        
        Example:
            >>> erros = [
            ...     {"produto": "HEINEKEN", "ncm": "99999999", ...}
            ... ]
            >>> df = self._prepare_dataframe(erros)
            >>> print(df.columns.tolist())
            ['Produto', 'NCM Sistema', 'NCM Correto', 'Valor a Recuperar (R$)', ...]
        """
        # Converte lista para DataFrame
        df = pd.DataFrame(lista_auditoria)
        
        # Garante que todas as colunas existam (adiciona vazias se faltar)
        for col in COLUMN_ORDER:
            if col not in df.columns:
                df[col] = ""
        
        # Seleciona e reordena colunas
        df_ordered = df[COLUMN_ORDER].copy()
        
        # Renomeia colunas para nomes amigáveis
        column_names = [COLUMN_MAPPING.get(col, col) for col in COLUMN_ORDER]
        df_ordered.columns = column_names
        
        return df_ordered
    
    def _format_currency(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Formata valores monetários no DataFrame.
        
        Converte a coluna de valores para formato brasileiro (R$).
        
        Args:
            df (pd.DataFrame): DataFrame com dados brutos.
        
        Returns:
            pd.DataFrame: DataFrame com valores formatados.
        
        Note:
            Esta função é opcional e pode ser expandida para
            adicionar mais formatações.
        """
        # Por enquanto, mantemos os valores numéricos para
        # permitir soma no Excel. A formatação é feita pelo Excel.
        return df
    
    def gerar_excel(self, lista_auditoria: List[Dict[str, Any]]) -> Optional[str]:
        """
        Gera o relatório Excel com os erros encontrados.
        
        Esta é a função principal do módulo. Ela:
        1. Valida se há dados para exportar
        2. Prepara o DataFrame
        3. Gera nome de arquivo único
        4. Exporta para Excel
        5. Exibe mensagem de sucesso
        
        Args:
            lista_auditoria (List[Dict]): Lista de erros encontrados na auditoria.
                Cada item deve ser um dicionário com as chaves:
                - produto (str): Nome do produto
                - ncm (str): NCM original (errado)
                - ncm_correto (str): NCM que deveria ser
                - imposto_recuperavel (float): Valor em R$
                - motivo (str): Explicação do erro
                - origem_analise (str): "Banco de Dados" ou "Agente AI"
        
        Returns:
            Optional[str]: Caminho completo do arquivo gerado ou None se vazio.
        
        Example:
            >>> exporter = ReportGenerator()
            >>> 
            >>> erros = [
            ...     {
            ...         "produto": "CERVEJA HEINEKEN 355ML",
            ...         "ncm": "99999999",
            ...         "ncm_correto": "22030000",
            ...         "imposto_recuperavel": 1.50,
            ...         "motivo": "Cerveja identificada",
            ...         "origem_analise": "Agente AI"
            ...     },
            ...     {
            ...         "produto": "COCA-COLA 2L",
            ...         "ncm": "99999999",
            ...         "ncm_correto": "22021000",
            ...         "imposto_recuperavel": 0.95,
            ...         "motivo": "Refrigerante identificado",
            ...         "origem_analise": "Banco de Dados"
            ...     }
            ... ]
            >>> 
            >>> filepath = exporter.gerar_excel(erros)
            📊 Relatório Excel gerado com sucesso: output_reports/Relatorio_...
            >>> 
            >>> print(filepath)
            'output_reports/Relatorio_Recuperacao_20251229_143052.xlsx'
        
        Note:
            - Se lista_auditoria estiver vazia, não gera arquivo
            - O arquivo usa engine 'openpyxl' para compatibilidade
            - Valores numéricos são mantidos para permitir fórmulas no Excel
        """
        # =====================================================================
        # VALIDAÇÃO: Verifica se há dados para exportar
        # =====================================================================
        if not lista_auditoria:
            print(Fore.YELLOW + "⚠️  Nenhum erro para exportar. Relatório não gerado.")
            return None
        
        # =====================================================================
        # PREPARAÇÃO: Converte e formata os dados
        # =====================================================================
        df = self._prepare_dataframe(lista_auditoria)
        df = self._format_currency(df)
        
        # =====================================================================
        # GERAÇÃO: Cria nome de arquivo e caminho completo
        # =====================================================================
        filename = self._generate_filename()
        filepath = os.path.join(self.output_folder, filename)
        
        # =====================================================================
        # EXPORTAÇÃO: Salva o arquivo Excel
        # =====================================================================
        try:
            # to_excel com index=False remove a coluna de índice do pandas
            # engine='openpyxl' é necessário para .xlsx
            df.to_excel(
                filepath,
                index=False,
                engine='openpyxl'
            )
            
            print(Fore.GREEN + f"\n📊 Relatório Excel gerado com sucesso!")
            print(Fore.WHITE + f"   📁 Arquivo: {filepath}")
            print(Fore.WHITE + f"   📋 Registros: {len(lista_auditoria)} itens")
            
            # Calcula e exibe o total
            total = sum(item.get('imposto_recuperavel', 0) for item in lista_auditoria)
            print(Fore.WHITE + f"   💰 Total: R$ {total:.2f}")
            
            return filepath
            
        except PermissionError:
            print(Fore.RED + f"❌ Erro: Arquivo {filepath} está aberto em outro programa.")
            print(Fore.YELLOW + "   Feche o Excel e tente novamente.")
            return None
            
        except Exception as e:
            print(Fore.RED + f"❌ Erro ao salvar Excel: {e}")
            return None
    
    def gerar_csv(self, lista_auditoria: List[Dict[str, Any]]) -> Optional[str]:
        """
        Gera o relatório em formato CSV (alternativa ao Excel).
        
        Útil para sistemas que não suportam Excel ou para
        importação em outros softwares.
        
        Args:
            lista_auditoria (List[Dict]): Lista de erros encontrados.
        
        Returns:
            Optional[str]: Caminho do arquivo ou None se erro.
        
        Example:
            >>> filepath = exporter.gerar_csv(erros)
            >>> print(filepath)
            'output_reports/Relatorio_Recuperacao_20251229_143052.csv'
        """
        if not lista_auditoria:
            print(Fore.YELLOW + "⚠️  Nenhum erro para exportar.")
            return None
        
        df = self._prepare_dataframe(lista_auditoria)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Relatorio_Recuperacao_{timestamp}.csv"
        filepath = os.path.join(self.output_folder, filename)
        
        try:
            # sep=';' para compatibilidade com Excel brasileiro
            # encoding='utf-8-sig' adiciona BOM para Excel reconhecer acentos
            df.to_csv(
                filepath,
                index=False,
                sep=';',
                encoding='utf-8-sig'
            )
            
            print(Fore.GREEN + f"📊 Relatório CSV gerado: {filepath}")
            return filepath
            
        except Exception as e:
            print(Fore.RED + f"❌ Erro ao salvar CSV: {e}")
            return None


# =============================================================================
# EXEMPLO DE USO (para testes)
# =============================================================================

if __name__ == "__main__":
    """
    Exemplo de uso do gerador quando executado diretamente.
    
    Uso:
        $ python exporter.py
    """
    print("=" * 60)
    print("📊 TESTE DO GERADOR DE RELATÓRIOS")
    print("=" * 60)
    
    # Dados de exemplo
    erros_exemplo = [
        {
            "produto": "CERVEJA HEINEKEN LONG NECK 355ML",
            "ncm": "99999999",
            "ncm_correto": "22030000",
            "imposto_recuperavel": 1.50,
            "motivo": "Cerveja identificada - marca Heineken",
            "origem_analise": "Agente AI"
        },
        {
            "produto": "REFRIGERANTE COCA-COLA 2L",
            "ncm": "99999999",
            "ncm_correto": "22021000",
            "imposto_recuperavel": 0.95,
            "motivo": "Refrigerante - NCM na base de dados",
            "origem_analise": "Banco de Dados"
        },
        {
            "produto": "AGUA MINERAL CRYSTAL 500ML",
            "ncm": "99999999",
            "ncm_correto": "22011000",
            "imposto_recuperavel": 0.25,
            "motivo": "Água mineral identificada",
            "origem_analise": "Agente AI"
        }
    ]
    
    # Gera relatório
    exporter = ReportGenerator(output_folder="output_reports_teste")
    
    print("\n📝 Gerando relatório Excel...")
    filepath_excel = exporter.gerar_excel(erros_exemplo)
    
    print("\n📝 Gerando relatório CSV...")
    filepath_csv = exporter.gerar_csv(erros_exemplo)
    
    print("\n✅ Teste concluído!")
    print(f"   Excel: {filepath_excel}")
    print(f"   CSV: {filepath_csv}")
