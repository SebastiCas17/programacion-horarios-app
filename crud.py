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

def preparar_sesiones_para_motor(db: Session):
    """
    Crea o actualiza las sesiones reales que el motor debe programar.
    Cada grupo activo genera tantas sesiones como indique el curso.
    No borra sesiones históricas para evitar romper asignaciones ya guardadas.
    """
    grupos = db.query(models.Grupo).all()
    cursos_por_id = {c.id: c for c in db.query(models.Curso).all()}

    sesiones_motor = []

    for grupo in grupos:
        if grupo.estado == "Cerrado":
            continue

        curso = cursos_por_id.get(grupo.id_curso)

        if not curso or not curso.estado:
            continue

        sesiones_existentes = db.query(models.SesionClase).filter(
            models.SesionClase.id_grupo == grupo.id
        ).all()

        sesiones_por_numero = {
            s.numero_sesion: s for s in sesiones_existentes
        }

        for numero in range(1, curso.sesiones_semana + 1):
            if numero in sesiones_por_numero:
                sesion = sesiones_por_numero[numero]
                sesion.estado = "Pendiente"
            else:
                sesion = models.SesionClase(
                    id_grupo=grupo.id,
                    numero_sesion=numero,
                    estado="Pendiente"
                )
                db.add(sesion)

            sesiones_motor.append(sesion)

    db.commit()

    for sesion in sesiones_motor:
        db.refresh(sesion)

    return sesiones_motor


def get_sesiones_motor(db: Session):
    """
    Retorna las sesiones reales que pueden ser usadas por el motor.
    """
    return db.query(models.SesionClase).join(
        models.Grupo,
        models.SesionClase.id_grupo == models.Grupo.id
    ).join(
        models.Curso,
        models.Grupo.id_curso == models.Curso.id
    ).filter(
        models.Grupo.estado != "Cerrado",
        models.Curso.estado == True
    ).all()


def actualizar_estado_sesion(db: Session, sesion_id: int, estado: str):
    """
    Cambia el estado de una sesión: Pendiente / Asignada / Conflicto.
    """
    sesion = db.query(models.SesionClase).filter(
        models.SesionClase.id == sesion_id
    ).first()

    if sesion:
        sesion.estado = estado
        db.commit()
        db.refresh(sesion)

    return sesion


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
    Incluye sesiones reales persistidas en la base de datos.
    """
    return {
        "docentes": get_docentes(db),
        "cursos": get_cursos(db),
        "grupos": get_grupos(db),
        "aulas": get_aulas(db),
        "franjas": get_franjas(db),
        "disponibilidades": get_disponibilidades(db),
        "elegibilidades": get_elegibilidades(db),
        "sesiones": get_sesiones_motor(db),
        "parametro_semestre": obtener_o_crear_parametro_activo(db)
    }


# ==============================================================================
# CRUD: Usuario (para autenticación y gestión de cuentas)
# ==============================================================================


from auth import generar_hash_password


def get_usuario_por_correo(db: Session, correo: str):
    return db.query(models.Usuario).filter(models.Usuario.correo == correo).first()


def create_usuario(db: Session, usuario: schemas.UsuarioCreate):
    db_usuario = models.Usuario(
        nombre=usuario.nombre,
        correo=usuario.correo,
        password_hash=generar_hash_password(usuario.password),
        rol=usuario.rol,
        estado=usuario.estado
    )

    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def get_usuarios(db: Session):
    return db.query(models.Usuario).all()

# ==============================================================================
# CRUD: ParametroSemestre
# ==============================================================================
def get_parametros_semestre(db: Session):
    return db.query(models.ParametroSemestre).all()


def get_parametro_activo(db: Session):
    return db.query(models.ParametroSemestre).filter(
        models.ParametroSemestre.activo == True
    ).first()


def obtener_o_crear_parametro_activo(db: Session):
    parametro = get_parametro_activo(db)

    if parametro:
        return parametro

    parametro = models.ParametroSemestre(
        nombre="2026-1",
        hora_inicio_lv="07:00",
        hora_fin_lv="22:00",
        hora_inicio_sab="07:00",
        hora_fin_sab="13:00",
        inicio_almuerzo="12:00",
        fin_almuerzo="13:00",
        max_sesiones_semana=4,
        min_inscritos_cierre=10,
        activo=True
    )

    db.add(parametro)
    db.commit()
    db.refresh(parametro)

    return parametro


def create_parametro_semestre(db: Session, parametro: schemas.ParametroSemestreCreate):
    """
    Crea o actualiza los parámetros del semestre.
    Si ya existe un semestre activo o uno con el mismo nombre, lo actualiza.
    Esto evita errores por nombre duplicado.
    """

    # Buscar si ya existe un parámetro con el mismo nombre
    existente = db.query(models.ParametroSemestre).filter(
        models.ParametroSemestre.nombre == parametro.nombre
    ).first()

    # Si no existe por nombre, buscar el activo
    if not existente:
        existente = get_parametro_activo(db)

    # Si existe, actualizarlo
    if existente:
        existente.nombre = parametro.nombre
        existente.hora_inicio_lv = parametro.hora_inicio_lv
        existente.hora_fin_lv = parametro.hora_fin_lv
        existente.hora_inicio_sab = parametro.hora_inicio_sab
        existente.hora_fin_sab = parametro.hora_fin_sab
        existente.inicio_almuerzo = parametro.inicio_almuerzo
        existente.fin_almuerzo = parametro.fin_almuerzo
        existente.max_sesiones_semana = parametro.max_sesiones_semana
        existente.min_inscritos_cierre = parametro.min_inscritos_cierre
        existente.activo = parametro.activo

        if parametro.activo:
            db.query(models.ParametroSemestre).filter(
                models.ParametroSemestre.id != existente.id
            ).update({"activo": False})

        db.commit()
        db.refresh(existente)
        return existente

    # Si no existe ninguno, crear uno nuevo
    if parametro.activo:
        db.query(models.ParametroSemestre).update({"activo": False})
        db.commit()

    db_parametro = models.ParametroSemestre(**parametro.model_dump())

    db.add(db_parametro)
    db.commit()
    db.refresh(db_parametro)

    return db_parametro