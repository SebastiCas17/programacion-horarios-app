"""
main.py
=======
Servidor FastAPI — Punto de entrada de la aplicación.
Define todos los endpoints REST, sirve la interfaz web, protege rutas críticas con JWT + roles,
permite generar horarios con backtracking, publicar horarios oficiales, exportar CSV y cargar datos iniciales.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from sqlalchemy.orm import Session
from typing import List

import os
import io
import csv
import asyncio
from concurrent.futures import ThreadPoolExecutor

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

executor = ThreadPoolExecutor(max_workers=2)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Convierte errores de validación Pydantic en mensajes legibles para el frontend.
    Así el usuario no ve errores técnicos ni estructuras difíciles de leer.
    """

    mensajes = []

    for error in exc.errors():
        ubicacion = [
            str(item)
            for item in error.get("loc", [])
            if item not in ("body", "query", "path")
        ]

        campo = ".".join(ubicacion) if ubicacion else "dato"
        mensaje = error.get("msg", "Dato inválido").replace("Value error, ", "")

        mensajes.append(f"{campo}: {mensaje}")

    return JSONResponse(
        status_code=422,
        content={
            "detail": " | ".join(mensajes)
        }
    )


# ==============================================================================
# USUARIOS INICIALES DEL SISTEMA
# ==============================================================================

def crear_usuarios_iniciales():
    """
    Crea automáticamente los usuarios iniciales del sistema si no existen.
    Roles disponibles:
    - Administrador
    - Coordinador
    - Consulta
    """

    db = next(get_db())

    try:
        usuarios_iniciales = [
            {
                "nombre": os.getenv("ADMIN_NAME", "Administrador del Sistema"),
                "correo": os.getenv("ADMIN_EMAIL", "admin@horarios.edu"),
                "password": os.getenv("ADMIN_PASSWORD", "admin123"),
                "rol": "Administrador"
            },
            {
                "nombre": os.getenv("COORDINADOR_NAME", "Coordinador Académico"),
                "correo": os.getenv("COORDINADOR_EMAIL", "coordinador@horarios.edu"),
                "password": os.getenv("COORDINADOR_PASSWORD", "coord123"),
                "rol": "Coordinador"
            },
            {
                "nombre": os.getenv("CONSULTA_NAME", "Usuario de Consulta"),
                "correo": os.getenv("CONSULTA_EMAIL", "consulta@horarios.edu"),
                "password": os.getenv("CONSULTA_PASSWORD", "consulta123"),
                "rol": "Consulta"
            }
        ]

        for datos_usuario in usuarios_iniciales:
            existente = crud.get_usuario_por_correo(db, datos_usuario["correo"])

            if existente:
                print(
                    f"Usuario ya existe: {datos_usuario['correo']} - Rol: {existente.rol}",
                    flush=True
                )
                continue

            usuario = schemas.UsuarioCreate(
                nombre=datos_usuario["nombre"],
                correo=datos_usuario["correo"],
                password=datos_usuario["password"],
                rol=datos_usuario["rol"],
                estado=True
            )

            crud.create_usuario(db, usuario)

            print(
                f"Usuario inicial creado: {datos_usuario['correo']} - Rol: {datos_usuario['rol']}",
                flush=True
            )

        print("Validación de usuarios iniciales finalizada.", flush=True)

    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    """
    Evento de arranque de FastAPI.
    Garantiza que existan los usuarios iniciales del sistema.
    """
    crear_usuarios_iniciales()


# ==============================================================================
# RUTAS PRINCIPALES — INTERFAZ WEB POR ROL
# ==============================================================================

@app.get("/")
def root():
    return RedirectResponse(url="/login")


@app.get("/login")
def login_view(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/admin")
def admin_view(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/coordinador")
def coordinador_view(request: Request):
    return templates.TemplateResponse("coordinador.html", {"request": request})


@app.get("/consulta")
def consulta_view(request: Request):
    return templates.TemplateResponse("consulta.html", {"request": request})


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
# PARÁMETROS DE SEMESTRE
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

    if not curso.estado:
        raise HTTPException(
            status_code=400,
            detail="No se puede crear un grupo para un curso inactivo."
        )

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
# ==============================================================================

@app.post("/api/generar-horario", tags=["Motor"])
async def generar_horario(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_roles("Administrador", "Coordinador"))
):
    # 1. Preparar sesiones y cargar datos con eager loading
    crud.preparar_sesiones_para_motor(db)
    datos = crud.get_todos_los_datos(db)

    # 2. Validaciones previas
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

    # 3. CRÍTICO: desvincula todos los objetos SQLAlchemy de la sesión DB
    #    antes de pasarlos al ThreadPoolExecutor.
    #    Sin esto, el motor intenta acceder a relaciones lazy en otro thread,
    #    lo que provoca DetachedInstanceError → HTTP 500.
    #    Con joinedload en get_todos_los_datos + expunge_all aquí, los datos
    #    son objetos Python puros en memoria, seguros para cualquier thread.
    db.expunge_all()

    # 4. Crear el registro del horario (después del expunge para que no se pierda)
    horario_db = crud.create_horario(db)

    # 5. Ejecutar el motor en un thread separado para no bloquear el event loop
    def ejecutar_motor():
        motor = GeneradorHorarios(datos)
        return motor.generar()

    loop = asyncio.get_event_loop()
    try:
        resultado = await asyncio.wait_for(
            loop.run_in_executor(executor, ejecutar_motor),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        horario_db.estado = "No_Factible"
        horario_db.puntaje_total = 0.0
        db.commit()
        raise HTTPException(
            status_code=408,
            detail="El motor tardó demasiado (60s). Revisa disponibilidades y franjas horarias."
        )

    puntaje_total = resultado.get("puntaje_total", 0.0)

    # 6. Persistir asignaciones
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

        # Actualizar estado de la sesión directamente por ID para evitar
        # operar sobre el objeto detached
        db.query(models.SesionClase).filter(
            models.SesionClase.id == sesion.id
        ).update({"estado": "Asignada"}, synchronize_session=False)

    # 7. Persistir conflictos (deduplicados)
    conflictos_vistos = set()
    for conf in resultado.get("conflictos", []):
        clave = (conf.get("id_restriccion"), conf.get("id_sesion"))
        if clave in conflictos_vistos:
            continue
        conflictos_vistos.add(clave)

        id_sesion = conf.get("id_sesion")
        conflicto_db = models.Conflicto(
            id_horario=horario_db.id,
            id_sesion=id_sesion,
            id_restriccion=conf.get("id_restriccion", "???")[:50],
            descripcion=conf.get("descripcion", ""),
            entidad_tipo=conf.get("entidad_tipo", "Sistema"),
            entidad_id=conf.get("entidad_id", 0)
        )
        db.add(conflicto_db)

        if id_sesion:
            db.query(models.SesionClase).filter(
                models.SesionClase.id == id_sesion
            ).update({"estado": "Conflicto"}, synchronize_session=False)

    # 8. Actualizar estado final del horario
    estado_final = "Valido" if resultado["exito"] else "No_Factible"
    horario_db.estado = estado_final
    horario_db.puntaje_total = puntaje_total

    db.commit()
    db.refresh(horario_db)

    # 9. Construir respuesta
    asignaciones_out = _construir_asignaciones_out(
        resultado.get("asignaciones", []),
        horario_db.id
    )

    conflictos_out = list({
        (c.get("id_restriccion"), c.get("id_sesion")): c
        for c in resultado.get("conflictos", [])
    }.values())

    return {
        "horario_id": horario_db.id,
        "estado": estado_final,
        "puntaje_total": puntaje_total,
        "total_asignadas": len(resultado.get("asignaciones", [])),
        "total_conflictos": len(conflictos_out),
        "asignaciones": asignaciones_out,
        "conflictos": conflictos_out,
        "reporte_blandas": resultado.get("reporte_blandas", {})
    }


def _construir_asignaciones_out(asignaciones: list, horario_id: int) -> list:
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

    filename = f"horario_{horario_id}.csv"

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
    try:
        return cargar_datos_academicos_iniciales(db)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar datos: {str(e)}"
        )