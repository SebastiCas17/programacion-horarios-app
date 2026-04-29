"""
models.py
=========
Modelos ORM que mapean directamente al modelo Entidad-Relación del documento de diseño.
Entidades: Docente, Curso, Grupo, Aula, FranjaHoraria, DisponibilidadDocente,
           ElegibilidadDocente, SesionClase, Asignacion, Horario, Conflicto
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    Float, DateTime, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(30), nullable=False, default="Consulta")
    estado = Column(Boolean, default=True)

# ==============================================================================
# ENTIDAD: Docente
# Representa a un profesor que puede dictar clases en el semestre
# ==============================================================================
class Docente(Base):
    __tablename__ = "docentes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    correo = Column(String(150), unique=True, nullable=False)
    # TC=Tiempo Completo, 3/4T=Tres Cuartos, MT=Medio Tiempo, 1/4T=Un Cuarto
    tipo_vinculacion = Column(String(30), nullable=False, default="TC")
    estado = Column(Boolean, default=True)  # True = activo en el semestre

    # Relaciones
    disponibilidades = relationship("DisponibilidadDocente", back_populates="docente", cascade="all, delete-orphan")
    elegibilidades = relationship("ElegibilidadDocente", back_populates="docente", cascade="all, delete-orphan")
    asignaciones = relationship("Asignacion", back_populates="docente")


# ==============================================================================
# ENTIDAD: Curso
# Unidad académica con número de sesiones semanales requeridas
# ==============================================================================
class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    codigo = Column(String(20), unique=True, nullable=False)
    creditos = Column(Integer, default=3)
    sesiones_semana = Column(Integer, default=2)   # Cuántas veces se dicta por semana
    duracion_sesion_h = Column(Integer, default=2)  # Duración fija: 2 horas (RH-12)
    requiere_computadores = Column(Boolean, default=False)  # Restricción RH-07
    requiere_sillas_moviles = Column(Boolean, default=False)
    estado = Column(Boolean, default=True)

    # Relaciones
    grupos = relationship("Grupo", back_populates="curso")
    elegibilidades = relationship("ElegibilidadDocente", back_populates="curso")


# ==============================================================================
# ENTIDAD: Grupo
# Sección de estudiantes inscritos en un curso específico
# ==============================================================================
class Grupo(Base):
    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True, index=True)
    id_curso = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    nombre_grupo = Column(String(20), nullable=False)  # Ej: IS2-01
    cupo_objetivo = Column(Integer, default=40)
    inscritos = Column(Integer, default=0)
    # Estado: Activo / Candidato_Cierre / Cerrado
    estado = Column(String(20), default="Activo")

    # Relaciones
    curso = relationship("Curso", back_populates="grupos")
    sesiones = relationship("SesionClase", back_populates="grupo", cascade="all, delete-orphan")


# ==============================================================================
# ENTIDAD: Aula
# Espacio físico con capacidad y recursos disponibles
# ==============================================================================
class Aula(Base):
    __tablename__ = "aulas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), unique=True, nullable=False)  # Ej: A-201
    capacidad = Column(Integer, nullable=False)
    tiene_computadores = Column(Boolean, default=False)
    tiene_sillas_moviles = Column(Boolean, default=False)
    edificio = Column(String(50), nullable=True)
    estado = Column(Boolean, default=True)  # True = disponible para asignación

    # Relaciones
    asignaciones = relationship("Asignacion", back_populates="aula")


# ==============================================================================
# ENTIDAD: FranjaHoraria
# Bloque de tiempo en el que se puede programar una sesión
# ==============================================================================
class FranjaHoraria(Base):
    __tablename__ = "franjas_horarias"

    id = Column(Integer, primary_key=True, index=True)
    # Días: Lunes, Martes, Miercoles, Jueves, Viernes, Sabado
    dia_semana = Column(String(10), nullable=False)
    hora_inicio = Column(String(5), nullable=False)  # Formato "HH:MM"
    hora_fin = Column(String(5), nullable=False)     # Formato "HH:MM"
    bloqueada = Column(Boolean, default=False)       # True = franja de almuerzo u otro bloqueo (RH-05)

    # Relaciones
    asignaciones = relationship("Asignacion", back_populates="franja")
    disponibilidades = relationship("DisponibilidadDocente", back_populates="franja")


# ==============================================================================
# ENTIDAD: DisponibilidadDocente
# Registro de en qué franjas horarias puede trabajar un docente (RH-01)
# ==============================================================================
class DisponibilidadDocente(Base):
    __tablename__ = "disponibilidad_docente"

    id = Column(Integer, primary_key=True, index=True)
    id_docente = Column(Integer, ForeignKey("docentes.id"), nullable=False)
    id_franja = Column(Integer, ForeignKey("franjas_horarias.id"), nullable=False)

    # Relaciones
    docente = relationship("Docente", back_populates="disponibilidades")
    franja = relationship("FranjaHoraria", back_populates="disponibilidades")


# ==============================================================================
# ENTIDAD: ElegibilidadDocente
# Relación N:M entre Docente y Curso — qué docente puede dictar qué curso (RH-02)
# ==============================================================================
class ElegibilidadDocente(Base):
    __tablename__ = "elegibilidad_docente"

    id = Column(Integer, primary_key=True, index=True)
    id_docente = Column(Integer, ForeignKey("docentes.id"), nullable=False)
    id_curso = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    activo = Column(Boolean, default=True)

    # Relaciones
    docente = relationship("Docente", back_populates="elegibilidades")
    curso = relationship("Curso", back_populates="elegibilidades")


# ==============================================================================
# ENTIDAD: ParametroSemestre
# Configuración institucional del semestre activo
# ==============================================================================
class ParametroSemestre(Base):
    __tablename__ = "parametros_semestre"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(20), unique=True, nullable=False, default="2026-1")

    # Rango académico Lun-Vie
    hora_inicio_lv = Column(String(5), nullable=False, default="07:00")
    hora_fin_lv = Column(String(5), nullable=False, default="22:00")

    # Rango académico sábado
    hora_inicio_sab = Column(String(5), nullable=False, default="07:00")
    hora_fin_sab = Column(String(5), nullable=False, default="13:00")

    # Franja bloqueada de almuerzo
    inicio_almuerzo = Column(String(5), nullable=False, default="12:00")
    fin_almuerzo = Column(String(5), nullable=False, default="13:00")

    # Reglas parametrizables
    max_sesiones_semana = Column(Integer, nullable=False, default=4)
    min_inscritos_cierre = Column(Integer, nullable=False, default=10)

    activo = Column(Boolean, nullable=False, default=True)


# ==============================================================================
# ENTIDAD: SesionClase
# Unidad de asignación del motor. Un grupo genera tantas sesiones como
# indique sesiones_semana del curso
# ==============================================================================
class SesionClase(Base):
    __tablename__ = "sesiones_clase"

    id = Column(Integer, primary_key=True, index=True)
    id_grupo = Column(Integer, ForeignKey("grupos.id"), nullable=False)
    numero_sesion = Column(Integer, nullable=False)  # 1, 2, 3... dentro de la semana
    # Estado: Pendiente / Asignada / Conflicto
    estado = Column(String(20), default="Pendiente")

    # Relaciones
    grupo = relationship("Grupo", back_populates="sesiones")
    asignacion = relationship("Asignacion", back_populates="sesion", uselist=False)


# ==============================================================================
# ENTIDAD: Horario
# Contenedor de todas las asignaciones de un intento de generación
# ==============================================================================
class Horario(Base):
    __tablename__ = "horarios"

    id = Column(Integer, primary_key=True, index=True)
    fecha_generacion = Column(DateTime, server_default=func.now())
    # Estado: Borrador / Valido / No_Factible / Oficial
    estado = Column(String(20), default="Borrador")
    puntaje_total = Column(Float, default=0.0)  # Penalización total por restricciones blandas
    es_oficial = Column(Boolean, default=False)  # True = publicado como oficial (RH-14)

    # Relaciones
    asignaciones = relationship("Asignacion", back_populates="horario", cascade="all, delete-orphan")
    conflictos = relationship("Conflicto", back_populates="horario", cascade="all, delete-orphan")


# ==============================================================================
# ENTIDAD: Asignacion
# Producto del motor: sesión + docente + aula + franja asignados
# ==============================================================================
class Asignacion(Base):
    __tablename__ = "asignaciones"

    id = Column(Integer, primary_key=True, index=True)
    id_sesion = Column(Integer, ForeignKey("sesiones_clase.id"), nullable=False)
    id_docente = Column(Integer, ForeignKey("docentes.id"), nullable=False)
    id_aula = Column(Integer, ForeignKey("aulas.id"), nullable=False)
    id_franja = Column(Integer, ForeignKey("franjas_horarias.id"), nullable=False)
    id_horario = Column(Integer, ForeignKey("horarios.id"), nullable=False)
    # Estado: Tentativa / Valida / Conflicto
    estado = Column(String(30), default="Valida")
    puntaje_penalizacion = Column(Float, default=0.0)  # Penalización por restricciones blandas

    # Relaciones
    sesion = relationship("SesionClase", back_populates="asignacion")
    docente = relationship("Docente", back_populates="asignaciones")
    aula = relationship("Aula", back_populates="asignaciones")
    franja = relationship("FranjaHoraria", back_populates="asignaciones")
    horario = relationship("Horario", back_populates="asignaciones")


# ==============================================================================
# ENTIDAD: Conflicto
# Registra sesiones que no pudieron ser asignadas, con el ID de la restricción violada
# Implementa RNF-08 (Trazabilidad)
# ==============================================================================
class Conflicto(Base):
    __tablename__ = "conflictos"

    id = Column(Integer, primary_key=True, index=True)
    id_horario = Column(Integer, ForeignKey("horarios.id"), nullable=False)
    id_sesion = Column(Integer, ForeignKey("sesiones_clase.id"), nullable=True)
    # ID de la restricción violada: RH-01, RA-02, etc. (RNF-08)
    id_restriccion = Column(String(10), nullable=False)
    # Descripción en lenguaje de dominio, no técnico (RNF-07)
    descripcion = Column(Text, nullable=False)
    entidad_tipo = Column(String(20), nullable=False)  # Docente / Aula / Grupo / Franja
    entidad_id = Column(Integer, nullable=True)
    timestamp_registro = Column(DateTime, server_default=func.now())

    # Relaciones
    horario = relationship("Horario", back_populates="conflictos")
