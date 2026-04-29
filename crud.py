"""
crud.py
=======
Operaciones CRUD (Create, Read, Update, Delete) sobre la base de datos.
Implementa el patrón Repository: la capa de negocio no conoce SQLAlchemy directamente.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
import models, schemas


# ==============================================================================
# CRUD: Docente
# ==============================================================================
def get_docentes(db: Session):
    """Retorna todos los docentes activos."""
    return db.query(models.Docente).filter(models.Docente.estado == True).all()

def get_docente(db: Session, docente_id: int):
    return db.query(models.Docente).filter(models.Docente.id == docente_id).first()

def create_docente(db: Session, docente: schemas.DocenteCreate):
    db_docente = models.Docente(**docente.model_dump())
    db.add(db_docente)
    db.commit()
    db.refresh(db_docente)
    return db_docente

def delete_docente(db: Session, docente_id: int):
    """Elimina docente y su disponibilidad/elegibilidad en cascada."""
    db_docente = db.query(models.Docente).filter(models.Docente.id == docente_id).first()
    if db_docente:
        db.delete(db_docente)
        db.commit()
    return db_docente


# ==============================================================================
# CRUD: Curso
# ==============================================================================
def get_cursos(db: Session):
    return db.query(models.Curso).filter(models.Curso.estado == True).all()

def get_curso(db: Session, curso_id: int):
    return db.query(models.Curso).filter(models.Curso.id == curso_id).first()

def create_curso(db: Session, curso: schemas.CursoCreate):
    db_curso = models.Curso(**curso.model_dump())
    db.add(db_curso)
    db.commit()
    db.refresh(db_curso)
    return db_curso

def delete_curso(db: Session, curso_id: int):
    db_curso = db.query(models.Curso).filter(models.Curso.id == curso_id).first()
    if db_curso:
        db.delete(db_curso)
        db.commit()
    return db_curso


# ==============================================================================
# CRUD: Grupo
# ==============================================================================
def get_grupos(db: Session):
    return db.query(models.Grupo).all()

def get_grupo(db: Session, grupo_id: int):
    return db.query(models.Grupo).filter(models.Grupo.id == grupo_id).first()

def create_grupo(db: Session, grupo: schemas.GrupoCreate):
    db_grupo = models.Grupo(**grupo.model_dump())
    db.add(db_grupo)
    db.commit()
    db.refresh(db_grupo)
    return db_grupo

def delete_grupo(db: Session, grupo_id: int):
    db_grupo = db.query(models.Grupo).filter(models.Grupo.id == grupo_id).first()
    if db_grupo:
        db.delete(db_grupo)
        db.commit()
    return db_grupo


# ==============================================================================
# CRUD: Aula
# ==============================================================================
def get_aulas(db: Session):
    return db.query(models.Aula).filter(models.Aula.estado == True).all()

def get_aula(db: Session, aula_id: int):
    return db.query(models.Aula).filter(models.Aula.id == aula_id).first()

def create_aula(db: Session, aula: schemas.AulaCreate):
    db_aula = models.Aula(**aula.model_dump())
    db.add(db_aula)
    db.commit()
    db.refresh(db_aula)
    return db_aula

def delete_aula(db: Session, aula_id: int):
    db_aula = db.query(models.Aula).filter(models.Aula.id == aula_id).first()
    if db_aula:
        db.delete(db_aula)
        db.commit()
    return db_aula


# ==============================================================================
# CRUD: FranjaHoraria
# ==============================================================================
def get_franjas(db: Session):
    return db.query(models.FranjaHoraria).all()

def get_franja(db: Session, franja_id: int):
    return db.query(models.FranjaHoraria).filter(models.FranjaHoraria.id == franja_id).first()

def create_franja(db: Session, franja: schemas.FranjaCreate):
    db_franja = models.FranjaHoraria(**franja.model_dump())
    db.add(db_franja)
    db.commit()
    db.refresh(db_franja)
    return db_franja

def delete_franja(db: Session, franja_id: int):
    db_franja = db.query(models.FranjaHoraria).filter(models.FranjaHoraria.id == franja_id).first()
    if db_franja:
        db.delete(db_franja)
        db.commit()
    return db_franja


# ==============================================================================
# CRUD: DisponibilidadDocente
# ==============================================================================
def get_disponibilidades(db: Session):
    return db.query(models.DisponibilidadDocente).all()

def get_disponibilidades_docente(db: Session, docente_id: int):
    """Retorna las franjas disponibles para un docente específico."""
    return db.query(models.DisponibilidadDocente).filter(
        models.DisponibilidadDocente.id_docente == docente_id
    ).all()

def create_disponibilidad(db: Session, disp: schemas.DisponibilidadCreate):
    # Verificar que no exista duplicado
    existente = db.query(models.DisponibilidadDocente).filter(
        and_(
            models.DisponibilidadDocente.id_docente == disp.id_docente,
            models.DisponibilidadDocente.id_franja == disp.id_franja
        )
    ).first()
    if existente:
        return existente  # Ya existe, retornar el existente
    db_disp = models.DisponibilidadDocente(**disp.model_dump())
    db.add(db_disp)
    db.commit()
    db.refresh(db_disp)
    return db_disp

def delete_disponibilidad(db: Session, disp_id: int):
    db_disp = db.query(models.DisponibilidadDocente).filter(
        models.DisponibilidadDocente.id == disp_id
    ).first()
    if db_disp:
        db.delete(db_disp)
        db.commit()
    return db_disp


# ==============================================================================
# CRUD: ElegibilidadDocente
# ==============================================================================
def get_elegibilidades(db: Session):
    return db.query(models.ElegibilidadDocente).filter(
        models.ElegibilidadDocente.activo == True
    ).all()

def create_elegibilidad(db: Session, eleg: schemas.ElegibilidadCreate):
    # Verificar que no exista duplicado
    existente = db.query(models.ElegibilidadDocente).filter(
        and_(
            models.ElegibilidadDocente.id_docente == eleg.id_docente,
            models.ElegibilidadDocente.id_curso == eleg.id_curso
        )
    ).first()
    if existente:
        existente.activo = True
        db.commit()
        return existente
    db_eleg = models.ElegibilidadDocente(**eleg.model_dump())
    db.add(db_eleg)
    db.commit()
    db.refresh(db_eleg)
    return db_eleg

def delete_elegibilidad(db: Session, eleg_id: int):
    db_eleg = db.query(models.ElegibilidadDocente).filter(
        models.ElegibilidadDocente.id == eleg_id
    ).first()
    if db_eleg:
        db.delete(db_eleg)
        db.commit()
    return db_eleg


# ==============================================================================
# CRUD: SesionClase
# Normalmente las sesiones se crean automáticamente por el motor
# ==============================================================================
def create_sesiones_para_grupo(db: Session, grupo_id: int, num_sesiones: int):
    """
    Crea automáticamente las sesiones de clase para un grupo.
    Se llama antes de ejecutar el motor de horarios.
    """
    # Eliminar sesiones previas si existen
    db.query(models.SesionClase).filter(
        models.SesionClase.id_grupo == grupo_id
    ).delete()
    db.commit()

    sesiones = []
    for i in range(1, num_sesiones + 1):
        sesion = models.SesionClase(
            id_grupo=grupo_id,
            numero_sesion=i,
            estado="Pendiente"
        )
        db.add(sesion)
        sesiones.append(sesion)
    db.commit()
    for s in sesiones:
        db.refresh(s)
    return sesiones


# ==============================================================================
# CRUD: Horario
# ==============================================================================
def get_horarios(db: Session):
    return db.query(models.Horario).order_by(models.Horario.fecha_generacion.desc()).all()

def get_horario(db: Session, horario_id: int):
    return db.query(models.Horario).filter(models.Horario.id == horario_id).first()

def get_ultimo_horario(db: Session):
    """Retorna el horario más reciente generado."""
    return db.query(models.Horario).order_by(
        models.Horario.fecha_generacion.desc()
    ).first()

def create_horario(db: Session):
    """Crea un nuevo registro de horario en estado Borrador."""
    horario = models.Horario(estado="Borrador", puntaje_total=0.0)
    db.add(horario)
    db.commit()
    db.refresh(horario)
    return horario

def update_horario_estado(db: Session, horario_id: int, estado: str, puntaje: float = 0.0):
    horario = db.query(models.Horario).filter(models.Horario.id == horario_id).first()
    if horario:
        horario.estado = estado
        horario.puntaje_total = puntaje
        db.commit()
        db.refresh(horario)
    return horario

def publicar_horario(db: Session, horario_id: int):
    """Marca el horario como oficial e inmutable (RH-14)."""
    horario = db.query(models.Horario).filter(models.Horario.id == horario_id).first()
    if horario and horario.estado == "Valido":
        horario.es_oficial = True
        horario.estado = "Oficial"
        db.commit()
        db.refresh(horario)
    return horario

def delete_horario(db: Session, horario_id: int):
    """Elimina un horario (solo si no es oficial)."""
    horario = db.query(models.Horario).filter(models.Horario.id == horario_id).first()
    if horario and not horario.es_oficial:
        db.delete(horario)
        db.commit()
    return horario


# ==============================================================================
# CONSULTAS para el Motor de Horarios
# ==============================================================================
def get_todos_los_datos(db: Session):
    """
    Carga todos los datos necesarios para el motor de horarios en memoria.
    Patrón Singleton aplicado: se carga una vez y se pasa a todos los módulos del motor.
    """
    return {
        "docentes": get_docentes(db),
        "cursos": get_cursos(db),
        "grupos": get_grupos(db),
        "aulas": get_aulas(db),
        "franjas": db.query(models.FranjaHoraria).filter(
            models.FranjaHoraria.bloqueada == False
        ).all(),
        "disponibilidades": get_disponibilidades(db),
        "elegibilidades": get_elegibilidades(db),
    }
