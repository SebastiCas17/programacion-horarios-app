"""
motor/restricciones.py
======================
Restricciones Blandas — Cálculo de penalizaciones.
No invalidan la asignación, pero influyen en la calidad del horario.

RS-01: Penalización por sesiones del mismo curso en días consecutivos
RS-02: Penalización por bajo aprovechamiento docente
"""

# Orden de los días para calcular consecutividad
ORDEN_DIAS = {
    "Lunes": 1, "Martes": 2, "Miercoles": 3,
    "Jueves": 4, "Viernes": 5, "Sabado": 6
}

# Penalizaciones configurables (en el documento: ParametroSemestre)
PENALIZACION_DIAS_CONSECUTIVOS = 10.0   # RS-01: por cada par de sesiones consecutivas del mismo curso
PENALIZACION_BAJO_APROVECHAMIENTO = 5.0  # RS-02: si docente tiene menos de 2 sesiones en el horario


def calcular_penalizacion(candidato: dict, asignaciones_actuales: list) -> float:
    """
    Calcula la penalización total de un candidato dadas las asignaciones ya hechas.
    
    Args:
        candidato: dict con 'docente', 'aula', 'franja', 'sesion', 'grupo', 'curso'
        asignaciones_actuales: lista de asignaciones ya realizadas en este horario
    
    Returns:
        float — puntaje de penalización (0.0 = sin penalización)
    """
    penalizacion = 0.0

    penalizacion += _penalizacion_dias_consecutivos(candidato, asignaciones_actuales)
    penalizacion += _penalizacion_bajo_aprovechamiento(candidato, asignaciones_actuales)

    return penalizacion


def _penalizacion_dias_consecutivos(candidato: dict, asignaciones_actuales: list) -> float:
    """
    RS-01: Penaliza si este candidato crea sesiones del mismo curso en días consecutivos.
    
    Ejemplo: Cálculo de Diferencial en Lunes y Martes → penalización porque son días seguidos.
    La preferencia es que las sesiones de un mismo curso estén distribuidas (ej: Lunes y Miércoles).
    """
    penalizacion = 0.0
    curso_actual = candidato["curso"]
    dia_actual = ORDEN_DIAS.get(candidato["franja"].dia_semana, 0)

    if dia_actual == 0:
        return 0.0

    # Buscar otras sesiones del mismo curso ya asignadas
    for asig in asignaciones_actuales:
        if asig["curso"].id == curso_actual.id:
            dia_existente = ORDEN_DIAS.get(asig["franja"].dia_semana, 0)
            if dia_existente > 0 and abs(dia_actual - dia_existente) == 1:
                # Son días consecutivos
                penalizacion += PENALIZACION_DIAS_CONSECUTIVOS

    return penalizacion


def _penalizacion_bajo_aprovechamiento(candidato: dict, asignaciones_actuales: list) -> float:
    """
    RS-02: Penaliza si se asigna un docente diferente cuando hay un docente con pocas horas.
    
    Lógica simplificada: cuenta cuántas sesiones tiene asignadas el docente candidato.
    Si ya tiene muchas, penaliza para distribuir carga entre docentes.
    """
    penalizacion = 0.0
    docente_actual = candidato["docente"]

    # Contar sesiones actuales del docente
    sesiones_docente = sum(
        1 for asig in asignaciones_actuales
        if asig["docente"].id == docente_actual.id
    )

    # Si el docente ya tiene muchas sesiones (más de 4), aplicar penalización leve
    # para incentivar distribución de carga
    if sesiones_docente > 4:
        penalizacion += PENALIZACION_BAJO_APROVECHAMIENTO

    return penalizacion


def generar_reporte_blandas(asignaciones: list) -> dict:
    """
    Genera un reporte con las métricas de restricciones blandas del horario completo.
    Se usa para mostrar en la interfaz la calidad del horario generado.
    
    Returns:
        dict con índices de calidad del horario
    """
    if not asignaciones:
        return {"indice_consecutividad": 0, "pares_consecutivos": 0, "aprovechamiento_docente": {}}

    # Calcular pares consecutivos (RS-01)
    pares_consecutivos = 0
    cursos_vistos = {}
    for asig in asignaciones:
        curso_id = asig["curso"].id
        dia = ORDEN_DIAS.get(asig["franja"].dia_semana, 0)
        if curso_id not in cursos_vistos:
            cursos_vistos[curso_id] = []
        cursos_vistos[curso_id].append(dia)

    for curso_id, dias in cursos_vistos.items():
        dias_sorted = sorted(dias)
        for i in range(len(dias_sorted) - 1):
            if dias_sorted[i + 1] - dias_sorted[i] == 1:
                pares_consecutivos += 1

    # Calcular aprovechamiento por docente (RS-02)
    aprovechamiento = {}
    for asig in asignaciones:
        nombre = asig["docente"].nombre
        aprovechamiento[nombre] = aprovechamiento.get(nombre, 0) + 1

    return {
        "indice_consecutividad": pares_consecutivos,
        "pares_consecutivos": pares_consecutivos,
        "aprovechamiento_docente": aprovechamiento,
        "total_sesiones_asignadas": len(asignaciones)
    }
