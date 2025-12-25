"""
Moteur de calcul LMD

AUCUN CALCUL MANUEL AUTORISÉ - Tout est automatique
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.lmd_engine.rules import LMDRules
from app.models.student import Student, AcademicRecord
from app.models.course import Grade, Course, CourseEnrollment
from app.models.university import Session as AcademicSession


class LMDEngine:
    """
    Moteur de calcul automatique des règles LMD
    
    Toutes les décisions académiques passent par ce moteur
    """
    
    def __init__(self, db: AsyncSession, rules: Optional[LMDRules] = None):
        self.db = db
        self.rules = rules or LMDRules.get_default_rules()
    
    async def calculate_student_credits(
        self,
        student_id: int,
        academic_year_id: int,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculer les crédits d'un étudiant pour une année académique
        
        Returns:
            {
                "total_attempted": int,
                "total_earned": int,
                "total_in_debt": int,
                "by_course": List[Dict],
                "capitalized": int,
                "compensated": int
            }
        """
        # Récupérer toutes les notes de l'étudiant pour cette année
        query = select(Grade).where(
            Grade.student_id == student_id,
            Grade.academic_year_id == academic_year_id,
            Grade.is_active == True
        )
        
        if session_id:
            query = query.where(Grade.session_id == session_id)
        
        result = await self.db.execute(query)
        grades = result.scalars().all()
        
        total_attempted = 0
        total_earned = 0
        total_in_debt = 0
        capitalized = 0
        compensated = 0
        by_course = []
        
        for grade in grades:
            # Récupérer le cours pour les crédits
            course_query = select(Course).where(Course.id == grade.course_id)
            course_result = await self.db.execute(course_query)
            course = course_result.scalar_one_or_none()
            
            if not course:
                continue
            
            course_credits = course.credits
            total_attempted += course_credits
            
            # Déterminer si les crédits sont obtenus
            if grade.is_passed or grade.is_capitalized or grade.is_compensated:
                total_earned += course_credits
                
                if grade.is_capitalized:
                    capitalized += course_credits
                elif grade.is_compensated:
                    compensated += course_credits
            else:
                total_in_debt += course_credits
            
            by_course.append({
                "course_code": course.code,
                "course_name": course.name,
                "credits": course_credits,
                "grade": grade.final_score,
                "status": "earned" if (grade.is_passed or grade.is_capitalized or grade.is_compensated) else "debt"
            })
        
        return {
            "total_attempted": total_attempted,
            "total_earned": total_earned,
            "total_in_debt": total_in_debt,
            "by_course": by_course,
            "capitalized": capitalized,
            "compensated": compensated
        }
    
    async def apply_compensation(
        self,
        student_id: int,
        academic_year_id: int,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Appliquer les règles de compensation
        
        La compensation permet de valider des UE avec note < 50 si :
        - La moyenne générale >= seuil
        - La note compensée >= note minimale compensable
        - Nombre de crédits compensés <= maximum autorisé
        """
        if not self.rules.compensation_allowed:
            return {"compensated": [], "message": "Compensation not allowed"}
        
        # Récupérer toutes les notes
        query = select(Grade).where(
            Grade.student_id == student_id,
            Grade.academic_year_id == academic_year_id,
            Grade.session_id == session_id,
            Grade.is_active == True
        )
        
        result = await self.db.execute(query)
        grades = result.scalars().all()
        
        if not grades:
            return {"compensated": [], "message": "No grades found"}
        
        # Calculer la moyenne générale
        total_score = sum(g.final_score or 0 for g in grades if g.final_score is not None)
        average = total_score / len(grades) if grades else 0
        
        # Vérifier si la moyenne permet la compensation
        if average < self.rules.compensation_min_average:
            return {"compensated": [], "message": f"Average {average:.2f} below minimum {self.rules.compensation_min_average}"}
        
        # Identifier les notes compensables
        compensable_grades = []
        for grade in grades:
            if grade.final_score is not None and self.rules.is_compensable(grade.final_score):
                # Récupérer les crédits du cours
                course_query = select(Course).where(Course.id == grade.course_id)
                course_result = await self.db.execute(course_query)
                course = course_result.scalar_one_or_none()
                
                if course:
                    compensable_grades.append({
                        "grade": grade,
                        "credits": course.credits,
                        "score": grade.final_score
                    })
        
        # Appliquer la compensation (maximum de crédits)
        compensated = []
        total_compensated_credits = 0
        
        for item in sorted(compensable_grades, key=lambda x: x["score"], reverse=True):
            if total_compensated_credits + item["credits"] <= self.rules.compensation_max_credits:
                # Marquer comme compensé
                grade = item["grade"]
                grade.is_compensated = True
                grade.is_passed = True
                grade.credits_earned = item["credits"]
                
                compensated.append({
                    "course_code": grade.course.code,
                    "score": item["score"],
                    "credits": item["credits"]
                })
                
                total_compensated_credits += item["credits"]
        
        await self.db.commit()
        
        return {
            "compensated": compensated,
            "total_credits": total_compensated_credits,
            "average": average
        }
    
    async def calculate_gpa(
        self,
        student_id: int,
        academic_year_id: int,
        session_id: Optional[int] = None
    ) -> float:
        """
        Calculer la moyenne générale pondérée (GPA)
        """
        query = select(Grade).where(
            Grade.student_id == student_id,
            Grade.academic_year_id == academic_year_id,
            Grade.is_active == True
        )
        
        if session_id:
            query = query.where(Grade.session_id == session_id)
        
        result = await self.db.execute(query)
        grades = result.scalars().all()
        
        if not grades:
            return 0.0
        
        total_weighted_score = 0.0
        total_credits = 0
        
        for grade in grades:
            if grade.final_score is not None:
                # Récupérer les crédits du cours
                course_query = select(Course).where(Course.id == grade.course_id)
                course_result = await self.db.execute(course_query)
                course = course_result.scalar_one_or_none()
                
                if course:
                    total_weighted_score += grade.final_score * course.credits
                    total_credits += course.credits
        
        return total_weighted_score / total_credits if total_credits > 0 else 0.0
    
    async def make_academic_decision(
        self,
        student_id: int,
        academic_year_id: int
    ) -> Dict[str, Any]:
        """
        Prendre la décision académique automatique
        
        Décisions possibles :
        - "admis": réussite complète
        - "admis_conditionnel": réussite avec dettes
        - "ajourné": échec, 2e session
        - "redoublant": échec définitif
        - "réorienté": échec après max redoublements
        """
        # Calculer les crédits
        credits = await self.calculate_student_credits(student_id, academic_year_id)
        
        total_earned = credits["total_earned"]
        total_in_debt = credits["total_in_debt"]
        
        # Calculer la moyenne
        gpa = await self.calculate_gpa(student_id, academic_year_id)
        
        # Vérifier la progression
        can_progress, progression_status = self.rules.can_progress(total_earned, total_in_debt)
        
        # Déterminer la décision
        decision = None
        is_conditional = False
        
        if can_progress:
            if progression_status == "normal":
                decision = "admis"
            elif progression_status == "conditional":
                decision = "admis_conditionnel"
                is_conditional = True
        else:
            # Vérifier si 2e session possible
            if self.rules.second_session_enabled:
                decision = "ajourné"  # Peut passer en 2e session
            else:
                decision = "redoublant"
        
        # Mettre à jour le dossier académique
        record_query = select(AcademicRecord).where(
            AcademicRecord.student_id == student_id,
            AcademicRecord.academic_year_id == academic_year_id
        )
        record_result = await self.db.execute(record_query)
        record = record_result.scalar_one_or_none()
        
        if record:
            record.total_credits_earned = total_earned
            record.credits_in_debt = total_in_debt
            record.gpa_final = gpa
            record.decision = decision
            record.is_conditional = is_conditional
            record.can_progress = can_progress
            
            await self.db.commit()
        
        return {
            "decision": decision,
            "is_conditional": is_conditional,
            "can_progress": can_progress,
            "total_earned": total_earned,
            "total_in_debt": total_in_debt,
            "gpa": gpa,
            "progression_status": progression_status
        }
    
    async def check_prerequisites(
        self,
        student_id: int,
        course_id: int
    ) -> Dict[str, Any]:
        """
        Vérifier si un étudiant a validé les prérequis d'un cours
        """
        # Récupérer le cours
        course_query = select(Course).where(Course.id == course_id)
        course_result = await self.db.execute(course_query)
        course = course_result.scalar_one_or_none()
        
        if not course or not course.prerequisites:
            return {"has_prerequisites": True, "missing": []}
        
        prerequisite_codes = course.prerequisites
        missing = []
        
        # Vérifier chaque prérequis
        for prereq_code in prerequisite_codes:
            # Trouver le cours prérequis
            prereq_query = select(Course).where(Course.code == prereq_code)
            prereq_result = await self.db.execute(prereq_query)
            prereq_course = prereq_result.scalar_one_or_none()
            
            if not prereq_course:
                continue
            
            # Vérifier si l'étudiant a validé ce cours
            grade_query = select(Grade).where(
                Grade.student_id == student_id,
                Grade.course_id == prereq_course.id,
                Grade.is_passed == True
            )
            grade_result = await self.db.execute(grade_query)
            grade = grade_result.scalar_one_or_none()
            
            if not grade:
                missing.append({
                    "code": prereq_code,
                    "name": prereq_course.name
                })
        
        return {
            "has_prerequisites": len(missing) == 0,
            "missing": missing
        }