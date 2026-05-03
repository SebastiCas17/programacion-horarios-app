"""
motor/restricciones.py
======================
Restricciones Blandas — Cálculo de penalizaciones.
No invalidan la asignación, pero influyen en la calidad del horario.

RS-01: Penalización por sesiones del mismo grupo en días consecutivos.
RS-02: Penalización leve por sobrecarga docente.
RS-03: Penalización leve por usar docente flexible en lugar de docente explícitamente autorizado.
"""

ORDEN_DIAS = {
    "Lunes": 1,
    "Martes": 2,
    "Miercoles": 3,
    "Miércoles": 3,
    "Jueves": 4,
    "Viernes": 5,
    "Sabado": 6,
    "Sábado": 6
}

PENALIZACION_DIAS_CONSECUTIVOS = 10.0
PENALIZACION_SOBRECARGA_DOCENTE = 5.0
PENALIZACION_DOCENTE_FLEXIBLE = 2.0


def _dia_orden(dia: str) -> int:
    return ORDEN_DIAS.get(dia, 0)


def calcular_penalizacion(candidato: dict, asignaciones_actuales: list) -> float:
    """
    Calcula la penalización total de un candidato dadas las asignaciones ya hechas.
    0.0 significa que el candidato no tiene penalización blanda.
    """

    penalizacion = 0.0

    penalizacion += _penalizacion_dias_consecutivos_mismo_grupo(
        candidato,
        asignaciones_actuales
    )

    penalizacion += _penalizacion_sobrecarga_docente(
        candidato,
        asignaciones_actuales
    )

    penalizacion += _penalizacion_docente_flexible(candidato)

    return penalizacion


def _penalizacion_dias_consecutivos_mismo_grupo(candidato: dict, asignaciones_actuales: list) -> float:
    """
    RS-01:
    Penaliza si una sesión del mismo grupo queda en días consecutivos.
    """

    penalizacion = 0.0

    grupo_actual = candidato["grupo"]
    dia_actual = _dia_orden(candidato["franja"].dia_semana)

    if dia_actual == 0:
        return 0.0

    for asig in asignaciones_actuales:
        if asig["grupo"].id == grupo_actual.id:
            dia_existente = _dia_orden(asig["franja"].dia_semana)

            if dia_existente > 0 and abs(dia_actual - dia_existente) == 1:
                penalizacion += PENALIZACION_DIAS_CONSECUTIVOS

    return penalizacion


def _penalizacion_sobrecarga_docente(candidato: dict, asignaciones_actuales: list) -> float:
    """
    RS-02:
    Penaliza levemente si el docente ya tiene varias sesiones asignadas.
    Esto ayuda a distribuir mejor la carga docente.
    """

    docente_actual = candidato["docente"]

    sesiones_docente = sum(
        1 for asig in asignaciones_actuales
        if asig["docente"].id == docente_actual.id
    )

    if sesiones_docente >= 4:
        return PENALIZACION_SOBRECARGA_DOCENTE

    return 0.0


def _penalizacion_docente_flexible(candidato: dict) -> float:
    """
    RS-03:
    Penaliza levemente el uso de docentes flexibles.
    Esto permite usarlos cuando sea necesario, pero prioriza docentes explícitamente autorizados.
    """

    if candidato.get("docente_flexible", False):
        return PENALIZACION_DOCENTE_FLEXIBLE

    return 0.0


def generar_reporte_blandas(asignaciones: list) -> dict:
    """
    Genera un reporte de calidad del horario.
    """

    if not asignaciones:
        return {
            "indice_consecutividad": 0,
            "pares_consecutivos": 0,
            "aprovechamiento_docente": {},
            "docentes_flexibles_usados": 0,
            "total_sesiones_asignadas": 0
        }

    pares_consecutivos = 0
    grupos_vistos = {}

    for asig in asignaciones:
        grupo_id = asig["grupo"].id
        dia = _dia_orden(asig["franja"].dia_semana)

        if dia == 0:
            continue

        if grupo_id not in grupos_vistos:
            grupos_vistos[grupo_id] = []

        grupos_vistos[grupo_id].append(dia)

    for grupo_id, dias in grupos_vistos.items():
        dias_ordenados = sorted(dias)

        for i in range(len(dias_ordenados) - 1):
            if dias_ordenados[i + 1] - dias_ordenados[i] == 1:
                pares_consecutivos += 1

    aprovechamiento = {}
    docentes_flexibles_usados = 0

    for asig in asignaciones:
        nombre_docente = asig["docente"].nombre
        aprovechamiento[nombre_docente] = aprovechamiento.get(nombre_docente, 0) + 1

        if asig.get("docente_flexible", False):
            docentes_flexibles_usados += 1

    return {
        "indice_consecutividad": pares_consecutivos,
        "pares_consecutivos": pares_consecutivos,
        "aprovechamiento_docente": aprovechamiento,
        "docentes_flexibles_usados": docentes_flexibles_usados,
        "total_sesiones_asignadas": len(asignaciones)
    }