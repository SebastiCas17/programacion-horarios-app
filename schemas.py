"""
schemas.py
==========
Esquemas Pydantic para validación de datos de entrada y serialización de respuestas.
"""

from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
import re


# ==============================================================================
# CONSTANTES DE VALIDACIÓN
# ==============================================================================

MAX_ESTUDIANTES_AULA = 40
MIN_INSCRITOS_GRUPO = 10
MAX_INSCRITOS_GRUPO = 40

TIPOS_VINCULACION = {"TC", "MT", "3/4T", "1/4T"}
ROLES_VALIDOS = {"Administrador", "Coordinador", "Consulta"}
DIAS_VALIDOS = {"Lunes", "Martes", "Miercoles", "Miércoles", "Jueves", "Viernes", "Sabado", "Sábado"}

REGEX_TEXTO_GENERAL = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 .,_\-]+$")
REGEX_NOMBRE_PERSONA = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ .'\-]+$")
REGEX_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REGEX_HORA = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def validar_texto_general(valor: str, campo: str, min_len: int = 2, max_len: int = 100) -> str:
    if valor is None:
        raise ValueError(f"{campo} es obligatorio.")

    valor = valor.strip()

    if len(valor) < min_len:
        raise ValueError(f"{campo} debe tener mínimo {min_len} caracteres.")

    if len(valor) > max_len:
        raise ValueError(f"{campo} no puede superar {max_len} caracteres.")

    if not REGEX_TEXTO_GENERAL.fullmatch(valor):
        raise ValueError(
            f"{campo} contiene caracteres no permitidos. Usa letras, números, espacios, guiones o puntos."
        )

    return valor


def validar_nombre_persona(valor: str, campo: str = "Nombre") -> str:
    if valor is None:
        raise ValueError(f"{campo} es obligatorio.")

    valor = valor.strip()

    if len(valor) < 2:
        raise ValueError(f"{campo} debe tener mínimo 2 caracteres.")

    if len(valor) > 100:
        raise ValueError(f"{campo} no puede superar 100 caracteres.")

    if not REGEX_NOMBRE_PERSONA.fullmatch(valor):
        raise ValueError(
            f"{campo} contiene caracteres no permitidos. No uses signos como @, #, $, %, *, /."
        )

    return valor


def validar_correo(valor: str) -> str:
    if valor is None:
        raise ValueError("El correo es obligatorio.")

    valor = valor.strip().lower()

    if not REGEX_CORREO.fullmatch(valor):
        raise ValueError("El correo no tiene un formato válido.")

    if len(valor) > 120:
        raise ValueError("El correo no puede superar 120 caracteres.")

    return valor


def validar_hora(valor: str, campo: str) -> str:
    if valor is None:
        raise ValueError(f"{campo} es obligatorio.")

    valor = valor.strip()

    if not REGEX_HORA.fullmatch(valor):
        raise ValueError(f"{campo} debe estar en formato militar HH:MM, por ejemplo 07:00 o 18:00.")

    return valor


def hora_a_minutos(hora: str) -> int:
    h, m = hora.split(":")
    return int(h) * 60 + int(m)


def validar_id_positivo(valor: int, campo: str) -> int:
    if valor is None or valor <= 0:
        raise ValueError(f"{campo} debe ser un ID válido mayor que cero.")

    return valor


# ==============================================================================
# SCHEMAS: Docente
# ==============================================================================
class DocenteBase(BaseModel):
    nombre: str
    correo: str
    tipo_vinculacion: str = "TC"
    estado: bool = True

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v):
        return validar_nombre_persona(v, "Nombre del docente")

    @field_validator("correo")
    @classmethod
    def validar_email_docente(cls, v):
        return validar_correo(v)

    @field_validator("tipo_vinculacion")
    @classmethod
    def validar_tipo(cls, v):
        if v not in TIPOS_VINCULACION:
            raise ValueError("El tipo de vinculación debe ser TC, MT, 3/4T o 1/4T.")
        return v


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

    @field_validator("nombre")
    @classmethod
    def validar_nombre_curso(cls, v):
        return validar_texto_general(v, "Nombre del curso", 2, 120)

    @field_validator("codigo")
    @classmethod
    def validar_codigo_curso(cls, v):
        return validar_texto_general(v, "Código del curso", 2, 30).upper()

    @field_validator("creditos")
    @classmethod
    def validar_creditos(cls, v):
        if v < 1 or v > 6:
            raise ValueError("Los créditos del curso deben estar entre 1 y 6.")
        return v

    @field_validator("sesiones_semana")
    @classmethod
    def validar_sesiones(cls, v):
        if v < 1 or v > 4:
            raise ValueError("Las sesiones por semana deben estar entre 1 y 4.")
        return v

    @field_validator("duracion_sesion_h")
    @classmethod
    def validar_duracion(cls, v):
        if v < 1 or v > 4:
            raise ValueError("La duración de la sesión debe estar entre 1 y 4 horas.")
        return v


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
    inscritos: int = 10
    estado: str = "Activo"

    @field_validator("id_curso")
    @classmethod
    def validar_id_curso(cls, v):
        return validar_id_positivo(v, "Curso")

    @field_validator("nombre_grupo")
    @classmethod
    def validar_nombre_grupo(cls, v):
        return validar_texto_general(v, "Nombre del grupo", 2, 50).upper()

    @field_validator("cupo_objetivo")
    @classmethod
    def validar_cupo(cls, v):
        if v < 1 or v > MAX_ESTUDIANTES_AULA:
            raise ValueError("El cupo objetivo del grupo debe estar entre 1 y 40 estudiantes.")
        return v

    @field_validator("inscritos")
    @classmethod
    def validar_inscritos(cls, v):
        if v < MIN_INSCRITOS_GRUPO:
            raise ValueError("No se puede registrar/programar un grupo con menos de 10 inscritos.")
        if v > MAX_INSCRITOS_GRUPO:
            raise ValueError("El número de inscritos no puede ser mayor a 40 estudiantes.")
        return v

    @field_validator("estado")
    @classmethod
    def validar_estado_grupo(cls, v):
        estados = {"Activo", "Cerrado", "Pendiente"}
        if v not in estados:
            raise ValueError("El estado del grupo debe ser Activo, Cerrado o Pendiente.")
        return v

    @model_validator(mode="after")
    def validar_inscritos_no_supera_cupo(self):
        if self.inscritos > self.cupo_objetivo:
            raise ValueError("El número de inscritos no puede superar el cupo objetivo del grupo.")
        return self


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

    @field_validator("codigo")
    @classmethod
    def validar_codigo_aula(cls, v):
        return validar_texto_general(v, "Código del aula", 1, 30).upper()

    @field_validator("capacidad")
    @classmethod
    def validar_capacidad(cls, v):
        if v < 1 or v > MAX_ESTUDIANTES_AULA:
            raise ValueError("La capacidad del aula debe estar entre 1 y 40 estudiantes.")
        return v

    @field_validator("edificio")
    @classmethod
    def validar_edificio(cls, v):
        if v is None or v.strip() == "":
            return None
        return validar_texto_general(v, "Edificio", 1, 60)


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
    dia_semana: str
    hora_inicio: str
    hora_fin: str
    bloqueada: bool = False

    @field_validator("dia_semana")
    @classmethod
    def validar_dia(cls, v):
        if v not in DIAS_VALIDOS:
            raise ValueError("El día debe ser Lunes, Martes, Miércoles, Jueves, Viernes o Sábado.")
        return v

    @field_validator("hora_inicio")
    @classmethod
    def validar_inicio(cls, v):
        return validar_hora(v, "Hora de inicio")

    @field_validator("hora_fin")
    @classmethod
    def validar_fin(cls, v):
        return validar_hora(v, "Hora de fin")

    @model_validator(mode="after")
    def validar_rango_horario(self):
        inicio = hora_a_minutos(self.hora_inicio)
        fin = hora_a_minutos(self.hora_fin)

        if inicio >= fin:
            raise ValueError("La hora de inicio debe ser menor que la hora de fin.")

        return self


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

    @field_validator("id_docente")
    @classmethod
    def validar_docente(cls, v):
        return validar_id_positivo(v, "Docente")

    @field_validator("id_franja")
    @classmethod
    def validar_franja(cls, v):
        return validar_id_positivo(v, "Franja")


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

    @field_validator("id_docente")
    @classmethod
    def validar_docente(cls, v):
        return validar_id_positivo(v, "Docente")

    @field_validator("id_curso")
    @classmethod
    def validar_curso(cls, v):
        return validar_id_positivo(v, "Curso")


class ElegibilidadCreate(ElegibilidadBase):
    pass


class ElegibilidadOut(ElegibilidadBase):
    id: int

    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: Asignacion
# ==============================================================================
class AsignacionOut(BaseModel):
    id: int
    id_sesion: int
    id_horario: int
    estado: str
    puntaje_penalizacion: float
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
    id_restriccion: str
    descripcion: str
    entidad_tipo: str
    entidad_id: Optional[int]

    class Config:
        from_attributes = True


# ==============================================================================
# SCHEMAS: Horario
# ==============================================================================
class HorarioOut(BaseModel):
    id: int
    fecha_generacion: Optional[datetime]
    estado: str
    puntaje_total: float
    es_oficial: bool
    asignaciones: List[AsignacionOut] = []
    conflictos: List[ConflictoOut] = []

    class Config:
        from_attributes = True


class GenerarHorarioRequest(BaseModel):
    descripcion: Optional[str] = "Horario generado automáticamente"


# ==============================================================================
# SCHEMA: Autenticación y usuarios
# ==============================================================================
class UsuarioCreate(BaseModel):
    nombre: str
    correo: str
    password: str
    rol: str = "Consulta"
    estado: bool = True

    @field_validator("nombre")
    @classmethod
    def validar_nombre_usuario(cls, v):
        return validar_nombre_persona(v, "Nombre del usuario")

    @field_validator("correo")
    @classmethod
    def validar_correo_usuario(cls, v):
        return validar_correo(v)

    @field_validator("password")
    @classmethod
    def validar_password(cls, v):
        if v is None or len(v.strip()) < 6:
            raise ValueError("La contraseña debe tener mínimo 6 caracteres.")
        if len(v) > 80:
            raise ValueError("La contraseña no puede superar 80 caracteres.")
        return v

    @field_validator("rol")
    @classmethod
    def validar_rol(cls, v):
        if v not in ROLES_VALIDOS:
            raise ValueError("El rol debe ser Administrador, Coordinador o Consulta.")
        return v


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

    @field_validator("correo")
    @classmethod
    def validar_correo_login(cls, v):
        return validar_correo(v)

    @field_validator("password")
    @classmethod
    def validar_password_login(cls, v):
        if v is None or not v.strip():
            raise ValueError("La contraseña es obligatoria.")
        return v


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioOut


# ==============================================================================
# SCHEMAS: ParametroSemestre
# ==============================================================================
class ParametroSemestreBase(BaseModel):
    nombre: str = "2026-1"
    hora_inicio_lv: str = "07:00"
    hora_fin_lv: str = "22:00"
    hora_inicio_sab: str = "07:00"
    hora_fin_sab: str = "13:00"
    inicio_almuerzo: str = "12:00"
    fin_almuerzo: str = "13:00"
    max_sesiones_semana: int = 4
    min_inscritos_cierre: int = 10
    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def validar_nombre_semestre(cls, v):
        return validar_texto_general(v, "Nombre del semestre", 3, 30)

    @field_validator("hora_inicio_lv")
    @classmethod
    def validar_hora_inicio_lv(cls, v):
        return validar_hora(v, "Hora inicio lunes a viernes")

    @field_validator("hora_fin_lv")
    @classmethod
    def validar_hora_fin_lv(cls, v):
        return validar_hora(v, "Hora fin lunes a viernes")

    @field_validator("hora_inicio_sab")
    @classmethod
    def validar_hora_inicio_sab(cls, v):
        return validar_hora(v, "Hora inicio sábado")

    @field_validator("hora_fin_sab")
    @classmethod
    def validar_hora_fin_sab(cls, v):
        return validar_hora(v, "Hora fin sábado")

    @field_validator("inicio_almuerzo")
    @classmethod
    def validar_inicio_almuerzo(cls, v):
        return validar_hora(v, "Inicio del almuerzo")

    @field_validator("fin_almuerzo")
    @classmethod
    def validar_fin_almuerzo(cls, v):
        return validar_hora(v, "Fin del almuerzo")

    @field_validator("max_sesiones_semana")
    @classmethod
    def validar_max_sesiones(cls, v):
        if v < 1 or v > 4:
            raise ValueError("El máximo de sesiones por semana debe estar entre 1 y 4.")
        return v

    @field_validator("min_inscritos_cierre")
    @classmethod
    def validar_min_cierre(cls, v):
        if v < 10 or v > 40:
            raise ValueError("El mínimo de inscritos para cierre debe estar entre 10 y 40.")
        return v

    @model_validator(mode="after")
    def validar_rangos_parametros(self):
        if hora_a_minutos(self.hora_inicio_lv) >= hora_a_minutos(self.hora_fin_lv):
            raise ValueError("La hora inicio lunes a viernes debe ser menor que la hora fin lunes a viernes.")

        if hora_a_minutos(self.hora_inicio_sab) >= hora_a_minutos(self.hora_fin_sab):
            raise ValueError("La hora inicio sábado debe ser menor que la hora fin sábado.")

        if hora_a_minutos(self.inicio_almuerzo) >= hora_a_minutos(self.fin_almuerzo):
            raise ValueError("El inicio del almuerzo debe ser menor que el fin del almuerzo.")

        return self


class ParametroSemestreCreate(ParametroSemestreBase):
    pass


class ParametroSemestreOut(ParametroSemestreBase):
    id: int

    class Config:
        from_attributes = True