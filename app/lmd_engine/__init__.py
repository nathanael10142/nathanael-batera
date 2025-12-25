"""
Moteur de règles LMD (Licence-Master-Doctorat)

Ce module contient toute la logique automatique pour :
- Calcul des crédits
- Capitalisation
- Compensation
- Dettes académiques
- Prérequis
- Progression
- Décisions académiques
"""
from app.lmd_engine.engine import LMDEngine
from app.lmd_engine.rules import LMDRules

__all__ = ["LMDEngine", "LMDRules"]