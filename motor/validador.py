"""
motor/validador.py
==================
Validador de Restricciones Duras.
Implementa el patrón Strategy: cada restricción es una función independiente
que recibe un candidato y el estado actual del horario.

Lógica académica aplicada:
- RA-01: No solapamiento de docente.
- RA-02: No solapamiento de aula.
- RA-03: No solapamiento de grupo en la misma franja.
- RA-04: Un mismo grupo no debe tener más de una sesión el mismo día.
- RH-01: Disponibilidad docente opcional:
         Si el docente tiene disponibilidad registrada, se respeta.
         Si no tiene disponibilidad registrada, se considera flexible.
- RH-02: Elegibilidad docente-curso flexible:
         Si el docente está autorizado para el curso, puede dictarlo.
         Si el docente no tiene ninguna materia asignada en elegibilidad, puede actuar como flexible.
         Si el docente tiene elegibilidades para otros cursos, no puede dictar cursos no autorizados.
- RH-03: Rango académico lunes a viernes.
- RH-04: Rango académico sábado.
- RH-05: Franja no bloqueada ni solapada con almuerzo.
- RH-07: Recursos del aula compatibles con el curso.
- RH-09: Capacidad del aula >= inscritos del grupo.
"""


class ResultadoValidacion:
    """
    Resultado de evaluar un candidato contra las restricciones duras.
    Si valida = False, incluye el ID de restricción violada y descripción.
    """

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


def _hora_a_minutos(hora: str) -> int:
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


def _normalizar_dia(dia: str) -> str:
    if not dia:
        return ""

    return (
        dia.strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def _mismo_dia(franja_a, franja_b) -> bool:
    return _normalizar_dia(franja_a.dia_semana) == _normalizar_dia(franja_b.dia_semana)


def _dentro_de_rango(franja, inicio: str, fin: str) -> bool:
    inicio_franja = _hora_a_minutos(franja.hora_inicio)
    fin_franja = _hora_a_minutos(franja.hora_fin)
    inicio_rango = _hora_a_minutos(inicio)
    fin_rango = _hora_a_minutos(fin)

    return inicio_franja >= inicio_rango and fin_franja <= fin_rango


def _se_solapa_con_rango(franja, inicio: str, fin: str) -> bool:
    inicio_franja = _hora_a_minutos(franja.hora_inicio)
    fin_franja = _hora_a_minutos(franja.hora_fin)
    inicio_bloqueo = _hora_a_minutos(inicio)
    fin_bloqueo = _hora_a_minutos(fin)

    return inicio_franja < fin_bloqueo and fin_franja > inicio_bloqueo


def _franjas_se_solapan(franja_a, franja_b) -> bool:
    if not _mismo_dia(franja_a, franja_b):
        return False

    inicio_a = _hora_a_minutos(franja_a.hora_inicio)
    fin_a = _hora_a_minutos(franja_a.hora_fin)

    inicio_b = _hora_a_minutos(franja_b.hora_inicio)
    fin_b = _hora_a_minutos(franja_b.hora_fin)

    return inicio_a < fin_b and fin_a > inicio_b


def validar_candidato(candidato: dict, asignaciones_actuales: list, datos: dict) -> ResultadoValidacion:
    """
    Evalúa un candidato contra todas las restricciones duras.

    candidato:
    {
        docente,
        aula,
        franja,
        sesion,
        grupo,
        curso,
        docente_flexible
    }
    """

    docente = candidato["docente"]
    aula = candidato["aula"]
    franja = candidato["franja"]
    grupo = candidato["grupo"]
    curso = candidato["curso"]

    parametro = datos.get("parametro_semestre")

    # ------------------------------------------------------------------
    # RH-03, RH-04 y RH-05: rangos institucionales y almuerzo
    # ------------------------------------------------------------------
    if parametro:
        dia = _normalizar_dia(franja.dia_semana)

        if dia in ["lunes", "martes", "miercoles", "jueves", "viernes"]:
            if not _dentro_de_rango(franja, parametro.hora_inicio_lv, parametro.hora_fin_lv):
                return ResultadoValidacion.fallo(
                    "RH-03",
                    f"La franja {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin} está fuera del rango académico de lunes a viernes {parametro.hora_inicio_lv}-{parametro.hora_fin_lv}.",
                    "Franja",
                    franja.id
                )

        if dia == "sabado":
            if not _dentro_de_rango(franja, parametro.hora_inicio_sab, parametro.hora_fin_sab):
                return ResultadoValidacion.fallo(
                    "RH-04",
                    f"La franja de sábado {franja.hora_inicio}-{franja.hora_fin} está fuera del rango permitido {parametro.hora_inicio_sab}-{parametro.hora_fin_sab}.",
                    "Franja",
                    franja.id
                )

        if _se_solapa_con_rango(franja, parametro.inicio_almuerzo, parametro.fin_almuerzo):
            return ResultadoValidacion.fallo(
                "RH-05",
                f"La franja {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin} se solapa con el almuerzo {parametro.inicio_almuerzo}-{parametro.fin_almuerzo}.",
                "Franja",
                franja.id
            )

    # ------------------------------------------------------------------
    # RH-05: franja bloqueada
    # ------------------------------------------------------------------
    if franja.bloqueada:
        return ResultadoValidacion.fallo(
            "RH-05",
            f"La franja {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin} está bloqueada.",
            "Franja",
            franja.id
        )

    # ------------------------------------------------------------------
    # RH-01: disponibilidad docente opcional
    # Si tiene disponibilidad registrada, se exige cumplirla.
    # Si no tiene disponibilidad registrada, se considera flexible.
    # ------------------------------------------------------------------
    disponibilidades_docente = [
        d.id_franja for d in datos.get("disponibilidades", [])
        if d.id_docente == docente.id
    ]

    if disponibilidades_docente and franja.id not in disponibilidades_docente:
        return ResultadoValidacion.fallo(
            "RH-01",
            f"El docente '{docente.nombre}' tiene restricción horaria y no está disponible el {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
            "Docente",
            docente.id
        )

    # ------------------------------------------------------------------
    # RH-02: elegibilidad docente-curso flexible
    # ------------------------------------------------------------------
    elegibilidades_activas = [
        e for e in datos.get("elegibilidades", [])
        if e.activo
    ]

    elegibles_curso = [
        e.id_docente for e in elegibilidades_activas
        if e.id_curso == curso.id
    ]

    materias_docente = [
        e.id_curso for e in elegibilidades_activas
        if e.id_docente == docente.id
    ]

    docente_autorizado_para_curso = docente.id in elegibles_curso
    docente_sin_materias_asignadas = len(materias_docente) == 0

    if not docente_autorizado_para_curso and not docente_sin_materias_asignadas:
        return ResultadoValidacion.fallo(
            "RH-02",
            f"El docente '{docente.nombre}' no está habilitado para dictar el curso '{curso.nombre}' y ya tiene materias específicas registradas.",
            "Docente",
            docente.id
        )

    # ------------------------------------------------------------------
    # RH-07: recursos del aula
    # ------------------------------------------------------------------
    if curso.requiere_computadores and not aula.tiene_computadores:
        return ResultadoValidacion.fallo(
            "RH-07",
            f"El curso '{curso.nombre}' requiere computadores, pero el aula '{aula.codigo}' no los tiene.",
            "Aula",
            aula.id
        )

    if curso.requiere_sillas_moviles and not aula.tiene_sillas_moviles:
        return ResultadoValidacion.fallo(
            "RH-07",
            f"El curso '{curso.nombre}' requiere sillas móviles, pero el aula '{aula.codigo}' no las tiene.",
            "Aula",
            aula.id
        )

    # ------------------------------------------------------------------
    # RH-09: capacidad del aula
    # ------------------------------------------------------------------
    inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo

    if aula.capacidad < inscritos:
        return ResultadoValidacion.fallo(
            "RH-09",
            f"El aula '{aula.codigo}' tiene capacidad {aula.capacidad}, pero el grupo '{grupo.nombre_grupo}' requiere {inscritos} cupos.",
            "Aula",
            aula.id
        )

    # ------------------------------------------------------------------
    # RA-01: docente sin cruces por día/hora
    # ------------------------------------------------------------------
    for asig in asignaciones_actuales:
        if asig["docente"].id == docente.id and _franjas_se_solapan(asig["franja"], franja):
            return ResultadoValidacion.fallo(
                "RA-01",
                f"El docente '{docente.nombre}' ya tiene una sesión asignada el {franja.dia_semana} entre {asig['franja'].hora_inicio}-{asig['franja'].hora_fin}, lo cual se cruza con {franja.hora_inicio}-{franja.hora_fin}.",
                "Docente",
                docente.id
            )

    # ------------------------------------------------------------------
    # RA-02: aula sin cruces por día/hora
    # ------------------------------------------------------------------
    for asig in asignaciones_actuales:
        if asig["aula"].id == aula.id and _franjas_se_solapan(asig["franja"], franja):
            return ResultadoValidacion.fallo(
                "RA-02",
                f"El aula '{aula.codigo}' ya está ocupada el {franja.dia_semana} {asig['franja'].hora_inicio}-{asig['franja'].hora_fin}, lo cual se cruza con {franja.hora_inicio}-{franja.hora_fin}.",
                "Aula",
                aula.id
            )

    # ------------------------------------------------------------------
    # RA-03: grupo sin cruces por día/hora
    # ------------------------------------------------------------------
    for asig in asignaciones_actuales:
        if asig["grupo"].id == grupo.id and _franjas_se_solapan(asig["franja"], franja):
            return ResultadoValidacion.fallo(
                "RA-03",
                f"El grupo '{grupo.nombre_grupo}' ya tiene una sesión el {franja.dia_semana} {asig['franja'].hora_inicio}-{asig['franja'].hora_fin}, lo cual se cruza con {franja.hora_inicio}-{franja.hora_fin}.",
                "Grupo",
                grupo.id
            )

    # ------------------------------------------------------------------
    # RA-04: un mismo grupo no debe tener dos sesiones el mismo día
    # ------------------------------------------------------------------
    for asig in asignaciones_actuales:
        if asig["grupo"].id == grupo.id and _mismo_dia(asig["franja"], franja):
            return ResultadoValidacion.fallo(
                "RA-04",
                f"El grupo '{grupo.nombre_grupo}' ya tiene una sesión programada el día {franja.dia_semana}. Para distribuir la carga académica, no se permite más de una sesión del mismo grupo el mismo día.",
                "Grupo",
                grupo.id
            )

    return ResultadoValidacion.ok()