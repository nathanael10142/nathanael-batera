"""
Moteur de calcul LMD adapté pour Firestore

Remplace les accès SQL par des requêtes Firestore. L'API publique reste la même
(les identifiants d'étudiants/ids de documents sont traités comme des chaînes).
"""
from typing import List, Dict, Any, Optional
from firebase_admin import firestore

from app.lmd_engine.rules import LMDRules


class LMDEngine:
    """
    Moteur de calcul automatique des règles LMD utilisant Firestore.
    """

    def __init__(self, rules: Optional[LMDRules] = None):
        self.db = firestore.client()
        self.rules = rules or LMDRules.get_default_rules()

    def _as_str(self, v) -> str:
        return str(v) if v is not None else ""

    def _fetch_course(self, course_id: Any) -> Optional[dict]:
        if course_id is None:
            return None
        doc = self.db.collection("courses").document(self._as_str(course_id)).get()
        return doc.to_dict() if doc.exists else None

    def _fetch_academic_record_doc(self, student_id: Any, academic_year_id: Any) -> Optional[firestore.DocumentReference]:
        # We assume academic_records collection stores documents keyed by an auto id and contains student_uid and academic_year_id
        q = self.db.collection("academic_records").where("student_uid", "==", self._as_str(student_id)).where("academic_year_id", "==", academic_year_id).limit(1).stream()
        docs = list(q)
        return docs[0].reference if docs else None

    def _fetch_grades(self, student_id: Any, academic_year_id: Any, session_id: Optional[Any] = None) -> List[dict]:
        q = self.db.collection("grades").where("student_uid", "==", self._as_str(student_id)).where("academic_year_id", "==", academic_year_id)
        if session_id is not None:
            q = q.where("session_id", "==", session_id)
        return [d.to_dict() | {"_id": d.id} for d in q.stream()]

    def _update_grade(self, grade_doc_id: str, data: dict):
        self.db.collection("grades").document(self._as_str(grade_doc_id)).update(data)

    def _commit_batch(self, updates: List[tuple]):
        # updates: list of (collection, doc_id, data)
        batch = self.db.batch()
        for coll, doc_id, data in updates:
            ref = self.db.collection(coll).document(self._as_str(doc_id))
            batch.update(ref, data)
        batch.commit()

    async def calculate_student_credits(
        self,
        student_id: Any,
        academic_year_id: Any,
        session_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Calculer les crédits d'un étudiant pour une année académique en lisant les documents Firestore.
        """
        grades = self._fetch_grades(student_id, academic_year_id, session_id)

        total_attempted = 0
        total_earned = 0
        total_in_debt = 0
        capitalized = 0
        compensated = 0
        by_course = []

        for g in grades:
            course = self._fetch_course(g.get("course_id"))
            if not course:
                continue

            course_credits = int(course.get("credits", 0) or 0)
            total_attempted += course_credits

            is_passed = bool(g.get("is_passed", False))
            is_capitalized = bool(g.get("is_capitalized", False))
            is_compensated = bool(g.get("is_compensated", False))

            if is_passed or is_capitalized or is_compensated:
                total_earned += course_credits
                if is_capitalized:
                    capitalized += course_credits
                elif is_compensated:
                    compensated += course_credits
            else:
                total_in_debt += course_credits

            by_course.append({
                "course_code": course.get("code"),
                "course_name": course.get("name"),
                "credits": course_credits,
                "grade": g.get("final_score"),
                "status": "earned" if (is_passed or is_capitalized or is_compensated) else "debt"
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
        student_id: Any,
        academic_year_id: Any,
        session_id: Any
    ) -> Dict[str, Any]:
        """
        Appliquer les règles de compensation en mettant à jour les documents grades dans Firestore.
        """
        if not self.rules.compensation_allowed:
            return {"compensated": [], "message": "Compensation not allowed"}

        grades = self._fetch_grades(student_id, academic_year_id, session_id)
        if not grades:
            return {"compensated": [], "message": "No grades found"}

        # Calculer la moyenne générale
        scores = [g.get("final_score") for g in grades if g.get("final_score") is not None]
        total_score = sum(scores) if scores else 0
        average = total_score / len(scores) if scores else 0

        if average < self.rules.compensation_min_average:
            return {"compensated": [], "message": f"Average {average:.2f} below minimum {self.rules.compensation_min_average}"}

        # Identifier notes compensables
        compensable = []
        for g in grades:
            score = g.get("final_score")
            if score is None:
                continue
            if self.rules.is_compensable(score):
                course = self._fetch_course(g.get("course_id"))
                if not course:
                    continue
                compensable.append({"grade_doc": g.get("_id"), "score": score, "credits": int(course.get("credits", 0) or 0)})

        compensated = []
        total_comp_credits = 0
        updates = []

        for item in sorted(compensable, key=lambda x: x["score"], reverse=True):
            if total_comp_credits + item["credits"] <= self.rules.compensation_max_credits:
                # Mark grade document as compensated
                updates.append(("grades", item["grade_doc"], {"is_compensated": True, "is_passed": True, "credits_earned": item["credits"]}))
                compensated.append({"grade_doc": item["grade_doc"], "score": item["score"], "credits": item["credits"]})
                total_comp_credits += item["credits"]

        if updates:
            self._commit_batch(updates)

        return {"compensated": compensated, "total_credits": total_comp_credits, "average": average}

    async def calculate_gpa(
        self,
        student_id: Any,
        academic_year_id: Any,
        session_id: Optional[Any] = None
    ) -> float:
        grades = self._fetch_grades(student_id, academic_year_id, session_id)
        if not grades:
            return 0.0

        total_weighted_score = 0.0
        total_credits = 0

        for g in grades:
            score = g.get("final_score")
            if score is None:
                continue
            course = self._fetch_course(g.get("course_id"))
            if not course:
                continue
            credits = int(course.get("credits", 0) or 0)
            total_weighted_score += score * credits
            total_credits += credits

        return (total_weighted_score / total_credits) if total_credits > 0 else 0.0

    async def make_academic_decision(
        self,
        student_id: Any,
        academic_year_id: Any
    ) -> Dict[str, Any]:
        credits = await self.calculate_student_credits(student_id, academic_year_id)
        total_earned = credits["total_earned"]
        total_in_debt = credits["total_in_debt"]

        gpa = await self.calculate_gpa(student_id, academic_year_id)

        can_progress, progression_status = self.rules.can_progress(total_earned, total_in_debt)

        decision = None
        is_conditional = False

        if can_progress:
            if progression_status == "normal":
                decision = "admis"
            elif progression_status == "conditional":
                decision = "admis_conditionnel"
                is_conditional = True
        else:
            if self.rules.second_session_enabled:
                decision = "ajourné"
            else:
                decision = "redoublant"

        # Mettre à jour le dossier académique si présent
        rec_ref = self._fetch_academic_record_doc(student_id, academic_year_id)
        if rec_ref:
            rec_ref.update({
                "total_credits_earned": total_earned,
                "credits_in_debt": total_in_debt,
                "gpa_final": gpa,
                "decision": decision,
                "is_conditional": is_conditional,
                "can_progress": can_progress
            })

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
        student_id: Any,
        course_id: Any
    ) -> Dict[str, Any]:
        course = self._fetch_course(course_id)
        if not course or not course.get("prerequisites"):
            return {"has_prerequisites": True, "missing": []}

        prerequisite_codes = course.get("prerequisites")
        missing = []

        for prereq_code in prerequisite_codes:
            # Find prereq course by code
            q = self.db.collection("courses").where("code", "==", prereq_code).limit(1).stream()
            prereq_docs = list(q)
            if not prereq_docs:
                continue
            prereq_course = prereq_docs[0].to_dict()
            prereq_id = prereq_docs[0].id

            # Check if student has a passing grade for this prereq
            qg = self.db.collection("grades").where("student_uid", "==", self._as_str(student_id)).where("course_id", "==", prereq_id).where("is_passed", "==", True).limit(1).stream()
            passed = any(True for _ in qg)
            if not passed:
                missing.append({"code": prereq_code, "name": prereq_course.get("name")})

        return {"has_prerequisites": len(missing) == 0, "missing": missing}