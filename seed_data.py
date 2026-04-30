"""
seed_data.py
============
Carga de datos académicos iniciales para pruebas del sistema.

Este archivo es idempotente:
- Si el dato ya existe, no lo duplica.
- Si no existe, lo crea.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_

import models
import crud


def _get_or_create_docente(db: Session, nombre: str, correo: str, tipo_vinculacion: str):
    docente = db.query(models.Docente).filter(models.Docente.correo == correo).first()

    if docente:
        return docente, False

    docente = models.Docente(
        nombre=nombre,
        correo=correo,
        tipo_vinculacion=tipo_vinculacion,
        estado=True
    )

    db.add(docente)
    db.flush()

    return docente, True


def _get_or_create_curso(
    db: Session,
    nombre: str,
    codigo: str,
    creditos: int,
    sesiones_semana: int,
    requiere_computadores: bool = False,
    requiere_sillas_moviles: bool = False
):
    curso = db.query(models.Curso).filter(models.Curso.codigo == codigo).first()

    if curso:
        return curso, False

    curso = models.Curso(
        nombre=nombre,
        codigo=codigo,
        creditos=creditos,
        sesiones_semana=sesiones_semana,
        duracion_sesion_h=2,
        requiere_computadores=requiere_computadores,
        requiere_sillas_moviles=requiere_sillas_moviles,
        estado=True
    )

    db.add(curso)
    db.flush()

    return curso, True


def _get_or_create_grupo(
    db: Session,
    curso: models.Curso,
    nombre_grupo: str,
    cupo_objetivo: int,
    inscritos: int
):
    grupo = db.query(models.Grupo).filter(
        and_(
            models.Grupo.id_curso == curso.id,
            models.Grupo.nombre_grupo == nombre_grupo
        )
    ).first()

    if grupo:
        return grupo, False

    grupo = models.Grupo(
        id_curso=curso.id,
        nombre_grupo=nombre_grupo,
        cupo_objetivo=cupo_objetivo,
        inscritos=inscritos,
        estado="Activo"
    )

    db.add(grupo)
    db.flush()

    return grupo, True


def _get_or_create_aula(
    db: Session,
    codigo: str,
    capacidad: int,
    edificio: str,
    tiene_computadores: bool = False,
    tiene_sillas_moviles: bool = False
):
    aula = db.query(models.Aula).filter(models.Aula.codigo == codigo).first()

    if aula:
        return aula, False

    aula = models.Aula(
        codigo=codigo,
        capacidad=capacidad,
        edificio=edificio,
        tiene_computadores=tiene_computadores,
        tiene_sillas_moviles=tiene_sillas_moviles,
        estado=True
    )

    db.add(aula)
    db.flush()

    return aula, True


def _get_or_create_franja(
    db: Session,
    dia_semana: str,
    hora_inicio: str,
    hora_fin: str,
    bloqueada: bool = False
):
    franja = db.query(models.FranjaHoraria).filter(
        and_(
            models.FranjaHoraria.dia_semana == dia_semana,
            models.FranjaHoraria.hora_inicio == hora_inicio,
            models.FranjaHoraria.hora_fin == hora_fin
        )
    ).first()

    if franja:
        return franja, False

    franja = models.FranjaHoraria(
        dia_semana=dia_semana,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        bloqueada=bloqueada
    )

    db.add(franja)
    db.flush()

    return franja, True


def _get_or_create_elegibilidad(db: Session, docente_id: int, curso_id: int):
    elegibilidad = db.query(models.ElegibilidadDocente).filter(
        and_(
            models.ElegibilidadDocente.id_docente == docente_id,
            models.ElegibilidadDocente.id_curso == curso_id
        )
    ).first()

    if elegibilidad:
        elegibilidad.activo = True
        return elegibilidad, False

    elegibilidad = models.ElegibilidadDocente(
        id_docente=docente_id,
        id_curso=curso_id,
        activo=True
    )

    db.add(elegibilidad)
    db.flush()

    return elegibilidad, True


def _get_or_create_disponibilidad(db: Session, docente_id: int, franja_id: int):
    disponibilidad = db.query(models.DisponibilidadDocente).filter(
        and_(
            models.DisponibilidadDocente.id_docente == docente_id,
            models.DisponibilidadDocente.id_franja == franja_id
        )
    ).first()

    if disponibilidad:
        return disponibilidad, False

    disponibilidad = models.DisponibilidadDocente(
        id_docente=docente_id,
        id_franja=franja_id
    )

    db.add(disponibilidad)
    db.flush()

    return disponibilidad, True


def cargar_datos_academicos_iniciales(db: Session):
    """
    Carga datos suficientes para probar:
    - login
    - docentes
    - cursos
    - grupos
    - aulas
    - franjas
    - disponibilidad
    - elegibilidad
    - motor de backtracking
    - generación de horario válido
    """

    creados = {
        "docentes": 0,
        "cursos": 0,
        "grupos": 0,
        "aulas": 0,
        "franjas": 0,
        "elegibilidades": 0,
        "disponibilidades": 0,
        "sesiones": 0
    }

    # Parámetro semestre activo
    parametro = crud.obtener_o_crear_parametro_activo(db)
    parametro.nombre = "2026-1"
    parametro.hora_inicio_lv = "07:00"
    parametro.hora_fin_lv = "22:00"
    parametro.hora_inicio_sab = "07:00"
    parametro.hora_fin_sab = "13:00"
    parametro.inicio_almuerzo = "12:00"
    parametro.fin_almuerzo = "13:00"
    parametro.max_sesiones_semana = 4
    parametro.min_inscritos_cierre = 10
    parametro.activo = True

    # Docentes
    ana, nuevo = _get_or_create_docente(
        db, "Ana Torres", "ana.torres@unbosque.edu.co", "TC"
    )
    creados["docentes"] += int(nuevo)

    carlos, nuevo = _get_or_create_docente(
        db, "Carlos Méndez", "carlos.mendez@unbosque.edu.co", "MT"
    )
    creados["docentes"] += int(nuevo)

    laura, nuevo = _get_or_create_docente(
        db, "Laura Gómez", "laura.gomez@unbosque.edu.co", "TC"
    )
    creados["docentes"] += int(nuevo)

    # Cursos
    calculo, nuevo = _get_or_create_curso(
        db, "Cálculo Diferencial", "CAL101", 4, 2
    )
    creados["cursos"] += int(nuevo)

    programacion, nuevo = _get_or_create_curso(
        db, "Programación I", "SIS101", 3, 2, requiere_computadores=True
    )
    creados["cursos"] += int(nuevo)

    bases, nuevo = _get_or_create_curso(
        db, "Bases de Datos", "SIS201", 3, 2, requiere_computadores=True
    )
    creados["cursos"] += int(nuevo)

    etica, nuevo = _get_or_create_curso(
        db, "Ética Profesional", "HUM101", 2, 1
    )
    creados["cursos"] += int(nuevo)

    # Grupos
    _, nuevo = _get_or_create_grupo(db, calculo, "CAL-01", 35, 30)
    creados["grupos"] += int(nuevo)

    _, nuevo = _get_or_create_grupo(db, programacion, "PROG-01", 30, 25)
    creados["grupos"] += int(nuevo)

    _, nuevo = _get_or_create_grupo(db, bases, "BD-01", 28, 22)
    creados["grupos"] += int(nuevo)

    _, nuevo = _get_or_create_grupo(db, etica, "ETI-01", 30, 18)
    creados["grupos"] += int(nuevo)

    # Aulas
    _, nuevo = _get_or_create_aula(db, "A-101", 40, "Bloque A")
    creados["aulas"] += int(nuevo)

    _, nuevo = _get_or_create_aula(db, "A-201", 35, "Bloque A")
    creados["aulas"] += int(nuevo)

    _, nuevo = _get_or_create_aula(
        db, "LAB-01", 30, "Laboratorios", tiene_computadores=True
    )
    creados["aulas"] += int(nuevo)

    _, nuevo = _get_or_create_aula(
        db, "LAB-02", 30, "Laboratorios", tiene_computadores=True
    )
    creados["aulas"] += int(nuevo)

    # Franjas horarias
    franjas_data = [
        ("Lunes", "07:00", "09:00", False),
        ("Lunes", "09:00", "11:00", False),
        ("Martes", "07:00", "09:00", False),
        ("Martes", "09:00", "11:00", False),
        ("Miercoles", "07:00", "09:00", False),
        ("Miercoles", "09:00", "11:00", False),
        ("Jueves", "07:00", "09:00", False),
        ("Viernes", "07:00", "09:00", False),
        ("Lunes", "12:00", "13:00", True),
    ]

    franjas = {}

    for dia, inicio, fin, bloqueada in franjas_data:
        franja, nuevo = _get_or_create_franja(db, dia, inicio, fin, bloqueada)
        creados["franjas"] += int(nuevo)
        franjas[(dia, inicio, fin)] = franja

    # Elegibilidad docente-curso
    elegibilidades_data = [
        (ana, calculo),
        (carlos, programacion),
        (laura, bases),
        (laura, etica),
    ]

    for docente, curso in elegibilidades_data:
        _, nuevo = _get_or_create_elegibilidad(db, docente.id, curso.id)
        creados["elegibilidades"] += int(nuevo)

    # Disponibilidad docente
    disponibilidad_data = [
        (ana, ("Lunes", "07:00", "09:00")),
        (ana, ("Miercoles", "07:00", "09:00")),
        (carlos, ("Martes", "07:00", "09:00")),
        (carlos, ("Jueves", "07:00", "09:00")),
        (laura, ("Miercoles", "09:00", "11:00")),
        (laura, ("Viernes", "07:00", "09:00")),
        (laura, ("Martes", "09:00", "11:00")),
    ]

    for docente, franja_key in disponibilidad_data:
        franja = franjas[franja_key]
        _, nuevo = _get_or_create_disponibilidad(db, docente.id, franja.id)
        creados["disponibilidades"] += int(nuevo)

    db.commit()

    sesiones = crud.preparar_sesiones_para_motor(db)
    creados["sesiones"] = len(sesiones)

    return {
        "mensaje": "Datos académicos iniciales cargados correctamente",
        "creados_en_esta_ejecucion": creados,
        "total_sesiones_preparadas": len(sesiones),
        "credenciales": {
            "correo": "admin@horarios.edu",
            "password": "admin123"
        }
    }