"""
================================================================================
REVFINDER AI 2.0 - Sistema de Recuperação Tributária Automatizada
================================================================================

Este é o módulo principal (entry point) do sistema RevFinder AI.

O RevFinder AI é uma ferramenta que analisa arquivos XML de Notas Fiscais 
Eletrônicas (NF-e) para identificar pagamentos indevidos de PIS/COFINS em 
produtos com tributação monofásica.

ARQUITETURA DO SISTEMA (v2.0):
------------------------------
O sistema funciona em 4 etapas (pipeline):

    1. CARREGAMENTO: Carrega banco de dados rico de NCMs
    2. PARSING: Lê e extrai dados dos XMLs de NF-e
    3. AUDITORIA: Verifica cada item em 3 níveis:
       - Nível 1: Banco de dados (NCM exato)
       - Nível 2: Identificação por keywords (nome do produto)
       - Nível 3: Inteligência Artificial (último recurso)
    4. EXPORTAÇÃO: Gera relatório Excel com valores recuperáveis

VANTAGENS DA v2.0:
------------------
    - Banco de dados rico com keywords de produtos
    - Identificação por nome ANTES de chamar IA
    - Economia de até 80% em chamadas de API
    - Base legal incluída nos relatórios

Autor: Grande Mestre
Versão: 2.0
Data: Dezembro/2025
Licença: MIT
================================================================================
"""

# =============================================================================
# IMPORTS
# =============================================================================
import os
import sys
from colorama import Fore, init
from dotenv import load_dotenv

# Adiciona o diretório pai ao path para imports funcionarem
# Isso permite rodar tanto "python run.py" da raiz quanto "python main.py" de src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Módulos Internos do Projeto
from src.core.parser import NFeParser
from src.core.ncm_database import NCMDatabase
from src.utils.exporter import ReportGenerator
from src.agents.auditor import FiscalAuditorAgent

# =============================================================================
# INICIALIZAÇÃO
# =============================================================================
init(autoreset=True)
load_dotenv()

# =============================================================================
# CONSTANTES DE CONFIGURAÇÃO
# =============================================================================

# Diretório onde o usuário deve colocar os arquivos XML
INPUT_DIR = "input_xmls"

# Diretório para relatórios de saída
OUTPUT_DIR = "output_reports"

# Caminho para o banco de dados JSON de NCMs monofásicos
# Usa caminho relativo ao arquivo para funcionar de qualquer diretório
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "ncm_rules.json")


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def print_header() -> None:
    """Imprime o cabeçalho visual do sistema."""
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + "🚀 REVFINDER AI 2.0 - SISTEMA DE RECUPERAÇÃO TRIBUTÁRIA")
    print(Fore.CYAN + "=" * 60 + "\n")


def print_summary(total_recuperavel: float, stats: dict) -> None:
    """Imprime o resumo final da análise."""
    print("\n" + Fore.GREEN + "=" * 60)
    print(Fore.WHITE + f"💰 TOTAL RECUPERÁVEL: R$ {total_recuperavel:.2f}")
    print(Fore.GREEN + "=" * 60)
    
    if stats:
        print(Fore.CYAN + "\n📊 Estatísticas da Análise:")
        print(Fore.WHITE + f"   • Identificados por Banco de Dados: {stats.get('banco_dados', 0)}")
        print(Fore.WHITE + f"   • Identificados por Keywords: {stats.get('keywords', 0)}")
        print(Fore.WHITE + f"   • Identificados por IA: {stats.get('ia', 0)}")
        print(Fore.WHITE + f"   • Chamadas de IA economizadas: {stats.get('ia_economizada', 0)}")


def initialize_ai_agent() -> FiscalAuditorAgent | None:
    """
    Tenta inicializar o agente de IA para auditoria fiscal.
    
    Returns:
        FiscalAuditorAgent | None: Instância do agente ou None se falha.
    """
    try:
        ia_auditor = FiscalAuditorAgent()
        print(Fore.BLUE + "🤖 Agente IA: ONLINE\n")
        return ia_auditor
    except Exception as e:
        print(Fore.YELLOW + f"⚠️  Agente IA: OFFLINE (modo economia)")
        print(Fore.YELLOW + f"   Motivo: {str(e)[:50]}...\n")
        return None


def analyze_item(
    item: dict,
    ncm_db: NCMDatabase,
    ia_auditor: FiscalAuditorAgent | None,
    stats: dict
) -> dict | None:
    """
    Analisa um item da nota fiscal para verificar se há imposto recuperável.
    
    Verificação em 3 níveis:
        1. Banco de dados (NCM exato) - GRÁTIS e INSTANTÂNEO
        2. Keywords (nome do produto) - GRÁTIS e INSTANTÂNEO
        3. Inteligência Artificial - PAGO e LENTO (último recurso)
    
    Args:
        item (dict): Dados do item da NF-e
        ncm_db (NCMDatabase): Banco de dados de NCMs
        ia_auditor (FiscalAuditorAgent | None): Agente de IA ou None
        stats (dict): Dicionário para acumular estatísticas
    
    Returns:
        dict | None: Erro encontrado ou None se item está ok
    """
    # Se não pagou imposto, não tem o que recuperar
    if item['imposto_total'] <= 0:
        return None
    
    # =========================================================================
    # ETAPA 1 e 2: Verificação pelo Banco de Dados (NCM + Keywords)
    # =========================================================================
    resultado_db = ncm_db.verificar_item(item['ncm'], item['produto'])
    
    if resultado_db['is_monofasico']:
        # Determina a fonte da identificação
        if resultado_db['fonte'] == 'banco_dados':
            stats['banco_dados'] = stats.get('banco_dados', 0) + 1
            origem = "Banco de Dados"
            motivo = f"NCM {item['ncm']} é monofásico - {resultado_db['descricao']}"
        elif resultado_db['fonte'] == 'cache_ia':
            # NOVO v2.1: Identificado pelo cache de aprendizado da IA
            stats['ia_economizada'] = stats.get('ia_economizada', 0) + 1
            origem = "Cache IA (Aprendizado)"
            motivo = f"Produto identificado por aprendizado anterior - {resultado_db['descricao']}"
            print(Fore.CYAN + f"   🧠 Cache hit! Economizou chamada de IA")
        else:
            stats['keywords'] = stats.get('keywords', 0) + 1
            stats['ia_economizada'] = stats.get('ia_economizada', 0) + 1
            origem = "Identificação por Nome"
            keyword = resultado_db.get('keyword_encontrada', '')
            motivo = f"Produto identificado por keyword '{keyword}' - {resultado_db['descricao']}"
        
        # NCM atual está errado?
        ncm_correto = resultado_db['ncm_correto']
        if not resultado_db['ncm_atual_correto']:
            print(Fore.YELLOW + f"   ⚠️  NCM INCORRETO: {item['ncm']} → deveria ser {ncm_correto}")
        
        print(Fore.RED + f"   🚨 RECUPERÁVEL: R$ {item['imposto_total']:.2f} ({item['produto'][:30]}...)")
        
        return {
            # Dados da nota (v2.1)
            "chave_acesso": item.get('chave_acesso', ''),
            "numero_nota": item.get('numero_nota', ''),
            "data_emissao": item.get('data_emissao', ''),
            "cnpj_emitente": item.get('cnpj_emitente', ''),
            "nome_emitente": item.get('nome_emitente', ''),
            # Dados do item
            "produto": item['produto'],
            "ncm": item['ncm'],
            "ncm_correto": ncm_correto,
            "imposto_recuperavel": item['imposto_total'],
            "motivo": motivo,
            "origem_analise": origem,
            "base_legal": resultado_db['base_legal'],
            "confianca": resultado_db.get('confianca', 'alta')
        }
    
    # =========================================================================
    # ETAPA 3: Inteligência Artificial (último recurso)
    # =========================================================================
    # Só chama IA se:
    # 1. Não encontrou no banco de dados
    # 2. Não encontrou no cache de aprendizado (NOVO v2.1)
    # 3. Agente está disponível
    # 4. Item tem imposto pago (já verificado acima)
    
    # NOVO v2.1: Se já tem no cache, NÃO chama IA (mesmo que não seja monofásico)
    if resultado_db.get('fonte') == 'cache_ia':
        stats['ia_economizada'] = stats.get('ia_economizada', 0) + 1
        print(Fore.CYAN + f"   🧠 Cache hit! '{item['produto'][:30]}...' não é monofásico (economizou IA)")
        return None  # Não é monofásico, não tem o que recuperar
    # 3. Item tem imposto pago (já verificado acima)
    
    if ia_auditor:
        print(Fore.YELLOW + f"   🤔 Consultando IA para '{item['produto'][:30]}...'")
        
        resultado_ia = ia_auditor.analyze_item(
            descricao=item['produto'],
            ncm_errado=item['ncm'],
            valor_item=item['valor_total']
        )
        
        # NOVO v2.1: Salva o aprendizado da IA no cache (independente do resultado)
        # Isso evita consultas repetidas ao mesmo produto no futuro
        ncm_db.salvar_aprendizado_ia(
            nome_produto=item['produto'],
            is_monofasico=(resultado_ia[0] == True),
            ncm_sugerido=resultado_ia[1],
            motivo=resultado_ia[2]
        )
        
        # resultado_ia = [is_monofasico, ncm_correto, motivo]
        if resultado_ia[0] == True:
            stats['ia'] = stats.get('ia', 0) + 1
            
            print(Fore.GREEN + f"   🤖 IA identificou! NCM correto: {resultado_ia[1]}")
            print(Fore.RED + f"   🚨 RECUPERÁVEL: R$ {item['imposto_total']:.2f}")
            
            return {
                # Dados da nota (v2.1)
                "chave_acesso": item.get('chave_acesso', ''),
                "numero_nota": item.get('numero_nota', ''),
                "data_emissao": item.get('data_emissao', ''),
                "cnpj_emitente": item.get('cnpj_emitente', ''),
                "nome_emitente": item.get('nome_emitente', ''),
                # Dados do item
                "produto": item['produto'],
                "ncm": item['ncm'],
                "ncm_correto": resultado_ia[1],
                "imposto_recuperavel": item['imposto_total'],
                "motivo": resultado_ia[2],
                "origem_analise": "Agente IA",
                "base_legal": ncm_db.get_base_legal(),
                "confianca": "media"
            }
    
    return None


# =============================================================================
# FUNÇÃO PRINCIPAL - PIPELINE DE PROCESSAMENTO
# =============================================================================

def process_pipeline() -> None:
    """
    Executa o pipeline completo de auditoria tributária.
    
    FLUXO:
    1. Inicializa componentes (Parser, Database, Exporter, IA)
    2. Lista arquivos XML no diretório de input
    3. Processa cada arquivo, analisando cada item
    4. Gera relatório Excel com resultados
    """
    
    print_header()
    
    # =========================================================================
    # ETAPA 1: INICIALIZAÇÃO DOS COMPONENTES
    # =========================================================================
    
    parser = NFeParser()
    exporter = ReportGenerator(output_folder=OUTPUT_DIR)
    
    # Carrega banco de dados rico de NCMs
    ncm_db = NCMDatabase(DB_PATH)
    
    # Mostra estatísticas do banco
    db_stats = ncm_db.get_estatisticas()
    print(Fore.CYAN + f"📚 Base de dados: {db_stats['total_ncms']} NCMs, {db_stats['total_keywords']} keywords")
    print(Fore.CYAN + f"📜 Base legal: {db_stats['base_legal']}\n")
    
    # Inicializa agente de IA (opcional)
    ia_auditor = initialize_ai_agent()
    
    # =========================================================================
    # ETAPA 2: COLETA DE ARQUIVOS XML
    # =========================================================================
    
    if not os.path.exists(INPUT_DIR):
        print(Fore.RED + f"❌ Diretório '{INPUT_DIR}' não encontrado!")
        print(Fore.YELLOW + f"   Crie a pasta e coloque os arquivos XML nela.")
        return
    
    arquivos_xml = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.xml')]
    
    if not arquivos_xml:
        print(Fore.YELLOW + f"⚠️  Nenhum arquivo XML encontrado em '{INPUT_DIR}'.")
        return
    
    print(Fore.WHITE + f"📋 {len(arquivos_xml)} arquivo(s) para análise.\n")
    
    # =========================================================================
    # ETAPA 3: PROCESSAMENTO DOS ARQUIVOS
    # =========================================================================
    
    erros_encontrados = []
    total_recuperavel = 0.0
    stats = {
        'banco_dados': 0,
        'keywords': 0,
        'ia': 0,
        'ia_economizada': 0
    }
    
    for xml_file in arquivos_xml:
        caminho_xml = os.path.join(INPUT_DIR, xml_file)
        print(f"📂 Processando: {xml_file}...")
        
        itens_nota = parser.parse(caminho_xml)
        
        if not itens_nota:
            print(Fore.YELLOW + f"   ⚠️  Não foi possível extrair itens de {xml_file}")
            continue
        
        for item in itens_nota:
            erro = analyze_item(item, ncm_db, ia_auditor, stats)
            
            if erro:
                erros_encontrados.append(erro)
                total_recuperavel += erro['imposto_recuperavel']
    
    # =========================================================================
    # ETAPA 4: FINALIZAÇÃO E RELATÓRIO
    # =========================================================================
    
    print_summary(total_recuperavel, stats)
    
    if total_recuperavel > 0:
        exporter.gerar_excel(erros_encontrados)
        
        print(Fore.CYAN + f"\n📈 Resumo Final:")
        print(Fore.WHITE + f"   • Arquivos analisados: {len(arquivos_xml)}")
        print(Fore.WHITE + f"   • Erros encontrados: {len(erros_encontrados)}")
        print(Fore.WHITE + f"   • Valor médio por erro: R$ {total_recuperavel/len(erros_encontrados):.2f}")
        
        # Calcula economia de IA
        total_identificados = stats['banco_dados'] + stats['keywords'] + stats['ia']
        if total_identificados > 0:
            economia_pct = (stats['ia_economizada'] / total_identificados) * 100
            print(Fore.GREEN + f"   • Economia de chamadas IA: {economia_pct:.0f}%")
    else:
        print(Fore.GREEN + "\n✅ Nenhum pagamento indevido encontrado.")


# =============================================================================
# PONTO DE ENTRADA DO PROGRAMA
# =============================================================================

if __name__ == "__main__":
    process_pipeline()
