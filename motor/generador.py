"""
motor/generador.py
==================
Motor de Generación de Horarios — Algoritmo de Backtracking Optimizado.

Optimizaciones aplicadas:
- Precálculo de todas las estructuras en __init__ (se hace una sola vez).
- Índices invertidos para detectar conflictos en O(1) en lugar de O(n).
- Poda temprana: se descartan combinaciones inválidas antes de llamar al validador.
- Límite de tiempo configurable como red de seguridad.
- Ordenamiento de sesiones por menor cantidad de candidatos (Most Constrained Variable).
"""

import time
from motor.validador import validar_candidato
from motor.restricciones import calcular_penalizacion, generar_reporte_blandas

TIEMPO_LIMITE_SEGUNDOS = 45


class GeneradorHorarios:
    """
    Motor de backtracking optimizado para generación de horarios académicos.
    """

    def __init__(self, datos: dict):
        self.datos = datos
        self.asignaciones = []
        self.conflictos = []
        self._inicio = None

        # ==============================================================
        # Precálculo de estructuras (se ejecuta una sola vez)
        # ==============================================================
        self._precalcular_estructuras()

    def _precalcular_estructuras(self):
        """
        Construye todos los índices y conjuntos necesarios para el motor.
        Llamar esto una sola vez evita recalcular en cada iteración del backtracking.
        """

        # Docentes activos indexados por ID
        self._docentes_por_id = {
            d.id: d
            for d in self.datos.get("docentes", [])
            if d.estado
        }

        # Cursos indexados por ID
        self._cursos_por_id = {
            c.id: c
            for c in self.datos.get("cursos", [])
            if c.estado
        }

        # Grupos indexados por ID
        self._grupos_por_id = {
            g.id: g
            for g in self.datos.get("grupos", [])
        }

        # Aulas activas
        self._aulas_activas = [
            a for a in self.datos.get("aulas", [])
            if a.estado
        ]

        # Franjas no bloqueadas
        self._franjas_disponibles = [
            f for f in self.datos.get("franjas", [])
            if not f.bloqueada
        ]

        # Elegibilidades activas: curso_id → set de docente_ids
        self._elegibles_por_curso: dict[int, set] = {}
        # Docentes que tienen AL MENOS una elegibilidad
        self._docentes_con_elegibilidad: set = set()

        for e in self.datos.get("elegibilidades", []):
            if not e.activo:
                continue
            self._docentes_con_elegibilidad.add(e.id_docente)
            if e.id_curso not in self._elegibles_por_curso:
                self._elegibles_por_curso[e.id_curso] = set()
            self._elegibles_por_curso[e.id_curso].add(e.id_docente)

        # Disponibilidades: docente_id → set de franja_ids
        self._disponibilidad_por_docente: dict[int, set] = {}
        for disp in self.datos.get("disponibilidades", []):
            if disp.id_docente not in self._disponibilidad_por_docente:
                self._disponibilidad_por_docente[disp.id_docente] = set()
            self._disponibilidad_por_docente[disp.id_docente].add(disp.id_franja)

        # Aulas por requisito (precalculado)
        self._aulas_con_computadores = [a for a in self._aulas_activas if a.tiene_computadores]
        self._aulas_con_sillas = [a for a in self._aulas_activas if a.tiene_sillas_moviles]

        # Candidatos de docente por curso (precalculado)
        self._candidatos_docente_por_curso: dict[int, list] = {}
        for curso in self._cursos_por_id.values():
            self._candidatos_docente_por_curso[curso.id] = self._calcular_docentes_para_curso(curso)

        # Franjas por docente (precalculado)
        self._franjas_por_docente: dict[int, list] = {}
        for docente_id in self._docentes_por_id:
            restringidas = self._disponibilidad_por_docente.get(docente_id)
            if restringidas:
                self._franjas_por_docente[docente_id] = [
                    f for f in self._franjas_disponibles
                    if f.id in restringidas
                ]
            else:
                self._franjas_por_docente[docente_id] = self._franjas_disponibles

    # ==================================================================
    # ÍNDICES DE ESTADO (se actualizan durante el backtracking)
    # Se usan para detectar conflictos en O(1)
    # ==================================================================

    def _inicializar_indices_estado(self):
        """Índices mutables que reflejan el estado actual de las asignaciones."""
        # docente_id → set de franja_ids ya usadas
        self._docente_franjas_usadas: dict[int, set] = {}
        # aula_id → set de franja_ids ya usadas
        self._aula_franjas_usadas: dict[int, set] = {}
        # grupo_id → set de franja_ids ya usadas
        self._grupo_franjas_usadas: dict[int, set] = {}
        # grupo_id → set de dias ya usados
        self._grupo_dias_usados: dict[int, list] = {}

    def _registrar_asignacion(self, candidato: dict):
        """Actualiza los índices al agregar una asignación."""
        did = candidato["docente"].id
        aid = candidato["aula"].id
        fid = candidato["franja"].id
        gid = candidato["grupo"].id
        dia = candidato["franja"].dia_semana

        if did not in self._docente_franjas_usadas:
            self._docente_franjas_usadas[did] = set()
        self._docente_franjas_usadas[did].add(fid)

        if aid not in self._aula_franjas_usadas:
            self._aula_franjas_usadas[aid] = set()
        self._aula_franjas_usadas[aid].add(fid)

        if gid not in self._grupo_franjas_usadas:
            self._grupo_franjas_usadas[gid] = set()
        self._grupo_franjas_usadas[gid].add(fid)

        if gid not in self._grupo_dias_usados:
            self._grupo_dias_usados[gid] = []
        self._grupo_dias_usados[gid].append(dia)

    def _desregistrar_asignacion(self, candidato: dict):
        """Revierte los índices al hacer backtrack."""
        did = candidato["docente"].id
        aid = candidato["aula"].id
        fid = candidato["franja"].id
        gid = candidato["grupo"].id
        dia = candidato["franja"].dia_semana

        self._docente_franjas_usadas[did].discard(fid)
        self._aula_franjas_usadas[aid].discard(fid)
        self._grupo_franjas_usadas[gid].discard(fid)
        if dia in self._grupo_dias_usados.get(gid, []):
            self._grupo_dias_usados[gid].remove(dia)

    def _es_valido_rapido(self, candidato: dict) -> bool:
        """
        Validación O(1) usando índices.
        Detecta los conflictos más comunes antes de llamar al validador completo.
        """
        did = candidato["docente"].id
        aid = candidato["aula"].id
        fid = candidato["franja"].id
        gid = candidato["grupo"].id

        # Docente ya ocupa esa franja
        if fid in self._docente_franjas_usadas.get(did, set()):
            return False

        # Aula ya ocupada en esa franja
        if fid in self._aula_franjas_usadas.get(aid, set()):
            return False

        # Grupo ya tiene clase en esa franja
        if fid in self._grupo_franjas_usadas.get(gid, set()):
            return False

        return True

    # ==================================================================
    # PUNTO DE ENTRADA
    # ==================================================================

    def generar(self) -> dict:
        """Punto de entrada principal del motor."""
        self.asignaciones = []
        self.conflictos = []
        self._inicio = time.time()
        self._inicializar_indices_estado()

        sesiones = self._construir_sesiones()

        if not sesiones:
            return {
                "exito": False,
                "asignaciones": [],
                "conflictos": [{
                    "id_restriccion": "CONFIG",
                    "descripcion": "No hay sesiones reales para programar. Verifica grupos, cursos y sesiones.",
                    "entidad_tipo": "Sistema",
                    "entidad_id": 0,
                    "id_sesion": None
                }],
                "puntaje_total": 0.0,
                "reporte_blandas": {}
            }

        sesiones_ordenadas = self._ordenar_por_dificultad(sesiones)
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

    # ==================================================================
    # CONSTRUCCIÓN Y ORDENAMIENTO DE SESIONES
    # ==================================================================

    def _construir_sesiones(self) -> list:
        """
        Construye sesiones del motor a partir de registros reales SesionClase.
        """
        sesiones_motor = []
        sesiones_db = self.datos.get("sesiones", [])
        parametro = self.datos.get("parametro_semestre")
        max_sesiones = parametro.max_sesiones_semana if parametro else 4
        min_cierre = parametro.min_inscritos_cierre if parametro else 10

        for sesion_db in sesiones_db:
            grupo = self._grupos_por_id.get(sesion_db.id_grupo)
            if not grupo or grupo.estado == "Cerrado":
                continue

            curso = self._cursos_por_id.get(grupo.id_curso)
            if not curso:
                continue

            if grupo.inscritos is not None and grupo.inscritos > 0 and grupo.inscritos < min_cierre:
                self.conflictos.append({
                    "id_restriccion": "RH-15",
                    "descripcion": (
                        f"El grupo '{grupo.nombre_grupo}' tiene {grupo.inscritos} inscritos, "
                        f"menor al mínimo de {min_cierre}. Candidato a cierre."
                    ),
                    "entidad_tipo": "Grupo",
                    "entidad_id": grupo.id,
                    "id_sesion": sesion_db.id
                })
                continue

            if curso.sesiones_semana < 1:
                self.conflictos.append({
                    "id_restriccion": "RH-10",
                    "descripcion": f"El curso '{curso.nombre}' no tiene sesiones configuradas.",
                    "entidad_tipo": "Curso",
                    "entidad_id": curso.id,
                    "id_sesion": sesion_db.id
                })
                continue

            if curso.sesiones_semana > max_sesiones:
                self.conflictos.append({
                    "id_restriccion": "RH-11/RH-16",
                    "descripcion": (
                        f"El curso '{curso.nombre}' tiene {curso.sesiones_semana} sesiones, "
                        f"superando el máximo de {max_sesiones}."
                    ),
                    "entidad_tipo": "Curso",
                    "entidad_id": curso.id,
                    "id_sesion": sesion_db.id
                })
                continue

            sesiones_motor.append({
                "sesion": sesion_db,
                "grupo": grupo,
                "curso": curso,
                "num_sesion": sesion_db.numero_sesion,
                "sesion_key": f"sesion{sesion_db.id}"
            })

        return sesiones_motor

    def _ordenar_por_dificultad(self, sesiones: list) -> list:
        """
        Most Constrained Variable: primero las sesiones con menos candidatos.
        Usa los candidatos precalculados para no recalcular aquí.
        """
        def dificultad(sesion):
            curso = sesion["curso"]
            grupo = sesion["grupo"]
            inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo

            n_docentes = len(self._candidatos_docente_por_curso.get(curso.id, []))
            n_aulas = len(self._aulas_para_grupo(curso, inscritos))
            # Penaliza si hay poca disponibilidad
            return n_docentes * n_aulas

        return sorted(sesiones, key=dificultad)

    # ==================================================================
    # BACKTRACKING
    # ==================================================================

    def _backtrack(self, indice: int, sesiones: list) -> bool:
        """Algoritmo de búsqueda con retroceso y poda temprana."""

        # Red de seguridad: tiempo límite
        if time.time() - self._inicio > TIEMPO_LIMITE_SEGUNDOS:
            return True

        if indice == len(sesiones):
            return True

        sesion_actual = sesiones[indice]
        candidatos_validos = self._generar_candidatos_validos(sesion_actual)

        for penalizacion, candidato in candidatos_validos:
            candidato["penalizacion"] = penalizacion
            self.asignaciones.append(candidato)
            self._registrar_asignacion(candidato)

            if self._backtrack(indice + 1, sesiones):
                return True

            self.asignaciones.pop()
            self._desregistrar_asignacion(candidato)

        self._registrar_conflicto_sin_candidatos(sesion_actual)
        return False

    def _generar_candidatos_validos(self, sesion: dict) -> list:
        """
        Genera y filtra candidatos válidos ya ordenados por penalización.
        Usa poda temprana O(1) antes de llamar al validador completo.
        """
        grupo = sesion["grupo"]
        curso = sesion["curso"]
        sesion_db = sesion["sesion"]
        inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo

        docentes_candidatos = self._candidatos_docente_por_curso.get(curso.id, [])
        aulas_candidatas = self._aulas_para_grupo(curso, inscritos)

        if not docentes_candidatos or not aulas_candidatas or not self._franjas_disponibles:
            return []

        candidatos_evaluados = []

        for item_docente in docentes_candidatos:
            docente = item_docente["docente"]
            docente_flexible = item_docente["docente_flexible"]
            franjas_docente = self._franjas_por_docente.get(docente.id, self._franjas_disponibles)

            for franja in franjas_docente:
                for aula in aulas_candidatas:

                    candidato = {
                        "docente": docente,
                        "docente_flexible": docente_flexible,
                        "aula": aula,
                        "franja": franja,
                        "sesion": sesion_db,
                        "grupo": grupo,
                        "curso": curso,
                    }

                    # Poda O(1): descarta los conflictos más comunes
                    if not self._es_valido_rapido(candidato):
                        continue

                    # Validación completa con índices O(1)
                    resultado = validar_candidato(
                        candidato,
                        self.asignaciones,
                        self.datos,
                        indices=self._indices_estado()
                    )
                    if not resultado.valida:
                        continue

                    penalizacion = calcular_penalizacion(candidato, self.asignaciones)
                    candidatos_evaluados.append((penalizacion, candidato))

        # Ordena por menor penalización primero
        candidatos_evaluados.sort(key=lambda x: x[0])
        return candidatos_evaluados

    # ==================================================================
    # PRECÁLCULO DE CANDIDATOS
    # ==================================================================

    def _calcular_docentes_para_curso(self, curso) -> list:
        """
        Calcula docentes candidatos para un curso (se llama una sola vez en __init__).
        """
        elegibles_ids = self._elegibles_por_curso.get(curso.id, set())
        candidatos = []

        for docente in self._docentes_por_id.values():
            es_elegible = docente.id in elegibles_ids
            es_flexible = docente.id not in self._docentes_con_elegibilidad

            if es_elegible or es_flexible:
                candidatos.append({
                    "docente": docente,
                    "docente_flexible": es_flexible and not es_elegible
                })

        return candidatos

    def _indices_estado(self) -> dict:
        """Expone los índices de estado actuales para el validador."""
        return {
            "docente_franjas_usadas": self._docente_franjas_usadas,
            "aula_franjas_usadas": self._aula_franjas_usadas,
            "grupo_franjas_usadas": self._grupo_franjas_usadas,
            "grupo_dias_usados": self._grupo_dias_usados,
            "disponibilidad_por_docente": self._disponibilidad_por_docente,
            "elegibles_por_curso": self._elegibles_por_curso,
            "docentes_con_elegibilidad": self._docentes_con_elegibilidad,
        }

    def _aulas_para_grupo(self, curso, inscritos: int) -> list:
        """Filtra aulas compatibles con el curso y número de inscritos."""
        if curso.requiere_computadores:
            base = self._aulas_con_computadores
        elif curso.requiere_sillas_moviles:
            base = self._aulas_con_sillas
        else:
            base = self._aulas_activas

        return [a for a in base if a.capacidad >= inscritos]

    # ==================================================================
    # REGISTRO DE CONFLICTOS
    # ==================================================================

    def _registrar_conflicto_sin_candidatos(self, sesion: dict):
        """Registra conflicto trazable cuando no se puede asignar una sesión."""
        grupo = sesion["grupo"]
        curso = sesion["curso"]
        sesion_db = sesion["sesion"]

        diagnostico = self._diagnosticar_sin_candidatos(sesion)

        if diagnostico:
            self.conflictos.append({
                **diagnostico,
                "id_sesion": sesion_db.id
            })
            return

        self.conflictos.append({
            "id_restriccion": "NO_FACTIBLE",
            "descripcion": (
                f"No se pudo asignar el grupo '{grupo.nombre_grupo}' "
                f"(curso: '{curso.nombre}', sesión {sesion_db.numero_sesion}) "
                f"por combinación no factible de restricciones."
            ),
            "entidad_tipo": "Grupo",
            "entidad_id": grupo.id,
            "id_sesion": sesion_db.id
        })

    def _diagnosticar_sin_candidatos(self, sesion: dict) -> dict | None:
        """Diagnóstico rápido de por qué no hay candidatos."""
        grupo = sesion["grupo"]
        curso = sesion["curso"]
        inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo

        if not self._docentes_por_id:
            return {
                "id_restriccion": "RH-02",
                "descripcion": "No hay docentes activos registrados.",
                "entidad_tipo": "Docente",
                "entidad_id": 0
            }

        docentes = self._candidatos_docente_por_curso.get(curso.id, [])
        if not docentes:
            return {
                "id_restriccion": "RH-02",
                "descripcion": (
                    f"No hay docentes disponibles para el curso '{curso.nombre}'. "
                    f"Registre un docente elegible o deje uno sin asignar para que actúe como flexible."
                ),
                "entidad_tipo": "Curso",
                "entidad_id": curso.id
            }

        aulas = self._aulas_para_grupo(curso, inscritos)
        if not aulas:
            return {
                "id_restriccion": "RH-07/RH-09",
                "descripcion": (
                    f"No hay aulas compatibles para '{grupo.nombre_grupo}' "
                    f"(curso: '{curso.nombre}'). Verifique capacidad, computadores o sillas móviles."
                ),
                "entidad_tipo": "Aula",
                "entidad_id": 0
            }

        if not self._franjas_disponibles:
            return {
                "id_restriccion": "RH-05",
                "descripcion": "No hay franjas horarias disponibles.",
                "entidad_tipo": "Franja",
                "entidad_id": 0
            }

        # Verificar si algún docente tiene al menos una franja útil
        for item in docentes:
            docente = item["docente"]
            if self._franjas_por_docente.get(docente.id):
                return None  # Sí hay candidatos, el problema es de combinación

        return {
            "id_restriccion": "RH-01",
            "descripcion": (
                f"Los docentes candidatos para '{curso.nombre}' no tienen "
                f"disponibilidad en ninguna franja activa."
            ),
            "entidad_tipo": "Docente",
            "entidad_id": 0
        }