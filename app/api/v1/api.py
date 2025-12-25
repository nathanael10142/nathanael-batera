from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    courses,
    faculties,
    finances,
    grades,
    messages,
    students,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(faculties.router, prefix="/faculties", tags=["Faculties"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])
api_router.include_router(grades.router, prefix="/grades", tags=["Grades"])
api_router.include_router(finances.router, prefix="/finances", tags=["Finances"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])