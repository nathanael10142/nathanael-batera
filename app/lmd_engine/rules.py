"""
Règles LMD configurables
"""
from typing import Dict, Any
from pydantic import BaseModel


class LMDRules(BaseModel):
    """
    Règles LMD paramétrables
    
    Ces règles peuvent être personnalisées par université/faculté
    """
    
    # Crédits
    credits_per_year: int = 60
    credits_per_semester: int = 30
    
    # Seuils de réussite
    passing_grade: float = 50.0  # Note minimale de réussite
    excellent_grade: float = 80.0
    
    # Compensation
    compensation_allowed: bool = True
    compensation_min_average: float = 50.0  # Moyenne minimale pour compenser
    compensation_min_grade: float = 40.0  # Note minimale compensable
    compensation_max_credits: int = 12  # Maximum de crédits compensables
    
    # Capitalisation
    capitalization_enabled: bool = True
    capitalization_min_grade: float = 50.0
    
    # Dettes académiques
    max_debt_credits: int = 12  # Maximum de crédits en dette pour progression
    max_debt_years: int = 2  # Maximum d'années de dettes cumulées
    
    # Progression
    min_credits_for_progression: int = 48  # Minimum pour passer au niveau supérieur
    conditional_progression_enabled: bool = True
    conditional_progression_min_credits: int = 48
    
    # Redoublement
    max_redoublements: int = 2  # Maximum de redoublements autorisés
    auto_reorientation_after_max_redoublement: bool = True
    
    # Sessions
    second_session_enabled: bool = True
    special_session_enabled: bool = True
    
    # Présence
    min_attendance_percentage: float = 75.0  # Minimum pour passer l'examen
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire"""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LMDRules":
        """Créer depuis un dictionnaire"""
        return cls(**data)
    
    @classmethod
    def get_default_rules(cls) -> "LMDRules":
        """Obtenir les règles par défaut"""
        return cls()
    
    def validate_grade(self, grade: float) -> bool:
        """Vérifier si une note est valide"""
        return 0.0 <= grade <= 100.0
    
    def is_passing_grade(self, grade: float) -> bool:
        """Vérifier si une note est une note de réussite"""
        return grade >= self.passing_grade
    
    def is_compensable(self, grade: float) -> bool:
        """Vérifier si une note peut être compensée"""
        if not self.compensation_allowed:
            return False
        return self.compensation_min_grade <= grade < self.passing_grade
    
    def can_progress(self, credits_earned: int, credits_in_debt: int) -> tuple[bool, str]:
        """
        Déterminer si un étudiant peut progresser
        
        Returns:
            (can_progress, status) où status peut être:
            - "normal": progression normale
            - "conditional": progression conditionnelle
            - "blocked": bloqué
        """
        if credits_earned >= self.min_credits_for_progression:
            return True, "normal"
        
        if self.conditional_progression_enabled:
            if credits_earned >= self.conditional_progression_min_credits:
                if credits_in_debt <= self.max_debt_credits:
                    return True, "conditional"
        
        return False, "blocked"