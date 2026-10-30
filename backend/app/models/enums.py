from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "student"
    ADMIN = "admin"


class AssignmentType(StrEnum):
    WORKSHEET = "worksheet"
    QUIZ = "quiz"
    LAB_REPORT = "lab_report"
    CODING = "coding"
    PROJECT = "project"


class MembershipRole(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    CLASS_ADMIN = "class_admin"
