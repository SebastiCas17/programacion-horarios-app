"""
motor/validador.py
==================
Validador de Restricciones Duras.
Implementa el patrón Strategy: cada restricción es una función independiente
que recibe un candidato y el estado actual del horario.

Restricciones implementadas:
- RA-01: No solapamiento de docente
- RA-02: No solapamiento de aula
- RA-03: No solapamiento de grupo
- RH-01: Disponibilidad del docente
- RH-02: Elegibilidad docente-curso
- RH-05: Franja no bloqueada
- RH-07: Recursos del aula compatibles con el curso
- RH-09: Capacidad del aula >= inscritos del grupo
"""


class ResultadoValidacion:
    """
    Resultado de evaluar un candidato contra las restricciones duras.
    Si valida = False, incluye el ID de restricción violada y descripción.
    """
    def __init__(self, valida: bool = True, id_restriccion: str = "", descripcion: str = "", entidad_tipo: str = "", entidad_id: int = 0):
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


def validar_candidato(candidato: dict, asignaciones_actuales: list, datos: dict) -> ResultadoValidacion:
    """
    Evalúa un candidato (docente, aula, franja) contra TODAS las restricciones duras.
    
    Args:
        candidato: dict con claves 'docente', 'aula', 'franja', 'sesion', 'grupo', 'curso'
        asignaciones_actuales: lista de candidatos ya asignados en este horario
        datos: diccionario con todos los datos del semestre
    
    Returns:
        ResultadoValidacion — si valida=False, el motor descarta este candidato
    """
    docente = candidato["docente"]
    aula = candidato["aula"]
    franja = candidato["franja"]
    sesion = candidato["sesion"]
    grupo = candidato["grupo"]
    curso = candidato["curso"]

    # ------------------------------------------------------------------
    # RH-05: La franja no debe estar bloqueada
    # ------------------------------------------------------------------
    if franja.bloqueada:
        return ResultadoValidacion.fallo(
            "RH-05",
            f"La franja {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin} está bloqueada (ej: horario de almuerzo).",
            "Franja", franja.id
        )

    # ------------------------------------------------------------------
    # RH-01: El docente debe estar disponible en esta franja
    # ------------------------------------------------------------------
    disponibilidades_docente = [
        d.id_franja for d in datos["disponibilidades"]
        if d.id_docente == docente.id
    ]
    if disponibilidades_docente and franja.id not in disponibilidades_docente:
        return ResultadoValidacion.fallo(
            "RH-01",
            f"El docente '{docente.nombre}' no está disponible el {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
            "Docente", docente.id
        )

    # ------------------------------------------------------------------
    # RH-02: El docente debe ser elegible para este curso
    # ------------------------------------------------------------------
    elegibles_curso = [
        e.id_docente for e in datos["elegibilidades"]
        if e.id_curso == curso.id and e.activo
    ]
    if elegibles_curso and docente.id not in elegibles_curso:
        return ResultadoValidacion.fallo(
            "RH-02",
            f"El docente '{docente.nombre}' no está habilitado para dictar el curso '{curso.nombre}'.",
            "Docente", docente.id
        )

    # ------------------------------------------------------------------
    # RH-07: El aula debe tener los recursos requeridos por el curso
    # ------------------------------------------------------------------
    if curso.requiere_computadores and not aula.tiene_computadores:
        return ResultadoValidacion.fallo(
            "RH-07",
            f"El curso '{curso.nombre}' requiere computadores, pero el aula '{aula.codigo}' no los tiene.",
            "Aula", aula.id
        )
    if curso.requiere_sillas_moviles and not aula.tiene_sillas_moviles:
        return ResultadoValidacion.fallo(
            "RH-07",
            f"El curso '{curso.nombre}' requiere sillas móviles, pero el aula '{aula.codigo}' no las tiene.",
            "Aula", aula.id
        )

    # ------------------------------------------------------------------
    # RH-09: La capacidad del aula >= inscritos del grupo
    # ------------------------------------------------------------------
    inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo
    if aula.capacidad < inscritos:
        return ResultadoValidacion.fallo(
            "RH-09",
            f"El aula '{aula.codigo}' tiene capacidad {aula.capacidad}, pero el grupo '{grupo.nombre_grupo}' tiene {inscritos} estudiantes.",
            "Aula", aula.id
        )

    # ------------------------------------------------------------------
    # RA-01: El docente no puede estar en dos sesiones en la misma franja
    # ------------------------------------------------------------------
    for asig in asignaciones_actuales:
        if asig["docente"].id == docente.id and asig["franja"].id == franja.id:
            return ResultadoValidacion.fallo(
                "RA-01",
                f"El docente '{docente.nombre}' ya tiene una sesión asignada el {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
                "Docente", docente.id
            )

    # ------------------------------------------------------------------
    # RA-02: El aula no puede tener dos sesiones en la misma franja
    # ------------------------------------------------------------------
    for asig in asignaciones_actuales:
        if asig["aula"].id == aula.id and asig["franja"].id == franja.id:
            return ResultadoValidacion.fallo(
                "RA-02",
                f"El aula '{aula.codigo}' ya está ocupada el {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
                "Aula", aula.id
            )

    # ------------------------------------------------------------------
    # RA-03: El grupo no puede estar en dos sesiones en la misma franja
    # ------------------------------------------------------------------
    for asig in asignaciones_actuales:
        if asig["grupo"].id == grupo.id and asig["franja"].id == franja.id:
            return ResultadoValidacion.fallo(
                "RA-03",
                f"El grupo '{grupo.nombre_grupo}' ya tiene una sesión el {franja.dia_semana} {franja.hora_inicio}-{franja.hora_fin}.",
                "Grupo", grupo.id
            )

    # Todos los chequeos pasaron — candidato válido
    return ResultadoValidacion.ok()
