"""
Initialisation de la base de données avec données de démonstration
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.security import get_password_hash
from app.models import (
    University, Faculty, Department, Option,
    AcademicYear, Session,
    Role, Permission, User,
    CycleType, YearLevel
)


async def init_permissions(db: AsyncSession) -> list[Permission]:
    """Créer les permissions de base"""
    permissions_data = [
        # Admin
        {"name": "Full Admin Access", "code": "admin.full", "category": "admin"},
        {"name": "Create Faculty", "code": "admin.create_faculty", "category": "admin"},
        {"name": "Manage Users", "code": "admin.manage_users", "category": "admin"},
        
        # Academic
        {"name": "View Academic Data", "code": "academic.view", "category": "academic"},
        {"name": "Manage Academic Data", "code": "academic.manage", "category": "academic"},
        {"name": "Encode Grades", "code": "academic.encode_notes", "category": "academic"},
        {"name": "Validate Grades", "code": "academic.validate_notes", "category": "academic"},
        {"name": "Conduct Deliberation", "code": "academic.deliberation", "category": "academic"},
        
        # Financial
        {"name": "View Financial Data", "code": "financial.view", "category": "financial"},
        {"name": "Manage Financial Data", "code": "financial.manage", "category": "financial"},
        {"name": "Process Payments", "code": "financial.payment", "category": "financial"},
        {"name": "Audit Financial Data", "code": "financial.audit", "category": "financial"},
        
        # Student
        {"name": "View Own Data", "code": "student.view_own", "category": "student"},
        {"name": "Manage Own Data", "code": "student.manage_own", "category": "student"},
        
        # Communication
        {"name": "Send Messages", "code": "communication.send", "category": "communication"},
        {"name": "Send Official Messages", "code": "communication.official", "category": "communication"},
    ]
    
    permissions = []
    for perm_data in permissions_data:
        permission = Permission(**perm_data)
        db.add(permission)
        permissions.append(permission)
    
    await db.commit()
    return permissions


async def init_roles(db: AsyncSession, permissions: list[Permission]) -> dict[str, Role]:
    """Créer les rôles de base"""
    
    # Mapper les permissions par code
    perm_map = {p.code: p for p in permissions}
    
    roles_data = {
        "super_admin": {
            "name": "Super Administrateur",
            "code": "super_admin",
            "category": "administrative",
            "hierarchy_level": 100,
            "permissions": [perm_map["admin.full"]]
        },
        "recteur": {
            "name": "Recteur",
            "code": "recteur",
            "category": "academic",
            "hierarchy_level": 90,
            "permissions": [
                perm_map["academic.view"],
                perm_map["academic.manage"],
                perm_map["academic.deliberation"],
                perm_map["financial.view"],
                perm_map["communication.official"]
            ]
        },
        "doyen": {
            "name": "Doyen",
            "code": "doyen",
            "category": "academic",
            "hierarchy_level": 80,
            "permissions": [
                perm_map["academic.view"],
                perm_map["academic.manage"],
                perm_map["academic.validate_notes"],
                perm_map["academic.deliberation"],
                perm_map["financial.view"],
                perm_map["communication.official"]
            ]
        },
        "chef_departement": {
            "name": "Chef de Département",
            "code": "chef_departement",
            "category": "academic",
            "hierarchy_level": 70,
            "permissions": [
                perm_map["academic.view"],
                perm_map["academic.manage"],
                perm_map["academic.validate_notes"],
                perm_map["communication.send"]
            ]
        },
        "enseignant": {
            "name": "Enseignant",
            "code": "enseignant",
            "category": "academic",
            "hierarchy_level": 60,
            "permissions": [
                perm_map["academic.view"],
                perm_map["academic.encode_notes"],
                perm_map["communication.send"]
            ]
        },
        "etudiant": {
            "name": "Étudiant",
            "code": "etudiant",
            "category": "academic",
            "hierarchy_level": 10,
            "permissions": [
                perm_map["student.view_own"],
                perm_map["student.manage_own"],
                perm_map["communication.send"]
            ]
        },
        "comptable": {
            "name": "Comptable",
            "code": "comptable",
            "category": "financial",
            "hierarchy_level": 50,
            "permissions": [
                perm_map["financial.view"],
                perm_map["financial.manage"],
                perm_map["financial.payment"]
            ]
        },
        "secretaire": {
            "name": "Secrétaire",
            "code": "secretaire",
            "category": "administrative",
            "hierarchy_level": 40,
            "permissions": [
                perm_map["academic.view"],
                perm_map["communication.send"]
            ]
        }
    }
    
    roles = {}
    for role_code, role_data in roles_data.items():
        role = Role(
            name=role_data["name"],
            code=role_data["code"],
            category=role_data["category"],
            hierarchy_level=role_data["hierarchy_level"]
        )
        role.permissions = role_data["permissions"]
        db.add(role)
        roles[role_code] = role
    
    await db.commit()
    return roles


async def init_university_structure(db: AsyncSession) -> dict:
    """Créer la structure universitaire modèle"""
    
    # Université
    university = University(
        name="Université de Goma",
        code="UNIGOM",
        acronym="UNIGOM",
        email="info@unigom.ac.cd",
        phone="+243 XXX XXX XXX",
        address="Goma, Nord-Kivu, RDC",
        lmd_settings={
            "credits_per_year": 60,
            "passing_grade": 50.0,
            "compensation_allowed": True
        }
    )
    db.add(university)
    await db.commit()
    
    # Faculté modèle : Faculté des Sciences
    faculty = Faculty(
        university_id=university.id,
        name="Faculté des Sciences",
        code="FSC",
        acronym="FSC",
        email="sciences@unigom.ac.cd",
        dean_name="Prof. KASONGO Jean",
        has_graduat=True,
        has_licence=True,
        has_master=True
    )
    db.add(faculty)
    await db.commit()
    
    # Départements
    dept_info = Department(
        faculty_id=faculty.id,
        name="Informatique",
        code="INFO",
        head_name="Dr. MUKENDI Paul"
    )
    
    dept_math = Department(
        faculty_id=faculty.id,
        name="Mathématiques",
        code="MATH",
        head_name="Prof. KABAMBA Marie"
    )
    
    db.add(dept_info)
    db.add(dept_math)
    await db.commit()
    
    # Options
    option_info = Option(
        department_id=dept_info.id,
        name="Génie Logiciel",
        code="GL",
        has_graduat=True,
        has_licence=True
    )
    
    option_reseaux = Option(
        department_id=dept_info.id,
        name="Réseaux et Télécommunications",
        code="RT",
        has_graduat=True
    )
    
    db.add(option_info)
    db.add(option_reseaux)
    await db.commit()
    
    # Année académique
    current_year = datetime.now().year
    academic_year = AcademicYear(
        name=f"{current_year}-{current_year + 1}",
        start_date=datetime(current_year, 9, 1),
        end_date=datetime(current_year + 1, 7, 31),
        is_current=True
    )
    db.add(academic_year)
    await db.commit()
    
    # Sessions
    session_1 = Session(
        academic_year_id=academic_year.id,
        name="1ère Session",
        session_type="first",
        start_date=datetime(current_year + 1, 1, 15),
        end_date=datetime(current_year + 1, 2, 28)
    )
    
    session_2 = Session(
        academic_year_id=academic_year.id,
        name="2e Session",
        session_type="second",
        start_date=datetime(current_year + 1, 7, 1),
        end_date=datetime(current_year + 1, 7, 20)
    )
    
    db.add(session_1)
    db.add(session_2)
    await db.commit()
    
    return {
        "university": university,
        "faculty": faculty,
        "departments": [dept_info, dept_math],
        "options": [option_info, option_reseaux],
        "academic_year": academic_year,
        "sessions": [session_1, session_2]
    }


async def init_admin_user(db: AsyncSession, roles: dict) -> User:
    """Créer l'utilisateur administrateur"""
    admin_user = User(
        username="admin",
        email="admin@unigom.ac.cd",
        hashed_password=get_password_hash("admin123"),
        first_name="Administrateur",
        last_name="Système",
        is_active=True,
        is_superuser=True,
        email_verified=True,
        role_id=roles["super_admin"].id
    )
    db.add(admin_user)
    await db.commit()
    return admin_user


async def init_db(db: AsyncSession) -> None:
    """Initialiser la base de données complète"""
    print("🚀 Initialisation de la base de données...")
    
    print("📝 Création des permissions...")
    permissions = await init_permissions(db)
    
    print("👥 Création des rôles...")
    roles = await init_roles(db, permissions)
    
    print("🏛️ Création de la structure universitaire...")
    structure = await init_university_structure(db)
    
    print("🔑 Création de l'administrateur...")
    admin = await init_admin_user(db, roles)
    
    print("✅ Base de données initialisée avec succès!")
    print(f"   - Université: {structure['university'].name}")
    print(f"   - Faculté modèle: {structure['faculty'].name}")
    print(f"   - Départements: {len(structure['departments'])}")
    print(f"   - Options: {len(structure['options'])}")
    print(f"   - Année académique: {structure['academic_year'].name}")
    print(f"   - Admin: {admin.username} / admin123")