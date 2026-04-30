"""
main.py
=======
Servidor FastAPI — Punto de entrada de la aplicación.
Define todos los endpoints REST, sirve la interfaz web, protege rutas críticas con JWT + roles,
permite generar horarios con backtracking, publicar horarios oficiales, exportar CSV y cargar datos iniciales.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from sqlalchemy.orm import Session
from typing import List

import os
import io
import csv

import models, schemas, crud
from database import engine, get_db
from motor.generador import GeneradorHorarios
from auth import verificar_password, crear_token_acceso, exigir_roles
from seed_data import cargar_datos_academicos_iniciales


# ==============================================================================
# INICIALIZACIÓN DE BASE DE DATOS
# ==============================================================================
models.Base.metadata.create_all(bind=engine)


# ==============================================================================
# APLICACIÓN FASTAPI
# ==============================================================================
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
            print(f"Usuario administrador ya existe: {admin_email}", flush=True)
            return

        admin = schemas.UsuarioCreate(
            nombre=admin_name,
            correo=admin_email,
            password=admin_password,
            rol="Administrador",
            estado=True
        )

        crud.create_usuario(db, admin)

        print("Usuario administrador inicial creado correctamente", flush=True)
        print(f"Correo: {admin_email}", flush=True)
        print(f"Contraseña: {admin_password}", flush=True)

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
# RUTA PRINCIPAL — INTERFAZ WEB
# ==============================================================================
@app.get("/")
def root(request: Request):
    """
    Sirve la interfaz web principal.
    """
    return templates.TemplateResponse("index.html", {"request": request})


# ==============================================================================
# AUTENTICACIÓN Y USUARIOS
# ==============================================================================
@app.post("/api/auth/login", response_model=schemas.TokenOut, tags=["Autenticación"])
def login(datos: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Inicia sesión y retorna un token JWT.
    """
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
    """
    Crea un usuario del sistema.
    Se deja abierto para permitir el primer registro si fuera necesario.
    """
    existente = crud.get_usuario_por_correo(db, usuario.correo)

    if existente:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    return crud.create_usuario(db, usuario)


@app.get("/api/usuarios", response_model=list[schemas.UsuarioOut], tags=["Usuarios"])
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador"))
):
    """
    Lista usuarios registrados. Solo Administrador.
    """
    return crud.get_usuarios(db)


# ==============================================================================
# PARÁMETROS DE SEMESTRE
# ==============================================================================
@app.get(
    "/api/parametros-semestre/activo",
    response_model=schemas.ParametroSemestreOut,
    tags=["Parámetros Semestre"]
)
def obtener_parametro_semestre_activo(db: Session = Depends(get_db)):
    """
    Obtiene el semestre activo. Si no existe, crea uno por defecto.
    """
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
    """
    Lista parámetros de semestre.
    """
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
    """
    Crea o actualiza parámetros de semestre.
    """
    return crud.create_parametro_semestre(db, parametro)


# ==============================================================================
# DOCENTES
# ==============================================================================
@app.get("/api/docentes", response_model=List[schemas.DocenteOut], tags=["Docentes"])
def listar_docentes(db: Session = Depends(get_db)):
    """
    Lista docentes activos.
    """
    return crud.get_docentes(db)


@app.post("/api/docentes", response_model=schemas.DocenteOut, tags=["Docentes"])
def crear_docente(
    docente: schemas.DocenteCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Crea un docente.
    """
    return crud.create_docente(db, docente)


@app.delete("/api/docentes/{docente_id}", tags=["Docentes"])
def eliminar_docente(
    docente_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Elimina un docente.
    """
    resultado = crud.delete_docente(db, docente_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    return {"mensaje": "Docente eliminado correctamente"}


# ==============================================================================
# CURSOS
# ==============================================================================
@app.get("/api/cursos", response_model=List[schemas.CursoOut], tags=["Cursos"])
def listar_cursos(db: Session = Depends(get_db)):
    """
    Lista cursos activos.
    """
    return crud.get_cursos(db)


@app.post("/api/cursos", response_model=schemas.CursoOut, tags=["Cursos"])
def crear_curso(
    curso: schemas.CursoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Crea un curso.
    """
    return crud.create_curso(db, curso)


@app.delete("/api/cursos/{curso_id}", tags=["Cursos"])
def eliminar_curso(
    curso_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Elimina un curso.
    """
    resultado = crud.delete_curso(db, curso_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    return {"mensaje": "Curso eliminado correctamente"}


# ==============================================================================
# GRUPOS
# ==============================================================================
@app.get("/api/grupos", response_model=List[schemas.GrupoOut], tags=["Grupos"])
def listar_grupos(db: Session = Depends(get_db)):
    """
    Lista grupos.
    """
    return crud.get_grupos(db)


@app.post("/api/grupos", response_model=schemas.GrupoOut, tags=["Grupos"])
def crear_grupo(
    grupo: schemas.GrupoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Crea un grupo asociado a un curso.
    """
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
    """
    Elimina un grupo.
    """
    resultado = crud.delete_grupo(db, grupo_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    return {"mensaje": "Grupo eliminado correctamente"}


# ==============================================================================
# AULAS
# ==============================================================================
@app.get("/api/aulas", response_model=List[schemas.AulaOut], tags=["Aulas"])
def listar_aulas(db: Session = Depends(get_db)):
    """
    Lista aulas activas.
    """
    return crud.get_aulas(db)


@app.post("/api/aulas", response_model=schemas.AulaOut, tags=["Aulas"])
def crear_aula(
    aula: schemas.AulaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Crea un aula.
    """
    return crud.create_aula(db, aula)


@app.delete("/api/aulas/{aula_id}", tags=["Aulas"])
def eliminar_aula(
    aula_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Elimina un aula.
    """
    resultado = crud.delete_aula(db, aula_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Aula no encontrada")

    return {"mensaje": "Aula eliminada correctamente"}


# ==============================================================================
# FRANJAS HORARIAS
# ==============================================================================
@app.get("/api/franjas", response_model=List[schemas.FranjaOut], tags=["Franjas"])
def listar_franjas(db: Session = Depends(get_db)):
    """
    Lista franjas horarias.
    """
    return crud.get_franjas(db)


@app.post("/api/franjas", response_model=schemas.FranjaOut, tags=["Franjas"])
def crear_franja(
    franja: schemas.FranjaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Crea una franja horaria.
    """
    return crud.create_franja(db, franja)


@app.delete("/api/franjas/{franja_id}", tags=["Franjas"])
def eliminar_franja(
    franja_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Elimina una franja horaria.
    """
    resultado = crud.delete_franja(db, franja_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Franja no encontrada")

    return {"mensaje": "Franja eliminada correctamente"}


# ==============================================================================
# DISPONIBILIDAD DOCENTE
# ==============================================================================
@app.get("/api/disponibilidad", response_model=List[schemas.DisponibilidadOut], tags=["Disponibilidad"])
def listar_disponibilidades(db: Session = Depends(get_db)):
    """
    Lista disponibilidades docentes.
    """
    return crud.get_disponibilidades(db)


@app.post("/api/disponibilidad", response_model=schemas.DisponibilidadOut, tags=["Disponibilidad"])
def crear_disponibilidad(
    disp: schemas.DisponibilidadCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Crea disponibilidad docente.
    """
    return crud.create_disponibilidad(db, disp)


@app.delete("/api/disponibilidad/{disp_id}", tags=["Disponibilidad"])
def eliminar_disponibilidad(
    disp_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Elimina disponibilidad docente.
    """
    resultado = crud.delete_disponibilidad(db, disp_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")

    return {"mensaje": "Disponibilidad eliminada correctamente"}


# ==============================================================================
# ELEGIBILIDAD DOCENTE-CURSO
# ==============================================================================
@app.get("/api/elegibilidad", response_model=List[schemas.ElegibilidadOut], tags=["Elegibilidad"])
def listar_elegibilidades(db: Session = Depends(get_db)):
    """
    Lista elegibilidades docente-curso.
    """
    return crud.get_elegibilidades(db)


@app.post("/api/elegibilidad", response_model=schemas.ElegibilidadOut, tags=["Elegibilidad"])
def crear_elegibilidad(
    eleg: schemas.ElegibilidadCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Crea elegibilidad docente-curso.
    """
    return crud.create_elegibilidad(db, eleg)


@app.delete("/api/elegibilidad/{eleg_id}", tags=["Elegibilidad"])
def eliminar_elegibilidad(
    eleg_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Elimina elegibilidad docente-curso.
    """
    resultado = crud.delete_elegibilidad(db, eleg_id)

    if not resultado:
        raise HTTPException(status_code=404, detail="Elegibilidad no encontrada")

    return {"mensaje": "Elegibilidad eliminada correctamente"}


# ==============================================================================
# MOTOR DE HORARIOS
# ==============================================================================
@app.post("/api/generar-horario", tags=["Motor"])
def generar_horario(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Ejecuta el motor de backtracking con sesiones reales.

    Flujo:
    1. Prepara sesiones reales en la base de datos.
    2. Carga todos los datos en memoria.
    3. Ejecuta el algoritmo de backtracking.
    4. Persiste asignaciones y conflictos.
    5. Retorna el horario generado.
    """

    # 1. Preparar sesiones reales en BD
    crud.preparar_sesiones_para_motor(db)

    # 2. Cargar datos en memoria
    datos = crud.get_todos_los_datos(db)

    if not datos["grupos"]:
        raise HTTPException(
            status_code=400,
            detail="No hay grupos registrados. Registra cursos y grupos antes de generar el horario."
        )

    if not datos["aulas"]:
        raise HTTPException(status_code=400, detail="No hay aulas registradas.")

    if not datos["franjas"]:
        raise HTTPException(status_code=400, detail="No hay franjas horarias registradas.")

    if not datos.get("sesiones"):
        raise HTTPException(
            status_code=400,
            detail="No hay sesiones reales generadas para programar."
        )

    # 3. Crear horario
    horario_db = crud.create_horario(db)

    # 4. Ejecutar motor
    motor = GeneradorHorarios(datos)
    resultado = motor.generar()

    puntaje_total = resultado.get("puntaje_total", 0.0)

    # 5. Persistir asignaciones reales
    for asig in resultado.get("asignaciones", []):
        sesion = asig["sesion"]

        asignacion_db = models.Asignacion(
            id_sesion=sesion.id,
            id_docente=asig["docente"].id,
            id_aula=asig["aula"].id,
            id_franja=asig["franja"].id,
            id_horario=horario_db.id,
            estado="Valida",
            puntaje_penalizacion=asig.get("penalizacion", 0.0)
        )

        db.add(asignacion_db)
        sesion.estado = "Asignada"

    # 6. Persistir conflictos trazables
    for conf in resultado.get("conflictos", []):
        id_sesion = conf.get("id_sesion")

        conflicto_db = models.Conflicto(
            id_horario=horario_db.id,
            id_sesion=id_sesion,
            id_restriccion=conf.get("id_restriccion", "???"),
            descripcion=conf.get("descripcion", ""),
            entidad_tipo=conf.get("entidad_tipo", "Sistema"),
            entidad_id=conf.get("entidad_id", 0)
        )

        db.add(conflicto_db)

        if id_sesion:
            sesion_conflicto = db.query(models.SesionClase).filter(
                models.SesionClase.id == id_sesion
            ).first()

            if sesion_conflicto:
                sesion_conflicto.estado = "Conflicto"

    # 7. Actualizar estado del horario
    estado_final = "Valido" if resultado["exito"] else "No_Factible"
    horario_db.estado = estado_final
    horario_db.puntaje_total = puntaje_total

    db.commit()
    db.refresh(horario_db)

    asignaciones_out = _construir_asignaciones_out(
        resultado.get("asignaciones", []),
        horario_db.id
    )

    return {
        "horario_id": horario_db.id,
        "estado": estado_final,
        "puntaje_total": puntaje_total,
        "total_asignadas": len(resultado.get("asignaciones", [])),
        "total_conflictos": len(resultado.get("conflictos", [])),
        "asignaciones": asignaciones_out,
        "conflictos": resultado.get("conflictos", []),
        "reporte_blandas": resultado.get("reporte_blandas", {})
    }


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
# SEED ACADÉMICO Y DATOS DE EJEMPLO
# ==============================================================================
@app.post("/api/seed/datos-academicos", tags=["Seed"])
def cargar_seed_academico(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Carga datos académicos iniciales sin duplicarlos.
    Permite probar el sistema después de levantar Docker desde cero.
    """
    try:
        return cargar_datos_academicos_iniciales(db)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar datos iniciales: {str(e)}"
        )


@app.post("/api/cargar-datos-ejemplo", tags=["Utilidades"])
def cargar_datos_ejemplo(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    """
    Compatibilidad con el endpoint antiguo.
    Ahora usa la carga idempotente de seed académico.
    """
    try:
        return cargar_datos_academicos_iniciales(db)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar datos: {str(e)}"
        )