"""
================================================================================
TESTES UNITÁRIOS - RevFinder AI
================================================================================

Execute com: pytest tests/ -v
"""

import os
import sys
import pytest

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.parser import NFeParser
from src.core.ncm_database import NCMDatabase


class TestNFeParser:
    """Testes para o parser de NF-e."""
    
    def setup_method(self):
        """Inicializa o parser antes de cada teste."""
        self.parser = NFeParser()
    
    def test_parser_initialization(self):
        """Testa se o parser inicializa corretamente."""
        assert self.parser is not None
        assert self.parser.ns is not None
        assert 'nfe' in self.parser.ns
    
    def test_safe_find_text_with_default(self):
        """Testa função de busca segura com valor default."""
        # Quando elemento não existe, deve retornar default
        import xml.etree.ElementTree as ET
        root = ET.fromstring('<root></root>')
        result = self.parser._safe_find_text(root, 'inexistente', 'DEFAULT')
        assert result == 'DEFAULT'
    
    def test_safe_find_float_with_default(self):
        """Testa função de busca numérica segura."""
        import xml.etree.ElementTree as ET
        root = ET.fromstring('<root></root>')
        result = self.parser._safe_find_float(root, 'inexistente', 99.99)
        assert result == 99.99


class TestNCMDatabase:
    """Testes para o banco de dados de NCMs."""
    
    def setup_method(self):
        """Inicializa o banco antes de cada teste."""
        db_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'src', 'database', 'ncm_rules.json'
        )
        self.db = NCMDatabase(db_path)
    
    def test_database_loads(self):
        """Testa se o banco de dados carrega."""
        assert self.db is not None
        assert len(self.db.ncm_lista) > 0
    
    def test_cerveja_is_monofasico(self):
        """Testa se cerveja (22030000) é identificada como monofásica."""
        assert self.db.is_monofasico("22030000") == True
    
    def test_refrigerante_is_monofasico(self):
        """Testa se refrigerante (22021000) é identificado como monofásico."""
        assert self.db.is_monofasico("22021000") == True
    
    def test_ncm_generico_not_monofasico(self):
        """Testa se NCM genérico não é monofásico."""
        assert self.db.is_monofasico("99999999") == False
    
    def test_identificar_heineken_por_nome(self):
        """Testa identificação de Heineken pelo nome."""
        resultado = self.db.identificar_por_nome("HEINEKEN LONG NECK 355ML")
        assert resultado is not None
        assert resultado['ncm_sugerido'] == "22030000"
        assert resultado['confianca'] == "alta"
    
    def test_identificar_coca_por_nome(self):
        """Testa identificação de Coca-Cola pelo nome."""
        resultado = self.db.identificar_por_nome("COCA COLA 2L")
        assert resultado is not None
        assert resultado['ncm_sugerido'] == "22021000"
    
    def test_nao_identificar_comida(self):
        """Testa que comida não é identificada como monofásico."""
        resultado = self.db.identificar_por_nome("ARROZ TIPO 1 5KG")
        assert resultado is None
    
    def test_verificar_item_ncm_errado(self):
        """Testa verificação de item com NCM errado."""
        resultado = self.db.verificar_item("99999999", "CERVEJA HEINEKEN 600ML")
        assert resultado['is_monofasico'] == True
        assert resultado['ncm_atual_correto'] == False
        assert resultado['ncm_correto'] == "22030000"
    
    def test_verificar_item_ncm_correto(self):
        """Testa verificação de item com NCM correto."""
        resultado = self.db.verificar_item("22030000", "CERVEJA QUALQUER")
        assert resultado['is_monofasico'] == True
        assert resultado['ncm_atual_correto'] == True


# =============================================================================
# EXECUÇÃO DIRETA
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
