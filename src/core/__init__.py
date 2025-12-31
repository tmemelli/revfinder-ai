"""
Pacote core - Módulos centrais do RevFinder AI.

Contém:
    - NFeParser: Extração de dados de XMLs de NF-e
    - NCMDatabase: Banco de dados inteligente de NCMs monofásicos
"""

from .parser import NFeParser
from .ncm_database import NCMDatabase

__all__ = ['NFeParser', 'NCMDatabase']
