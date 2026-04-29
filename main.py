"""
main.py
=======
Servidor FastAPI — Punto de entrada de la aplicación.
Define todos los endpoints REST y sirve la interfaz web.

Nota sobre JWT (ampliación futura):
  Para agregar autenticación JWT, instalar: pip install python-jose[cryptography] passlib[bcrypt]
  y agregar middleware de autenticación antes de los endpoints protegidos.
  
  from fastapi.security import OAuth2PasswordBearer
  oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas, crud
from database import engine, get_db
from motor.generador import GeneradorHorarios

# Crear todas las tablas en la base de datos al arrancar
models.Base.metadata.create_all(bind=engine)

# Inicializar aplicación FastAPI
app = FastAPI(
    title="Programación de Horarios de Clase",
    description="Motor de generación de horarios académicos con backtracking — Universidad El Bosque",
    version="1.0.0 MVP"
)

# Servir archivos estáticos (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Motor de templates Jinja2 para el HTML
templates = Jinja2Templates(directory="templates")


# ==============================================================================
# RUTA PRINCIPAL — Interfaz Web
# ==============================================================================
@app.get("/")
def root(request: Request):
    """Sirve la interfaz web principal."""
    return templates.TemplateResponse("index.html", {"request": request})


# ==============================================================================
# ENDPOINTS: Docentes
# ==============================================================================
@app.get("/api/docentes", response_model=List[schemas.DocenteOut], tags=["Docentes"])
def listar_docentes(db: Session = Depends(get_db)):
    """Lista todos los docentes activos."""
    return crud.get_docentes(db)

@app.post("/api/docentes", response_model=schemas.DocenteOut, tags=["Docentes"])
def crear_docente(docente: schemas.DocenteCreate, db: Session = Depends(get_db)):
    """Registra un nuevo docente."""
    return crud.create_docente(db, docente)

@app.delete("/api/docentes/{docente_id}", tags=["Docentes"])
def eliminar_docente(docente_id: int, db: Session = Depends(get_db)):
    """Elimina un docente (y su disponibilidad/elegibilidad en cascada)."""
    resultado = crud.delete_docente(db, docente_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    return {"mensaje": "Docente eliminado correctamente"}


# ==============================================================================
# ENDPOINTS: Cursos
# ==============================================================================
@app.get("/api/cursos", response_model=List[schemas.CursoOut], tags=["Cursos"])
def listar_cursos(db: Session = Depends(get_db)):
    return crud.get_cursos(db)

@app.post("/api/cursos", response_model=schemas.CursoOut, tags=["Cursos"])
def crear_curso(curso: schemas.CursoCreate, db: Session = Depends(get_db)):
    return crud.create_curso(db, curso)

@app.delete("/api/cursos/{curso_id}", tags=["Cursos"])
def eliminar_curso(curso_id: int, db: Session = Depends(get_db)):
    resultado = crud.delete_curso(db, curso_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return {"mensaje": "Curso eliminado correctamente"}


# ==============================================================================
# ENDPOINTS: Grupos
# ==============================================================================
@app.get("/api/grupos", response_model=List[schemas.GrupoOut], tags=["Grupos"])
def listar_grupos(db: Session = Depends(get_db)):
    return crud.get_grupos(db)

@app.post("/api/grupos", response_model=schemas.GrupoOut, tags=["Grupos"])
def crear_grupo(grupo: schemas.GrupoCreate, db: Session = Depends(get_db)):
    # Verificar que el curso existe
    curso = crud.get_curso(db, grupo.id_curso)
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return crud.create_grupo(db, grupo)

@app.delete("/api/grupos/{grupo_id}", tags=["Grupos"])
def eliminar_grupo(grupo_id: int, db: Session = Depends(get_db)):
    resultado = crud.delete_grupo(db, grupo_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return {"mensaje": "Grupo eliminado correctamente"}


# ==============================================================================
# ENDPOINTS: Aulas
# ==============================================================================
@app.get("/api/aulas", response_model=List[schemas.AulaOut], tags=["Aulas"])
def listar_aulas(db: Session = Depends(get_db)):
    return crud.get_aulas(db)

@app.post("/api/aulas", response_model=schemas.AulaOut, tags=["Aulas"])
def crear_aula(aula: schemas.AulaCreate, db: Session = Depends(get_db)):
    return crud.create_aula(db, aula)

@app.delete("/api/aulas/{aula_id}", tags=["Aulas"])
def eliminar_aula(aula_id: int, db: Session = Depends(get_db)):
    resultado = crud.delete_aula(db, aula_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    return {"mensaje": "Aula eliminada correctamente"}


# ==============================================================================
# ENDPOINTS: Franjas Horarias
# ==============================================================================
@app.get("/api/franjas", response_model=List[schemas.FranjaOut], tags=["Franjas"])
def listar_franjas(db: Session = Depends(get_db)):
    return crud.get_franjas(db)

@app.post("/api/franjas", response_model=schemas.FranjaOut, tags=["Franjas"])
def crear_franja(franja: schemas.FranjaCreate, db: Session = Depends(get_db)):
    return crud.create_franja(db, franja)

@app.delete("/api/franjas/{franja_id}", tags=["Franjas"])
def eliminar_franja(franja_id: int, db: Session = Depends(get_db)):
    resultado = crud.delete_franja(db, franja_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Franja no encontrada")
    return {"mensaje": "Franja eliminada correctamente"}


# ==============================================================================
# ENDPOINTS: Disponibilidad Docente (RH-01)
# ==============================================================================
@app.get("/api/disponibilidad", response_model=List[schemas.DisponibilidadOut], tags=["Disponibilidad"])
def listar_disponibilidades(db: Session = Depends(get_db)):
    return crud.get_disponibilidades(db)

@app.post("/api/disponibilidad", response_model=schemas.DisponibilidadOut, tags=["Disponibilidad"])
def crear_disponibilidad(disp: schemas.DisponibilidadCreate, db: Session = Depends(get_db)):
    return crud.create_disponibilidad(db, disp)

@app.delete("/api/disponibilidad/{disp_id}", tags=["Disponibilidad"])
def eliminar_disponibilidad(disp_id: int, db: Session = Depends(get_db)):
    resultado = crud.delete_disponibilidad(db, disp_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada")
    return {"mensaje": "Disponibilidad eliminada correctamente"}


# ==============================================================================
# ENDPOINTS: Elegibilidad Docente (RH-02)
# ==============================================================================
@app.get("/api/elegibilidad", response_model=List[schemas.ElegibilidadOut], tags=["Elegibilidad"])
def listar_elegibilidades(db: Session = Depends(get_db)):
    return crud.get_elegibilidades(db)

@app.post("/api/elegibilidad", response_model=schemas.ElegibilidadOut, tags=["Elegibilidad"])
def crear_elegibilidad(eleg: schemas.ElegibilidadCreate, db: Session = Depends(get_db)):
    return crud.create_elegibilidad(db, eleg)

@app.delete("/api/elegibilidad/{eleg_id}", tags=["Elegibilidad"])
def eliminar_elegibilidad(eleg_id: int, db: Session = Depends(get_db)):
    resultado = crud.delete_elegibilidad(db, eleg_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Elegibilidad no encontrada")
    return {"mensaje": "Elegibilidad eliminada correctamente"}


# ==============================================================================
# ENDPOINT PRINCIPAL: Generar Horario (Motor de Backtracking)
# ==============================================================================
@app.post("/api/generar-horario", tags=["Motor"])
def generar_horario(db: Session = Depends(get_db)):
    """
    Ejecuta el motor de backtracking y genera un horario.
    
    Flujo:
    1. Carga todos los datos del semestre en memoria
    2. Ejecuta GeneradorHorarios (backtracking)
    3. Persiste el resultado (asignaciones + conflictos) en la BD
    4. Retorna el horario con estado Valido o No_Factible
    
    Nota Celery (ampliación futura):
      En producción, este endpoint encolaría la tarea y retornaría un ID:
        tarea = tarea_generar_horario.delay(semestre_id)
        return {"tarea_id": tarea.id, "estado": "En proceso"}
      El frontend haría polling a GET /api/horario/{id}/estado
    """
    # Cargar datos del semestre en memoria (patrón Singleton)
    datos = crud.get_todos_los_datos(db)

    # Verificar que hay datos mínimos para generar
    if not datos["grupos"]:
        raise HTTPException(status_code=400, detail="No hay grupos registrados. Registra cursos y grupos antes de generar el horario.")
    if not datos["aulas"]:
        raise HTTPException(status_code=400, detail="No hay aulas registradas.")
    if not datos["franjas"]:
        raise HTTPException(status_code=400, detail="No hay franjas horarias registradas.")

    # Crear registro de horario en BD
    horario_db = crud.create_horario(db)

    # Ejecutar motor de backtracking
    motor = GeneradorHorarios(datos)
    resultado = motor.generar()

    # Persistir asignaciones en la BD
    puntaje_total = resultado.get("puntaje_total", 0.0)
    for asig in resultado.get("asignaciones", []):
        asignacion_db = models.Asignacion(
            id_sesion=0,          # Sesión virtual (MVP simplificado)
            id_docente=asig["docente"].id,
            id_aula=asig["aula"].id,
            id_franja=asig["franja"].id,
            id_horario=horario_db.id,
            estado="Valida",
            puntaje_penalizacion=asig.get("penalizacion", 0.0)
        )
        db.add(asignacion_db)

    # Persistir conflictos en la BD
    for conf in resultado.get("conflictos", []):
        conflicto_db = models.Conflicto(
            id_horario=horario_db.id,
            id_sesion=None,
            id_restriccion=conf.get("id_restriccion", "???"),
            descripcion=conf.get("descripcion", ""),
            entidad_tipo=conf.get("entidad_tipo", "Sistema"),
            entidad_id=conf.get("entidad_id", 0)
        )
        db.add(conflicto_db)

    # Actualizar estado del horario
    estado_final = "Valido" if resultado["exito"] else "No_Factible"
    horario_db.estado = estado_final
    horario_db.puntaje_total = puntaje_total
    db.commit()
    db.refresh(horario_db)

    # Construir respuesta enriquecida para el frontend
    asignaciones_out = _construir_asignaciones_out(resultado.get("asignaciones", []), horario_db.id)

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
    """Construye la lista de asignaciones para el frontend con datos expandidos."""
    resultado = []
    for asig in asignaciones:
        resultado.append({
            "horario_id": horario_id,
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
# ENDPOINTS: Consulta de Horarios Generados
# ==============================================================================
@app.get("/api/horarios", tags=["Horarios"])
def listar_horarios(db: Session = Depends(get_db)):
    """Lista todos los horarios generados (más reciente primero)."""
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
def obtener_horario(horario_id: int, db: Session = Depends(get_db)):
    """Obtiene el detalle completo de un horario generado."""
    horario = crud.get_horario(db, horario_id)
    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    asignaciones_out = []
    for asig in horario.asignaciones:
        asignaciones_out.append({
            "id": asig.id,
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
def publicar_horario(horario_id: int, db: Session = Depends(get_db)):
    """Marca un horario como oficial e inmutable (RH-14)."""
    horario = crud.publicar_horario(db, horario_id)
    if not horario:
        raise HTTPException(status_code=400, detail="Solo se pueden publicar horarios con estado Valido")
    return {"mensaje": "Horario publicado como oficial", "horario_id": horario_id}

@app.delete("/api/horarios/{horario_id}", tags=["Horarios"])
def eliminar_horario(horario_id: int, db: Session = Depends(get_db)):
    """Elimina un horario (solo si no es oficial)."""
    resultado = crud.delete_horario(db, horario_id)
    if not resultado:
        raise HTTPException(status_code=400, detail="No se puede eliminar: horario no encontrado o es oficial")
    return {"mensaje": "Horario eliminado correctamente"}


# ==============================================================================
# ENDPOINT: Datos de ejemplo para pruebas rápidas
# ==============================================================================
@app.post("/api/cargar-datos-ejemplo", tags=["Utilidades"])
def cargar_datos_ejemplo(db: Session = Depends(get_db)):
    """
    Carga datos de prueba para demostrar el funcionamiento del motor.
    Útil para la primera ejecución del MVP.
    """
    try:
        # Franjas horarias
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

        # Aulas
        aulas_data = [
            {"codigo": "A-101", "capacidad": 40, "edificio": "Bloque A"},
            {"codigo": "A-201", "capacidad": 35, "edificio": "Bloque A"},
            {"codigo": "LAB-01", "capacidad": 30, "tiene_computadores": True, "edificio": "Laboratorios"},
        ]
        aulas_creadas = []
        for a in aulas_data:
            aula = crud.create_aula(db, schemas.AulaCreate(**a))
            aulas_creadas.append(aula)

        # Docentes
        docentes_data = [
            {"nombre": "Carlos García", "correo": "cgarcia@unbosque.edu.co", "tipo_vinculacion": "TC"},
            {"nombre": "María López", "correo": "mlopez@unbosque.edu.co", "tipo_vinculacion": "MT"},
            {"nombre": "Andrés Rodríguez", "correo": "arodriguez@unbosque.edu.co", "tipo_vinculacion": "TC"},
        ]
        docentes_creados = []
        for d in docentes_data:
            docente = crud.create_docente(db, schemas.DocenteCreate(**d))
            docentes_creados.append(docente)

        # Cursos
        cursos_data = [
            {"nombre": "Cálculo Diferencial", "codigo": "MAT101", "creditos": 4, "sesiones_semana": 2},
            {"nombre": "Programación I", "codigo": "SIS101", "creditos": 3, "sesiones_semana": 2, "requiere_computadores": True},
            {"nombre": "Bases de Datos", "codigo": "SIS201", "creditos": 3, "sesiones_semana": 2, "requiere_computadores": True},
        ]
        cursos_creados = []
        for c in cursos_data:
            curso = crud.create_curso(db, schemas.CursoCreate(**c))
            cursos_creados.append(curso)

        # Grupos
        grupos_data = [
            {"id_curso": cursos_creados[0].id, "nombre_grupo": "CAL-01", "cupo_objetivo": 35, "inscritos": 30},
            {"id_curso": cursos_creados[1].id, "nombre_grupo": "SIS-01", "cupo_objetivo": 30, "inscritos": 25},
            {"id_curso": cursos_creados[2].id, "nombre_grupo": "BD-01", "cupo_objetivo": 28, "inscritos": 22},
        ]
        grupos_creados = []
        for g in grupos_data:
            grupo = crud.create_grupo(db, schemas.GrupoCreate(**g))
            grupos_creados.append(grupo)

        # Elegibilidades
        eleg_data = [
            {"id_docente": docentes_creados[0].id, "id_curso": cursos_creados[0].id},
            {"id_docente": docentes_creados[1].id, "id_curso": cursos_creados[1].id},
            {"id_docente": docentes_creados[2].id, "id_curso": cursos_creados[2].id},
            {"id_docente": docentes_creados[0].id, "id_curso": cursos_creados[2].id},
        ]
        for e in eleg_data:
            crud.create_elegibilidad(db, schemas.ElegibilidadCreate(**e))

        # Disponibilidades (todos los docentes disponibles en todas las franjas no bloqueadas)
        franjas_activas = [f for f in franjas_creadas if not f.bloqueada]
        for docente in docentes_creados:
            for franja in franjas_activas:
                crud.create_disponibilidad(db, schemas.DisponibilidadCreate(
                    id_docente=docente.id, id_franja=franja.id
                ))

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
