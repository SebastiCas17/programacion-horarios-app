"""
main.py
=======
Servidor FastAPI — Punto de entrada de la aplicación.
Define todos los endpoints REST, sirve la interfaz web y protege rutas críticas con JWT + roles.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
import io
import csv
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.orm import Session
from typing import List
import os

import models, schemas, crud
from database import engine, get_db
from motor.generador import GeneradorHorarios
from auth import verificar_password, crear_token_acceso, exigir_roles

# Crear tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Programación de Horarios de Clase",
    description="Motor de generación de horarios académicos con backtracking — Universidad El Bosque",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ==============================================================================
# USUARIO ADMINISTRADOR INICIAL
# ==============================================================================
def crear_admin_inicial():
    """
    Crea automáticamente un usuario administrador inicial si no existe.
    Esto permite que el sistema pueda usarse inmediatamente después de levantar Docker.
    """

    db = next(get_db())

    try:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@horarios.edu")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_name = os.getenv("ADMIN_NAME", "Administrador del Sistema")

        existente = crud.get_usuario_por_correo(db, admin_email)

        if existente:
            print(f"Usuario administrador ya existe: {admin_email}")
            return

        admin = schemas.UsuarioCreate(
            nombre=admin_name,
            correo=admin_email,
            password=admin_password,
            rol="Administrador",
            estado=True
        )

        crud.create_usuario(db, admin)

        print("Usuario administrador inicial creado correctamente")
        print(f"Correo: {admin_email}")
        print(f"Contraseña: {admin_password}")

    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    """
    Evento de arranque de FastAPI.
    Garantiza que exista un administrador inicial.
    """
    crear_admin_inicial()

# ==============================================================================
# RUTA PRINCIPAL
# ==============================================================================
@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ==============================================================================
# AUTENTICACIÓN Y USUARIOS
# ==============================================================================
@app.post("/api/auth/login", response_model=schemas.TokenOut, tags=["Autenticación"])
def login(datos: schemas.LoginRequest, db: Session = Depends(get_db)):
    usuario = crud.get_usuario_por_correo(db, datos.correo)

    if not usuario or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    if not usuario.estado:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    token = crear_token_acceso(data={
        "sub": str(usuario.id),
        "rol": usuario.rol
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": usuario
    }


@app.post("/api/usuarios", response_model=schemas.UsuarioOut, tags=["Usuarios"])
def crear_usuario(
    usuario: schemas.UsuarioCreate,
    db: Session = Depends(get_db)
):
    existente = crud.get_usuario_por_correo(db, usuario.correo)

    if existente:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    return crud.create_usuario(db, usuario)


@app.get("/api/usuarios", response_model=list[schemas.UsuarioOut], tags=["Usuarios"])
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador"))
):
    return crud.get_usuarios(db)

# ==============================================================================
# PARAMETROS DE SEMESTRE
# ==============================================================================
@app.get(
    "/api/parametros-semestre/activo",
    response_model=schemas.ParametroSemestreOut,
    tags=["Parámetros Semestre"]
)
def obtener_parametro_semestre_activo(db: Session = Depends(get_db)):
    return crud.obtener_o_crear_parametro_activo(db)


@app.get(
    "/api/parametros-semestre",
    response_model=List[schemas.ParametroSemestreOut],
    tags=["Parámetros Semestre"]
)
def listar_parametros_semestre(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    return crud.get_parametros_semestre(db)


@app.post(
    "/api/parametros-semestre",
    response_model=schemas.ParametroSemestreOut,
    tags=["Parámetros Semestre"]
)
def crear_parametro_semestre(
    parametro: schemas.ParametroSemestreCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    return crud.create_parametro_semestre(db, parametro)


# ==============================================================================
# DOCENTES
# ==============================================================================
@app.get("/api/docentes", response_model=List[schemas.DocenteOut], tags=["Docentes"])
def listar_docentes(db: Session = Depends(get_db)):
    return crud.get_docentes(db)


@app.post("/api/docentes", response_model=schemas.DocenteOut, tags=["Docentes"])
def crear_docente(
    docente: schemas.DocenteCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    return crud.create_docente(db, docente)


@app.delete("/api/docentes/{docente_id}", tags=["Docentes"])
def eliminar_docente(
    docente_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    resultado = crud.delete_docente(db, docente_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    return {"mensaje": "Docente eliminado correctamente"}


# ==============================================================================
# CURSOS
# ==============================================================================
@app.get("/api/cursos", response_model=List[schemas.CursoOut], tags=["Cursos"])
def listar_cursos(db: Session = Depends(get_db)):
    return crud.get_cursos(db)


@app.post("/api/cursos", response_model=schemas.CursoOut, tags=["Cursos"])
def crear_curso(
    curso: schemas.CursoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    return crud.create_curso(db, curso)


@app.delete("/api/cursos/{curso_id}", tags=["Cursos"])
def eliminar_curso(
    curso_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    resultado = crud.delete_curso(db, curso_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return {"mensaje": "Curso eliminado correctamente"}


# ==============================================================================
# GRUPOS
# ==============================================================================
@app.get("/api/grupos", response_model=List[schemas.GrupoOut], tags=["Grupos"])
def listar_grupos(db: Session = Depends(get_db)):
    return crud.get_grupos(db)


@app.post("/api/grupos", response_model=schemas.GrupoOut, tags=["Grupos"])
def crear_grupo(
    grupo: schemas.GrupoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    curso = crud.get_curso(db, grupo.id_curso)
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    return crud.create_grupo(db, grupo)


@app.delete("/api/grupos/{grupo_id}", tags=["Grupos"])
def eliminar_grupo(
    grupo_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    resultado = crud.delete_grupo(db, grupo_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return {"mensaje": "Grupo eliminado correctamente"}


# ==============================================================================
# AULAS
# ==============================================================================
@app.get("/api/aulas", response_model=List[schemas.AulaOut], tags=["Aulas"])
def listar_aulas(db: Session = Depends(get_db)):
    return crud.get_aulas(db)


@app.post("/api/aulas", response_model=schemas.AulaOut, tags=["Aulas"])
def crear_aula(
    aula: schemas.AulaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    return crud.create_aula(db, aula)


@app.delete("/api/aulas/{aula_id}", tags=["Aulas"])
def eliminar_aula(
    aula_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    resultado = crud.delete_aula(db, aula_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    return {"mensaje": "Aula eliminada correctamente"}


# ==============================================================================
# FRANJAS HORARIAS
# ==============================================================================
@app.get("/api/franjas", response_model=List[schemas.FranjaOut], tags=["Franjas"])
def listar_franjas(db: Session = Depends(get_db)):
    return crud.get_franjas(db)


@app.post("/api/franjas", response_model=schemas.FranjaOut, tags=["Franjas"])
def crear_franja(
    franja: schemas.FranjaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    return crud.create_franja(db, franja)


@app.delete("/api/franjas/{franja_id}", tags=["Franjas"])
def eliminar_franja(
    franja_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    resultado = crud.delete_franja(db, franja_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Franja no encontrada")
    return {"mensaje": "Franja eliminada correctamente"}


# ==============================================================================
# DISPONIBILIDAD DOCENTE
# ==============================================================================
@app.get("/api/disponibilidad", response_model=List[schemas.DisponibilidadOut], tags=["Disponibilidad"])
def listar_disponibilidades(db: Session = Depends(get_db)):
    return crud.get_disponibilidades(db)


@app.post("/api/disponibilidad", response_model=schemas.DisponibilidadOut, tags=["Disponibilidad"])
def crear_disponibilidad(
    disp: schemas.DisponibilidadCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    return crud.create_disponibilidad(db, disp)


@app.delete("/api/disponibilidad/{disp_id}", tags=["Disponibilidad"])
def eliminar_disponibilidad(
    disp_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    resultado = crud.delete_disponibilidad(db, disp_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")
    return {"mensaje": "Disponibilidad eliminada correctamente"}


# ==============================================================================
# ELEGIBILIDAD DOCENTE-CURSO
# ==============================================================================
@app.get("/api/elegibilidad", response_model=List[schemas.ElegibilidadOut], tags=["Elegibilidad"])
def listar_elegibilidades(db: Session = Depends(get_db)):
    return crud.get_elegibilidades(db)


@app.post("/api/elegibilidad", response_model=schemas.ElegibilidadOut, tags=["Elegibilidad"])
def crear_elegibilidad(
    eleg: schemas.ElegibilidadCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    return crud.create_elegibilidad(db, eleg)


@app.delete("/api/elegibilidad/{eleg_id}", tags=["Elegibilidad"])
def eliminar_elegibilidad(
    eleg_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    resultado = crud.delete_elegibilidad(db, eleg_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Elegibilidad no encontrada")
    return {"mensaje": "Elegibilidad eliminada correctamente"}


# ==============================================================================
# MOTOR DE HORARIOS
# =============================================================================

def _construir_asignaciones_out(asignaciones: list, horario_id: int) -> list:
    """
    Construye la lista de asignaciones para el frontend con datos expandidos.
    """
    resultado = []

    for asig in asignaciones:
        resultado.append({
            "horario_id": horario_id,
            "sesion_id": asig["sesion"].id,
            "numero_sesion": asig["sesion"].numero_sesion,
            "docente_nombre": asig["docente"].nombre,
            "aula_codigo": asig["aula"].codigo,
            "franja_dia": asig["franja"].dia_semana,
            "franja_inicio": asig["franja"].hora_inicio,
            "franja_fin": asig["franja"].hora_fin,
            "curso_nombre": asig["curso"].nombre,
            "grupo_nombre": asig["grupo"].nombre_grupo,
            "penalizacion": asig.get("penalizacion", 0.0)
        })

    return resultado


# ==============================================================================
# HORARIOS GENERADOS
# ==============================================================================
# ==============================================================================
# HORARIOS GENERADOS, PUBLICACIÓN OFICIAL Y EXPORTACIÓN
# ==============================================================================
@app.get("/api/horarios", tags=["Horarios"])
def listar_horarios(db: Session = Depends(get_db)):
    """
    Lista todos los horarios generados.
    Permite al frontend mostrar historial, estado y opción de publicar/exportar.
    """
    horarios = crud.get_horarios(db)

    return [
        {
            "id": h.id,
            "fecha_generacion": h.fecha_generacion,
            "estado": h.estado,
            "puntaje_total": h.puntaje_total,
            "es_oficial": h.es_oficial,
            "num_asignaciones": len(h.asignaciones),
            "num_conflictos": len(h.conflictos)
        }
        for h in horarios
    ]


@app.get("/api/horarios/{horario_id}", tags=["Horarios"])
def obtener_horario(
    horario_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene el detalle completo de un horario generado.
    """
    horario = crud.get_horario(db, horario_id)

    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    asignaciones_out = []

    for asig in horario.asignaciones:
        curso_nombre = "N/A"
        grupo_nombre = "N/A"
        numero_sesion = None

        if asig.sesion:
            numero_sesion = asig.sesion.numero_sesion

            if asig.sesion.grupo:
                grupo_nombre = asig.sesion.grupo.nombre_grupo

                if asig.sesion.grupo.curso:
                    curso_nombre = asig.sesion.grupo.curso.nombre

        asignaciones_out.append({
            "id": asig.id,
            "sesion_id": asig.id_sesion,
            "numero_sesion": numero_sesion,
            "curso_nombre": curso_nombre,
            "grupo_nombre": grupo_nombre,
            "docente_nombre": asig.docente.nombre if asig.docente else "N/A",
            "aula_codigo": asig.aula.codigo if asig.aula else "N/A",
            "franja_dia": asig.franja.dia_semana if asig.franja else "N/A",
            "franja_inicio": asig.franja.hora_inicio if asig.franja else "",
            "franja_fin": asig.franja.hora_fin if asig.franja else "",
            "estado": asig.estado,
            "penalizacion": asig.puntaje_penalizacion
        })

    conflictos_out = []

    for conf in horario.conflictos:
        conflictos_out.append({
            "id": conf.id,
            "id_sesion": conf.id_sesion,
            "id_restriccion": conf.id_restriccion,
            "descripcion": conf.descripcion,
            "entidad_tipo": conf.entidad_tipo,
            "entidad_id": conf.entidad_id
        })

    return {
        "id": horario.id,
        "fecha_generacion": horario.fecha_generacion,
        "estado": horario.estado,
        "puntaje_total": horario.puntaje_total,
        "es_oficial": horario.es_oficial,
        "asignaciones": asignaciones_out,
        "conflictos": conflictos_out
    }


@app.post("/api/horarios/{horario_id}/publicar", tags=["Horarios"])
def publicar_horario(
    horario_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Marca un horario válido como oficial e inmutable.
    Cumple RH-14: versión oficial publicada.
    """
    horario = crud.publicar_horario(db, horario_id)

    if not horario:
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden publicar horarios con estado Valido"
        )

    return {
        "mensaje": "Horario publicado como oficial",
        "horario_id": horario_id,
        "estado": horario.estado,
        "es_oficial": horario.es_oficial
    }


@app.delete("/api/horarios/{horario_id}", tags=["Horarios"])
def eliminar_horario(
    horario_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador"))
):
    """
    Elimina un horario solo si no es oficial.
    """
    resultado = crud.delete_horario(db, horario_id)

    if not resultado:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: horario no encontrado o es oficial"
        )

    return {"mensaje": "Horario eliminado correctamente"}


@app.get("/api/horarios/{horario_id}/exportar-csv", tags=["Horarios"])
def exportar_horario_csv(
    horario_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador", "Consulta"))
):
    """
    Exporta el horario generado en formato CSV.
    Puede abrirse en Excel como insumo del proceso académico.
    """
    horario = crud.get_horario(db, horario_id)

    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    output = io.StringIO()

    # BOM para que Excel reconozca tildes y caracteres especiales
    output.write("\ufeff")

    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "Horario ID",
        "Estado",
        "Oficial",
        "Fecha generación",
        "Curso",
        "Grupo",
        "Sesión",
        "Docente",
        "Aula",
        "Día",
        "Hora inicio",
        "Hora fin",
        "Penalización"
    ])

    for asig in horario.asignaciones:
        curso_nombre = "N/A"
        grupo_nombre = "N/A"
        numero_sesion = ""

        if asig.sesion:
            numero_sesion = asig.sesion.numero_sesion

            if asig.sesion.grupo:
                grupo_nombre = asig.sesion.grupo.nombre_grupo

                if asig.sesion.grupo.curso:
                    curso_nombre = asig.sesion.grupo.curso.nombre

        writer.writerow([
            horario.id,
            horario.estado,
            "Sí" if horario.es_oficial else "No",
            horario.fecha_generacion,
            curso_nombre,
            grupo_nombre,
            numero_sesion,
            asig.docente.nombre if asig.docente else "N/A",
            asig.aula.codigo if asig.aula else "N/A",
            asig.franja.dia_semana if asig.franja else "N/A",
            asig.franja.hora_inicio if asig.franja else "",
            asig.franja.hora_fin if asig.franja else "",
            asig.puntaje_penalizacion
        ])

    output.seek(0)

    filename = f"horario_{horario.id}.csv"

    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv"
    )

    response.headers["Content-Disposition"] = f"attachment; filename={filename}"

    return response

# ==============================================================================
# DATOS DE EJEMPLO
# ==============================================================================
@app.post("/api/cargar-datos-ejemplo", tags=["Utilidades"])
def cargar_datos_ejemplo(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    try:
        franjas_data = [
            {"dia_semana": "Lunes", "hora_inicio": "07:00", "hora_fin": "09:00"},
            {"dia_semana": "Lunes", "hora_inicio": "09:00", "hora_fin": "11:00"},
            {"dia_semana": "Martes", "hora_inicio": "07:00", "hora_fin": "09:00"},
            {"dia_semana": "Martes", "hora_inicio": "09:00", "hora_fin": "11:00"},
            {"dia_semana": "Miercoles", "hora_inicio": "07:00", "hora_fin": "09:00"},
            {"dia_semana": "Miercoles", "hora_inicio": "09:00", "hora_fin": "11:00"},
            {"dia_semana": "Jueves", "hora_inicio": "07:00", "hora_fin": "09:00"},
            {"dia_semana": "Viernes", "hora_inicio": "07:00", "hora_fin": "09:00"},
            {"dia_semana": "Lunes", "hora_inicio": "12:00", "hora_fin": "13:00", "bloqueada": True},
        ]

        franjas_creadas = []
        for f in franjas_data:
            franja = crud.create_franja(db, schemas.FranjaCreate(**f))
            franjas_creadas.append(franja)

        aulas_data = [
            {"codigo": "A-101", "capacidad": 40, "edificio": "Bloque A"},
            {"codigo": "A-201", "capacidad": 35, "edificio": "Bloque A"},
            {"codigo": "LAB-01", "capacidad": 30, "tiene_computadores": True, "edificio": "Laboratorios"},
        ]

        aulas_creadas = []
        for a in aulas_data:
            aula = crud.create_aula(db, schemas.AulaCreate(**a))
            aulas_creadas.append(aula)

        docentes_data = [
            {"nombre": "Carlos García", "correo": "cgarcia@unbosque.edu.co", "tipo_vinculacion": "TC"},
            {"nombre": "María López", "correo": "mlopez@unbosque.edu.co", "tipo_vinculacion": "MT"},
            {"nombre": "Andrés Rodríguez", "correo": "arodriguez@unbosque.edu.co", "tipo_vinculacion": "TC"},
        ]

        docentes_creados = []
        for d in docentes_data:
            docente = crud.create_docente(db, schemas.DocenteCreate(**d))
            docentes_creados.append(docente)

        cursos_data = [
            {"nombre": "Cálculo Diferencial", "codigo": "MAT101", "creditos": 4, "sesiones_semana": 2},
            {"nombre": "Programación I", "codigo": "SIS101", "creditos": 3, "sesiones_semana": 2, "requiere_computadores": True},
            {"nombre": "Bases de Datos", "codigo": "SIS201", "creditos": 3, "sesiones_semana": 2, "requiere_computadores": True},
        ]

        cursos_creados = []
        for c in cursos_data:
            curso = crud.create_curso(db, schemas.CursoCreate(**c))
            cursos_creados.append(curso)

        grupos_data = [
            {"id_curso": cursos_creados[0].id, "nombre_grupo": "CAL-01", "cupo_objetivo": 35, "inscritos": 30},
            {"id_curso": cursos_creados[1].id, "nombre_grupo": "SIS-01", "cupo_objetivo": 30, "inscritos": 25},
            {"id_curso": cursos_creados[2].id, "nombre_grupo": "BD-01", "cupo_objetivo": 28, "inscritos": 22},
        ]

        grupos_creados = []
        for g in grupos_data:
            grupo = crud.create_grupo(db, schemas.GrupoCreate(**g))
            grupos_creados.append(grupo)

        eleg_data = [
            {"id_docente": docentes_creados[0].id, "id_curso": cursos_creados[0].id},
            {"id_docente": docentes_creados[1].id, "id_curso": cursos_creados[1].id},
            {"id_docente": docentes_creados[2].id, "id_curso": cursos_creados[2].id},
            {"id_docente": docentes_creados[0].id, "id_curso": cursos_creados[2].id},
        ]

        for e in eleg_data:
            crud.create_elegibilidad(db, schemas.ElegibilidadCreate(**e))

        franjas_activas = [f for f in franjas_creadas if not f.bloqueada]

        for docente in docentes_creados:
            for franja in franjas_activas:
                crud.create_disponibilidad(
                    db,
                    schemas.DisponibilidadCreate(
                        id_docente=docente.id,
                        id_franja=franja.id
                    )
                )

        return {
            "mensaje": "Datos de ejemplo cargados correctamente",
            "franjas": len(franjas_creadas),
            "aulas": len(aulas_creadas),
            "docentes": len(docentes_creados),
            "cursos": len(cursos_creados),
            "grupos": len(grupos_creados)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al cargar datos: {str(e)}")