"""
motor/generador.py
==================
Motor de Generación de Horarios — Algoritmo de Backtracking.

Implementa la lógica descrita en el Anexo D del documento de diseño:
1. Ordenar sesiones por dificultad (heurística)
2. Generar candidatos (docente × aula × franja)
3. Validar restricciones duras
4. Calcular penalización por restricciones blandas
5. Retroceder si no hay candidatos válidos

Nota sobre Celery/Redis:
  En producción, este generador se ejecutaría como una tarea Celery asíncrona:
  
  @celery_app.task
  def tarea_generar_horario(datos_id: int):
      datos = cargar_datos(datos_id)
      return GeneradorHorarios(datos).generar()
  
  En el MVP se ejecuta síncrono desde el endpoint FastAPI.
"""

from motor.validador import validar_candidato
from motor.restricciones import calcular_penalizacion, generar_reporte_blandas


class GeneradorHorarios:
    """
    Motor de backtracking para generación de horarios académicos.
    
    Recibe todos los datos del semestre cargados en memoria (patrón Singleton
    de ParametroSemestre) y produce un resultado con asignaciones y/o conflictos.
    """

    def __init__(self, datos: dict):
        """
        Args:
            datos: dict con claves 'docentes', 'cursos', 'grupos', 'aulas',
                   'franjas', 'disponibilidades', 'elegibilidades'
        """
        self.datos = datos
        self.asignaciones = []   # Lista de candidatos exitosamente asignados
        self.conflictos = []     # Lista de conflictos detectados

def generar(self) -> dict:
    """
    Punto de entrada principal del motor.
    Ejecuta backtracking respetando parámetros del semestre y restricciones.
    """
    self.asignaciones = []
    self.conflictos = []

    # Paso 1: Construir sesiones a asignar
    sesiones = self._construir_sesiones()

    if not sesiones:
        return {
            "exito": False,
            "asignaciones": [],
            "conflictos": self.conflictos if self.conflictos else [
                {
                    "id_restriccion": "CONFIG",
                    "descripcion": "No hay sesiones para programar. Verifica que existan grupos activos con cursos válidos.",
                    "entidad_tipo": "Sistema",
                    "entidad_id": 0
                }
            ],
            "puntaje_total": 0.0,
            "reporte_blandas": {}
        }

    # Paso 2: Ordenar por dificultad
    sesiones_ordenadas = self._ordenar_por_dificultad(sesiones)

    # Paso 3: Backtracking
    exito = self._backtrack(0, sesiones_ordenadas)

    puntaje_total = sum(a.get("penalizacion", 0.0) for a in self.asignaciones)
    reporte = generar_reporte_blandas(self.asignaciones)

    return {
        "exito": exito,
        "asignaciones": self.asignaciones,
        "conflictos": self.conflictos,
        "puntaje_total": puntaje_total,
        "reporte_blandas": reporte
    }

def _construir_sesiones(self) -> list:
    """
    Construye la lista de sesiones a programar.
    Aplica RH-10, RH-11, RH-15 y RH-16 antes del backtracking.
    """
    sesiones = []
    grupos = self.datos.get("grupos", [])
    cursos_por_id = {c.id: c for c in self.datos.get("cursos", [])}
    parametro = self.datos.get("parametro_semestre")

    max_sesiones = parametro.max_sesiones_semana if parametro else 4
    min_cierre = parametro.min_inscritos_cierre if parametro else 10

    for grupo in grupos:
        if grupo.estado == "Cerrado":
            continue

        curso = cursos_por_id.get(grupo.id_curso)

        if not curso or not curso.estado:
            continue

        # RH-15: grupos con inscritos menores al mínimo configurable
        if grupo.inscritos is not None and grupo.inscritos > 0 and grupo.inscritos < min_cierre:
            self.conflictos.append({
                "id_restriccion": "RH-15",
                "descripcion": f"El grupo '{grupo.nombre_grupo}' tiene {grupo.inscritos} inscritos, menor al mínimo configurable de {min_cierre}. Debe marcarse como candidato a cierre.",
                "entidad_tipo": "Grupo",
                "entidad_id": grupo.id
            })
            continue

        # RH-10: cada curso debe tener al menos una sesión por semana
        if curso.sesiones_semana < 1:
            self.conflictos.append({
                "id_restriccion": "RH-10",
                "descripcion": f"El curso '{curso.nombre}' no tiene sesiones semanales configuradas.",
                "entidad_tipo": "Curso",
                "entidad_id": curso.id
            })
            continue

        # RH-11 y RH-16: máximo de sesiones parametrizable
        if curso.sesiones_semana > max_sesiones:
            self.conflictos.append({
                "id_restriccion": "RH-11/RH-16",
                "descripcion": f"El curso '{curso.nombre}' tiene {curso.sesiones_semana} sesiones, superando el máximo configurable de {max_sesiones}.",
                "entidad_tipo": "Curso",
                "entidad_id": curso.id
            })
            continue

        for num_sesion in range(1, curso.sesiones_semana + 1):
            sesiones.append({
                "grupo": grupo,
                "curso": curso,
                "num_sesion": num_sesion,
                "sesion_key": f"grupo{grupo.id}_sesion{num_sesion}"
            })

    return sesiones

    def _ordenar_por_dificultad(self, sesiones: list) -> list:
        """
        Heurística de ordenamiento: las sesiones más difíciles de asignar van primero.
        La dificultad = número de candidatos posibles (menor candidatos → más difícil).
        
        Esto reduce el retroceso tardío (fail-first principle).
        """
        def dificultad(sesion):
            num_candidatos = len(self._generar_candidatos(sesion))
            return num_candidatos  # Menor = más difícil = va primero

        return sorted(sesiones, key=dificultad)

    def _backtrack(self, indice: int, sesiones: list) -> bool:
        """
        Algoritmo de búsqueda con retroceso.
        
        Args:
            indice: posición actual en la lista de sesiones
            sesiones: lista completa de sesiones ordenadas por dificultad
        
        Returns:
            True si se encontró una asignación válida para todas las sesiones
        """
        # Caso base: todas las sesiones fueron asignadas exitosamente
        if indice == len(sesiones):
            return True

        sesion_actual = sesiones[indice]

        # Generar todos los candidatos válidos para esta sesión
        candidatos = self._generar_candidatos(sesion_actual)

        # Ordenar candidatos por penalización ascendente (menor penalización primero)
        candidatos_evaluados = []
        for candidato in candidatos:
            resultado = validar_candidato(candidato, self.asignaciones, self.datos)
            if resultado.valida:
                penalizacion = calcular_penalizacion(candidato, self.asignaciones)
                candidatos_evaluados.append((penalizacion, candidato))

        # Ordenar por penalización (greedy: intentar primero el mejor candidato)
        candidatos_evaluados.sort(key=lambda x: x[0])

        # Intentar cada candidato válido
        for penalizacion, candidato in candidatos_evaluados:
            # Asignación tentativa
            candidato["penalizacion"] = penalizacion
            self.asignaciones.append(candidato)

            # Llamada recursiva: intentar asignar la siguiente sesión
            if self._backtrack(indice + 1, sesiones):
                return True  # ¡Éxito! Propagamos hacia arriba

            # Retroceso (backtrack): esta asignación no llevó a solución completa
            self.asignaciones.pop()

        # Sin candidatos válidos para esta sesión — registrar conflicto
        self._registrar_conflicto_sin_candidatos(sesion_actual)
        return False

    def _generar_candidatos(self, sesion: dict) -> list:
        """
        Genera todas las combinaciones posibles de (docente, aula, franja)
        para una sesión dada, aplicando filtros básicos pre-validación.
        
        Implementa el Builder de candidatos del documento de diseño.
        """
        grupo = sesion["grupo"]
        curso = sesion["curso"]
        candidatos = []

        # Filtrar docentes elegibles para este curso
        docentes_elegibles_ids = set(
            e.id_docente for e in self.datos.get("elegibilidades", [])
            if e.id_curso == curso.id and e.activo
        )
        # Si no hay elegibilidades definidas, usar todos los docentes activos
        if not docentes_elegibles_ids:
            docentes_candidatos = self.datos.get("docentes", [])
        else:
            docentes_candidatos = [
                d for d in self.datos.get("docentes", [])
                if d.id in docentes_elegibles_ids and d.estado
            ]

        # Filtrar aulas con suficiente capacidad y recursos compatibles
        inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo
        aulas_candidatas = [
            a for a in self.datos.get("aulas", [])
            if a.capacidad >= inscritos
            and a.estado
            and (not curso.requiere_computadores or a.tiene_computadores)
            and (not curso.requiere_sillas_moviles or a.tiene_sillas_moviles)
        ]

        # Franjas no bloqueadas
        franjas_disponibles = [
            f for f in self.datos.get("franjas", [])
            if not f.bloqueada
        ]

        # Construir combinaciones — el validador hará la validación completa
        for docente in docentes_candidatos:
            for franja in franjas_disponibles:
                for aula in aulas_candidatas:
                    candidatos.append({
                        "docente": docente,
                        "aula": aula,
                        "franja": franja,
                        "sesion": sesion,
                        "grupo": grupo,
                        "curso": curso,
                    })

        return candidatos

    def _registrar_conflicto_sin_candidatos(self, sesion: dict):
        """
        Registra un conflicto cuando ningún candidato es válido para una sesión.
        Incluye el ID de restricción más probable y descripción en lenguaje de dominio.
        """
        grupo = sesion["grupo"]
        curso = sesion["curso"]

        # Intentar identificar la causa más probable del conflicto
        candidatos_raw = self._generar_candidatos(sesion)

        if not candidatos_raw:
            # No hay candidatos en absoluto — problema de configuración
            descripcion = (
                f"No hay candidatos para el grupo '{grupo.nombre_grupo}' "
                f"(curso: '{curso.nombre}', sesión {sesion['num_sesion']}). "
                f"Verifica que existan docentes elegibles, aulas con capacidad "
                f"suficiente ({grupo.cupo_objetivo} estudiantes) y franjas disponibles."
            )
            id_restriccion = "RH-08"
        else:
            # Hay candidatos pero todos fallaron validación — verificar cuál falla primero
            primer_resultado = validar_candidato(
                candidatos_raw[0], self.asignaciones, self.datos
            )
            id_restriccion = primer_resultado.id_restriccion or "RA-01"
            descripcion = (
                f"No se pudo asignar el grupo '{grupo.nombre_grupo}' "
                f"(curso: '{curso.nombre}', sesión {sesion['num_sesion']}). "
                f"Causa probable — {primer_resultado.descripcion}"
            )

        self.conflictos.append({
            "id_restriccion": id_restriccion,
            "descripcion": descripcion,
            "entidad_tipo": "Grupo",
            "entidad_id": grupo.id,
            "sesion_key": sesion.get("sesion_key", "")
        })
