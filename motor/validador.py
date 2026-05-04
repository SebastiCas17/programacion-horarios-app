"""
motor/validador.py
==================
Validador de Restricciones Duras — Versión Optimizada.

Cambios respecto a la versión anterior:
- RH-01 y RH-02 ya no recorren listas: usan los índices precalculados del generador.
- RA-01, RA-02, RA-03, RA-04 usan los índices O(1) del generador cuando están disponibles.
  Si no se pasan índices (llamada directa), hacen el recorrido clásico como fallback.

Restricciones implementadas:
- RA-01: No solapamiento de docente.
- RA-02: No solapamiento de aula.
- RA-03: No solapamiento de grupo en la misma franja.
- RA-04: Un mismo grupo no puede tener más de una sesión el mismo día.
- RH-01: Disponibilidad docente (opcional — flexible si no tiene registrada).
- RH-02: Elegibilidad docente-curso (flexible si no tiene ninguna materia).
- RH-03: Rango académico lunes a viernes.
- RH-04: Rango académico sábado.
- RH-05: Franja no bloqueada ni solapada con almuerzo.
- RH-07: Recursos del aula compatibles con el curso.
- RH-09: Capacidad del aula >= inscritos del grupo.
"""


class ResultadoValidacion:
    def __init__(
        self,
        valida: bool = True,
        id_restriccion: str = "",
        descripcion: str = "",
        entidad_tipo: str = "",
        entidad_id: int = 0
    ):
        self.valida = valida
        self.id_restriccion = id_restriccion
        self.descripcion = descripcion
        self.entidad_tipo = entidad_tipo
        self.entidad_id = entidad_id

    @staticmethod
    def ok():
        return ResultadoValidacion(valida=True)

    @staticmethod
    def fallo(id_restriccion, descripcion, entidad_tipo="", entidad_id=0):
        return ResultadoValidacion(
            valida=False,
            id_restriccion=id_restriccion,
            descripcion=descripcion,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id
        )


# ==============================================================================
# Utilidades de tiempo y día
# ==============================================================================

def _hora_a_minutos(hora: str) -> int:
    h, m = hora.split(":")
    return int(h) * 60 + int(m)


def _normalizar_dia(dia: str) -> str:
    if not dia:
        return ""
    return (
        dia.strip().lower()
        .replace("á", "a").replace("é", "e")
        .replace("í", "i").replace("ó", "o").replace("ú", "u")
    )


def _mismo_dia(franja_a, franja_b) -> bool:
    return _normalizar_dia(franja_a.dia_semana) == _normalizar_dia(franja_b.dia_semana)


def _dentro_de_rango(franja, inicio: str, fin: str) -> bool:
    return (
        _hora_a_minutos(franja.hora_inicio) >= _hora_a_minutos(inicio)
        and _hora_a_minutos(franja.hora_fin) <= _hora_a_minutos(fin)
    )


def _se_solapa_con_rango(franja, inicio: str, fin: str) -> bool:
    return (
        _hora_a_minutos(franja.hora_inicio) < _hora_a_minutos(fin)
        and _hora_a_minutos(franja.hora_fin) > _hora_a_minutos(inicio)
    )


def _franjas_se_solapan(franja_a, franja_b) -> bool:
    if not _mismo_dia(franja_a, franja_b):
        return False
    return (
        _hora_a_minutos(franja_a.hora_inicio) < _hora_a_minutos(franja_b.hora_fin)
        and _hora_a_minutos(franja_a.hora_fin) > _hora_a_minutos(franja_b.hora_inicio)
    )


# ==============================================================================
# Validador principal
# ==============================================================================

def validar_candidato(
    candidato: dict,
    asignaciones_actuales: list,
    datos: dict,
    indices: dict = None
) -> ResultadoValidacion:
    """
    Evalúa un candidato contra todas las restricciones duras.

    El parámetro `indices` es opcional. Si se pasa (desde el generador optimizado),
    las validaciones RA-01..RA-04 se hacen en O(1). Si no se pasa, se hace
    el recorrido clásico O(n) como fallback.

    indices esperado:
    {
        "docente_franjas_usadas": dict[int, set],   # docente_id -> set(franja_id)
        "aula_franjas_usadas":    dict[int, set],   # aula_id    -> set(franja_id)
        "grupo_franjas_usadas":   dict[int, set],   # grupo_id   -> set(franja_id)
        "grupo_dias_usados":      dict[int, list],  # grupo_id   -> [dia_str, ...]
        "disponibilidad_por_docente": dict[int, set],  # docente_id -> set(franja_id)
        "elegibles_por_curso":    dict[int, set],   # curso_id   -> set(docente_id)
        "docentes_con_elegibilidad": set,           # set(docente_id)
    }
    """

    docente = candidato["docente"]
    aula    = candidato["aula"]
    franja  = candidato["franja"]
    grupo   = candidato["grupo"]
    curso   = candidato["curso"]

    parametro = datos.get("parametro_semestre")

    # ------------------------------------------------------------------
    # RH-03 / RH-04 / RH-05: rangos institucionales y almuerzo
    # ------------------------------------------------------------------
    if parametro:
        dia = _normalizar_dia(franja.dia_semana)

        if dia in ("lunes", "martes", "miercoles", "jueves", "viernes"):
            if not _dentro_de_rango(franja, parametro.hora_inicio_lv, parametro.hora_fin_lv):
                return ResultadoValidacion.fallo(
                    "RH-03",
                    f"Franja {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin} "
                    f"fuera del rango académico L-V ({parametro.hora_inicio_lv}-{parametro.hora_fin_lv}).",
                    "Franja", franja.id
                )

        elif dia == "sabado":
            if not _dentro_de_rango(franja, parametro.hora_inicio_sab, parametro.hora_fin_sab):
                return ResultadoValidacion.fallo(
                    "RH-04",
                    f"Franja sábado {franja.hora_inicio}-{franja.hora_fin} "
                    f"fuera del rango permitido ({parametro.hora_inicio_sab}-{parametro.hora_fin_sab}).",
                    "Franja", franja.id
                )

        if _se_solapa_con_rango(franja, parametro.inicio_almuerzo, parametro.fin_almuerzo):
            return ResultadoValidacion.fallo(
                "RH-05",
                f"Franja {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin} "
                f"se solapa con almuerzo ({parametro.inicio_almuerzo}-{parametro.fin_almuerzo}).",
                "Franja", franja.id
            )

    if franja.bloqueada:
        return ResultadoValidacion.fallo(
            "RH-05",
            f"La franja {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin} está bloqueada.",
            "Franja", franja.id
        )

    # ------------------------------------------------------------------
    # RH-07: recursos del aula
    # ------------------------------------------------------------------
    if curso.requiere_computadores and not aula.tiene_computadores:
        return ResultadoValidacion.fallo(
            "RH-07",
            f"Curso '{curso.nombre}' requiere computadores; aula '{aula.codigo}' no los tiene.",
            "Aula", aula.id
        )

    if curso.requiere_sillas_moviles and not aula.tiene_sillas_moviles:
        return ResultadoValidacion.fallo(
            "RH-07",
            f"Curso '{curso.nombre}' requiere sillas móviles; aula '{aula.codigo}' no las tiene.",
            "Aula", aula.id
        )

    # ------------------------------------------------------------------
    # RH-09: capacidad del aula
    # ------------------------------------------------------------------
    inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo
    if aula.capacidad < inscritos:
        return ResultadoValidacion.fallo(
            "RH-09",
            f"Aula '{aula.codigo}' (cap. {aula.capacidad}) insuficiente para "
            f"grupo '{grupo.nombre_grupo}' ({inscritos} inscritos).",
            "Aula", aula.id
        )

    # ------------------------------------------------------------------
    # RH-01: disponibilidad docente
    # ------------------------------------------------------------------
    if indices:
        disp = indices["disponibilidad_por_docente"].get(docente.id)
        if disp and franja.id not in disp:
            return ResultadoValidacion.fallo(
                "RH-01",
                f"Docente '{docente.nombre}' no disponible el "
                f"{franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
                "Docente", docente.id
            )
    else:
        # Fallback O(n)
        disp_ids = [
            d.id_franja for d in datos.get("disponibilidades", [])
            if d.id_docente == docente.id
        ]
        if disp_ids and franja.id not in disp_ids:
            return ResultadoValidacion.fallo(
                "RH-01",
                f"Docente '{docente.nombre}' no disponible el "
                f"{franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
                "Docente", docente.id
            )

    # ------------------------------------------------------------------
    # RH-02: elegibilidad docente-curso
    # ------------------------------------------------------------------
    if indices:
        elegibles = indices["elegibles_por_curso"].get(curso.id, set())
        con_elegibilidad = indices["docentes_con_elegibilidad"]
        autorizado = docente.id in elegibles
        flexible = docente.id not in con_elegibilidad
    else:
        # Fallback O(n)
        eleg_activas = [e for e in datos.get("elegibilidades", []) if e.activo]
        elegibles = {e.id_docente for e in eleg_activas if e.id_curso == curso.id}
        con_elegibilidad = {e.id_docente for e in eleg_activas}
        autorizado = docente.id in elegibles
        flexible = docente.id not in con_elegibilidad

    if not autorizado and not flexible:
        return ResultadoValidacion.fallo(
            "RH-02",
            f"Docente '{docente.nombre}' no habilitado para '{curso.nombre}'.",
            "Docente", docente.id
        )

    # ------------------------------------------------------------------
    # RA-01 / RA-02 / RA-03 / RA-04: solapamientos
    # Con índices: O(1). Sin índices: O(n) fallback.
    # ------------------------------------------------------------------
    if indices:
        fid = franja.id
        dia_actual = _normalizar_dia(franja.dia_semana)

        # RA-01: docente ya ocupa esa franja exacta
        if fid in indices["docente_franjas_usadas"].get(docente.id, set()):
            return ResultadoValidacion.fallo(
                "RA-01",
                f"Docente '{docente.nombre}' ya tiene clase en "
                f"{franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
                "Docente", docente.id
            )

        # RA-02: aula ya ocupada en esa franja exacta
        if fid in indices["aula_franjas_usadas"].get(aula.id, set()):
            return ResultadoValidacion.fallo(
                "RA-02",
                f"Aula '{aula.codigo}' ya ocupada en "
                f"{franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
                "Aula", aula.id
            )

        # RA-03: grupo ya tiene clase en esa franja exacta
        if fid in indices["grupo_franjas_usadas"].get(grupo.id, set()):
            return ResultadoValidacion.fallo(
                "RA-03",
                f"Grupo '{grupo.nombre_grupo}' ya tiene clase en "
                f"{franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
                "Grupo", grupo.id
            )

        # RA-04: grupo ya tiene sesión ese día
        dias_grupo = indices["grupo_dias_usados"].get(grupo.id, [])
        if any(_normalizar_dia(d) == dia_actual for d in dias_grupo):
            return ResultadoValidacion.fallo(
                "RA-04",
                f"Grupo '{grupo.nombre_grupo}' ya tiene sesión el {franja.dia_semana}. "
                f"No se permiten dos sesiones del mismo grupo en el mismo día.",
                "Grupo", grupo.id
            )

    else:
        # Fallback O(n) — mismo comportamiento que la versión original
        for asig in asignaciones_actuales:
            if asig["docente"].id == docente.id and _franjas_se_solapan(asig["franja"], franja):
                return ResultadoValidacion.fallo(
                    "RA-01",
                    f"Docente '{docente.nombre}' ya tiene sesión en "
                    f"{franja.dia_semana} {asig['franja'].hora_inicio}-{asig['franja'].hora_fin}.",
                    "Docente", docente.id
                )

        for asig in asignaciones_actuales:
            if asig["aula"].id == aula.id and _franjas_se_solapan(asig["franja"], franja):
                return ResultadoValidacion.fallo(
                    "RA-02",
                    f"Aula '{aula.codigo}' ya ocupada en "
                    f"{franja.dia_semana} {asig['franja'].hora_inicio}-{asig['franja'].hora_fin}.",
                    "Aula", aula.id
                )

        for asig in asignaciones_actuales:
            if asig["grupo"].id == grupo.id and _franjas_se_solapan(asig["franja"], franja):
                return ResultadoValidacion.fallo(
                    "RA-03",
                    f"Grupo '{grupo.nombre_grupo}' ya tiene clase en "
                    f"{franja.dia_semana} {asig['franja'].hora_inicio}-{asig['franja'].hora_fin}.",
                    "Grupo", grupo.id
                )

        for asig in asignaciones_actuales:
            if asig["grupo"].id == grupo.id and _mismo_dia(asig["franja"], franja):
                return ResultadoValidacion.fallo(
                    "RA-04",
                    f"Grupo '{grupo.nombre_grupo}' ya tiene sesión el {franja.dia_semana}.",
                    "Grupo", grupo.id
                )

    return ResultadoValidacion.ok()