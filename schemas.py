"""
schemas.py
==========
Esquemas Pydantic para validación de datos de entrada y serialización de respuestas.
Implementa el patrón DTO (Data Transfer Object) para desacoplar el modelo de dominio
del modelo de presentación (Patrón DTO del documento de diseño).
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


# ==============================================================================
# SCHEMAS: Docente
# ==============================================================================
class DocenteBase(BaseModel):
    nombre: str
    correo: str
    tipo_vinculacion: str = "TC"  # TC / 3/4T / MT / 1/4T
    estado: bool = True

class DocenteCreate(DocenteBase):
    pass

class DocenteOut(DocenteBase):
    id: int
    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: Curso
# ==============================================================================
class CursoBase(BaseModel):
    nombre: str
    codigo: str
    creditos: int = 3
    sesiones_semana: int = 2
    duracion_sesion_h: int = 2
    requiere_computadores: bool = False
    requiere_sillas_moviles: bool = False
    estado: bool = True

class CursoCreate(CursoBase):
    pass

class CursoOut(CursoBase):
    id: int
    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: Grupo
# ==============================================================================
class GrupoBase(BaseModel):
    id_curso: int
    nombre_grupo: str
    cupo_objetivo: int = 40
    inscritos: int = 0
    estado: str = "Activo"

class GrupoCreate(GrupoBase):
    pass

class GrupoOut(GrupoBase):
    id: int
    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: Aula
# ==============================================================================
class AulaBase(BaseModel):
    codigo: str
    capacidad: int
    tiene_computadores: bool = False
    tiene_sillas_moviles: bool = False
    edificio: Optional[str] = None
    estado: bool = True

class AulaCreate(AulaBase):
    pass

class AulaOut(AulaBase):
    id: int
    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: FranjaHoraria
# ==============================================================================
class FranjaBase(BaseModel):
    dia_semana: str   # Lunes, Martes, Miercoles, Jueves, Viernes, Sabado
    hora_inicio: str  # "07:00"
    hora_fin: str     # "09:00"
    bloqueada: bool = False

class FranjaCreate(FranjaBase):
    pass

class FranjaOut(FranjaBase):
    id: int
    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: DisponibilidadDocente
# ==============================================================================
class DisponibilidadBase(BaseModel):
    id_docente: int
    id_franja: int

class DisponibilidadCreate(DisponibilidadBase):
    pass

class DisponibilidadOut(DisponibilidadBase):
    id: int
    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: ElegibilidadDocente
# ==============================================================================
class ElegibilidadBase(BaseModel):
    id_docente: int
    id_curso: int
    activo: bool = True

class ElegibilidadCreate(ElegibilidadBase):
    pass

class ElegibilidadOut(ElegibilidadBase):
    id: int
    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: Asignacion (para visualización del horario)
# ==============================================================================
class AsignacionOut(BaseModel):
    id: int
    id_sesion: int
    id_horario: int
    estado: str
    puntaje_penalizacion: float
    # Datos expandidos para visualización
    docente_nombre: Optional[str] = None
    aula_codigo: Optional[str] = None
    franja_dia: Optional[str] = None
    franja_inicio: Optional[str] = None
    franja_fin: Optional[str] = None
    curso_nombre: Optional[str] = None
    grupo_nombre: Optional[str] = None

    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: Conflicto
# ==============================================================================
class ConflictoOut(BaseModel):
    id: int
    id_sesion: Optional[int]
    id_restriccion: str      # Ej: "RH-01", "RA-02"
    descripcion: str         # Descripción en lenguaje de dominio
    entidad_tipo: str
    entidad_id: Optional[int]

    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: Horario (resultado de la generación)
# ==============================================================================
class HorarioOut(BaseModel):
    id: int
    fecha_generacion: Optional[datetime]
    estado: str              # Valido / No_Factible / Borrador / Oficial
    puntaje_total: float
    es_oficial: bool
    asignaciones: List[AsignacionOut] = []
    conflictos: List[ConflictoOut] = []

    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMA: Solicitud de generación de horario
# ==============================================================================
class GenerarHorarioRequest(BaseModel):
    descripcion: Optional[str] = "Horario generado automáticamente"





class UsuarioCreate(BaseModel):
    nombre: str
    correo: str
    password: str
    rol: str = "Consulta"
    estado: bool = True


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    correo: str
    rol: str
    estado: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    correo: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioOut