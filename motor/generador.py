"""
motor/generador.py
==================
Motor de Generación de Horarios — Algoritmo de Backtracking.

Esta versión usa sesiones reales persistidas en la base de datos:
SesionClase -> Asignacion -> Horario.

Lógica aplicada:
- Docentes con disponibilidad registrada: solo se usan en esas franjas.
- Docentes sin disponibilidad registrada: se consideran flexibles en horario.
- Docentes con elegibilidades registradas: solo dictan sus cursos autorizados.
- Docentes sin ninguna elegibilidad registrada: se consideran flexibles y pueden ser asignados.
- Si sobran docentes sin asignación, no se considera conflicto.
"""

from motor.validador import validar_candidato
from motor.restricciones import calcular_penalizacion, generar_reporte_blandas


class GeneradorHorarios:
    """
    Motor de backtracking para generación de horarios académicos.
    """

    def __init__(self, datos: dict):
        self.datos = datos
        self.asignaciones = []
        self.conflictos = []

    def generar(self) -> dict:
        """
        Punto de entrada principal del motor.
        """

        self.asignaciones = []
        self.conflictos = []

        sesiones = self._construir_sesiones()

        if not sesiones:
            return {
                "exito": False,
                "asignaciones": [],
                "conflictos": self.conflictos if self.conflictos else [
                    {
                        "id_restriccion": "CONFIG",
                        "descripcion": "No hay sesiones reales para programar. Verifica grupos, cursos y sesiones.",
                        "entidad_tipo": "Sistema",
                        "entidad_id": 0,
                        "id_sesion": None
                    }
                ],
                "puntaje_total": 0.0,
                "reporte_blandas": {}
            }

        sesiones_ordenadas = self._ordenar_por_dificultad(sesiones)

        exito = self._backtrack(0, sesiones_ordenadas)

        puntaje_total = sum(
            a.get("penalizacion", 0.0)
            for a in self.asignaciones
        )

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
        Construye sesiones del motor a partir de registros reales SesionClase.
        Aplica validaciones RH-10, RH-11, RH-15 y RH-16.
        """

        sesiones_motor = []

        sesiones_db = self.datos.get("sesiones", [])
        grupos_por_id = {g.id: g for g in self.datos.get("grupos", [])}
        cursos_por_id = {c.id: c for c in self.datos.get("cursos", [])}

        parametro = self.datos.get("parametro_semestre")
        max_sesiones = parametro.max_sesiones_semana if parametro else 4
        min_cierre = parametro.min_inscritos_cierre if parametro else 10

        for sesion_db in sesiones_db:
            grupo = grupos_por_id.get(sesion_db.id_grupo)

            if not grupo:
                continue

            if grupo.estado == "Cerrado":
                continue

            curso = cursos_por_id.get(grupo.id_curso)

            if not curso or not curso.estado:
                continue

            if grupo.inscritos is not None and grupo.inscritos > 0 and grupo.inscritos < min_cierre:
                self.conflictos.append({
                    "id_restriccion": "RH-15",
                    "descripcion": f"El grupo '{grupo.nombre_grupo}' tiene {grupo.inscritos} inscritos, menor al mínimo configurable de {min_cierre}. Debe marcarse como candidato a cierre.",
                    "entidad_tipo": "Grupo",
                    "entidad_id": grupo.id,
                    "id_sesion": sesion_db.id
                })
                continue

            if curso.sesiones_semana < 1:
                self.conflictos.append({
                    "id_restriccion": "RH-10",
                    "descripcion": f"El curso '{curso.nombre}' no tiene sesiones semanales configuradas.",
                    "entidad_tipo": "Curso",
                    "entidad_id": curso.id,
                    "id_sesion": sesion_db.id
                })
                continue

            if curso.sesiones_semana > max_sesiones:
                self.conflictos.append({
                    "id_restriccion": "RH-11/RH-16",
                    "descripcion": f"El curso '{curso.nombre}' tiene {curso.sesiones_semana} sesiones, superando el máximo configurable de {max_sesiones}.",
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
        Ordena sesiones por menor cantidad de candidatos posibles.
        """

        def dificultad(sesion):
            return len(self._generar_candidatos(sesion))

        return sorted(sesiones, key=dificultad)

    def _backtrack(self, indice: int, sesiones: list) -> bool:
        """
        Algoritmo de búsqueda con retroceso.
        """

        if indice == len(sesiones):
            return True

        sesion_actual = sesiones[indice]

        candidatos = self._generar_candidatos(sesion_actual)
        candidatos_evaluados = []

        for candidato in candidatos:
            resultado = validar_candidato(candidato, self.asignaciones, self.datos)

            if resultado.valida:
                penalizacion = calcular_penalizacion(candidato, self.asignaciones)
                candidatos_evaluados.append((penalizacion, candidato))

        candidatos_evaluados.sort(key=lambda x: x[0])

        for penalizacion, candidato in candidatos_evaluados:
            candidato["penalizacion"] = penalizacion
            self.asignaciones.append(candidato)

            if self._backtrack(indice + 1, sesiones):
                return True

            self.asignaciones.pop()

        self._registrar_conflicto_sin_candidatos(sesion_actual)
        return False

    def _elegibilidades_activas(self):
        return [
            e for e in self.datos.get("elegibilidades", [])
            if e.activo
        ]

    def _docentes_activos(self):
        return [
            d for d in self.datos.get("docentes", [])
            if d.estado
        ]

    def _docentes_candidatos_para_curso(self, curso):
        """
        Retorna docentes candidatos para un curso.

        Incluye:
        - Docentes explícitamente elegibles para el curso.
        - Docentes sin ninguna elegibilidad activa, tratados como flexibles.
        """

        elegibilidades = self._elegibilidades_activas()
        docentes_activos = self._docentes_activos()

        docentes_elegibles_curso_ids = set(
            e.id_docente
            for e in elegibilidades
            if e.id_curso == curso.id
        )

        docentes_con_alguna_materia_ids = set(
            e.id_docente
            for e in elegibilidades
        )

        candidatos = []

        for docente in docentes_activos:
            es_elegible_para_curso = docente.id in docentes_elegibles_curso_ids
            es_docente_flexible = docente.id not in docentes_con_alguna_materia_ids

            if es_elegible_para_curso or es_docente_flexible:
                candidatos.append({
                    "docente": docente,
                    "docente_flexible": es_docente_flexible and not es_elegible_para_curso
                })

        return candidatos

    def _disponibilidades_por_docente(self):
        """
        Agrupa disponibilidades por docente.

        Si un docente no aparece en este diccionario, se entiende que es flexible en horario.
        """

        disponibilidades = {}

        for disp in self.datos.get("disponibilidades", []):
            if disp.id_docente not in disponibilidades:
                disponibilidades[disp.id_docente] = set()

            disponibilidades[disp.id_docente].add(disp.id_franja)

        return disponibilidades

    def _generar_candidatos(self, sesion: dict) -> list:
        """
        Genera combinaciones posibles:
        docente + aula + franja.
        """

        grupo = sesion["grupo"]
        curso = sesion["curso"]
        sesion_db = sesion["sesion"]

        candidatos = []

        # --------------------------------------------------------------
        # 1. Docentes candidatos
        # --------------------------------------------------------------
        docentes_candidatos = self._docentes_candidatos_para_curso(curso)

        if not docentes_candidatos:
            return []

        # --------------------------------------------------------------
        # 2. Aulas candidatas
        # --------------------------------------------------------------
        inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo

        aulas_candidatas = [
            a for a in self.datos.get("aulas", [])
            if a.estado
            and a.capacidad >= inscritos
            and (not curso.requiere_computadores or a.tiene_computadores)
            and (not curso.requiere_sillas_moviles or a.tiene_sillas_moviles)
        ]

        if not aulas_candidatas:
            return []

        # --------------------------------------------------------------
        # 3. Franjas disponibles
        # --------------------------------------------------------------
        franjas_disponibles = [
            f for f in self.datos.get("franjas", [])
            if not f.bloqueada
        ]

        if not franjas_disponibles:
            return []

        # --------------------------------------------------------------
        # 4. Disponibilidad por docente
        # --------------------------------------------------------------
        disponibilidades_por_docente = self._disponibilidades_por_docente()

        # --------------------------------------------------------------
        # 5. Combinaciones docente + franja + aula
        # --------------------------------------------------------------
        for item_docente in docentes_candidatos:
            docente = item_docente["docente"]
            docente_flexible = item_docente["docente_flexible"]

            franjas_restringidas = disponibilidades_por_docente.get(docente.id)

            if franjas_restringidas:
                franjas_docente = [
                    franja for franja in franjas_disponibles
                    if franja.id in franjas_restringidas
                ]
            else:
                franjas_docente = franjas_disponibles

            for franja in franjas_docente:
                for aula in aulas_candidatas:
                    candidatos.append({
                        "docente": docente,
                        "docente_flexible": docente_flexible,
                        "aula": aula,
                        "franja": franja,
                        "sesion": sesion_db,
                        "grupo": grupo,
                        "curso": curso,
                    })

        return candidatos

    def _registrar_conflicto_sin_candidatos(self, sesion: dict):
        """
        Registra conflicto trazable para una sesión real.
        """

        grupo = sesion["grupo"]
        curso = sesion["curso"]
        sesion_db = sesion["sesion"]

        diagnostico = self._diagnosticar_sin_candidatos(sesion)

        if diagnostico:
            self.conflictos.append({
                "id_restriccion": diagnostico["id_restriccion"],
                "descripcion": diagnostico["descripcion"],
                "entidad_tipo": diagnostico["entidad_tipo"],
                "entidad_id": diagnostico["entidad_id"],
                "id_sesion": sesion_db.id
            })
            return

        candidatos_raw = self._generar_candidatos(sesion)

        if not candidatos_raw:
            self.conflictos.append({
                "id_restriccion": "RH-08",
                "descripcion": (
                    f"No hay candidatos para el grupo '{grupo.nombre_grupo}' "
                    f"(curso: '{curso.nombre}', sesión {sesion_db.numero_sesion}). "
                    f"Verifica docentes activos, elegibilidades, disponibilidad horaria, aulas compatibles y franjas disponibles."
                ),
                "entidad_tipo": "Grupo",
                "entidad_id": grupo.id,
                "id_sesion": sesion_db.id
            })
            return

        for candidato in candidatos_raw:
            resultado = validar_candidato(
                candidato,
                self.asignaciones,
                self.datos
            )

            if not resultado.valida:
                self.conflictos.append({
                    "id_restriccion": resultado.id_restriccion or "RA-01",
                    "descripcion": (
                        f"No se pudo asignar el grupo '{grupo.nombre_grupo}' "
                        f"(curso: '{curso.nombre}', sesión {sesion_db.numero_sesion}). "
                        f"Causa probable: {resultado.descripcion}"
                    ),
                    "entidad_tipo": resultado.entidad_tipo or "Grupo",
                    "entidad_id": resultado.entidad_id or grupo.id,
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

    def _diagnosticar_sin_candidatos(self, sesion: dict):
        """
        Diagnóstico específico cuando no se generan candidatos.
        """

        grupo = sesion["grupo"]
        curso = sesion["curso"]

        docentes_activos = self._docentes_activos()

        if not docentes_activos:
            return {
                "id_restriccion": "RH-02",
                "descripcion": "No hay docentes activos registrados para asignar horarios.",
                "entidad_tipo": "Docente",
                "entidad_id": 0
            }

        docentes_candidatos = self._docentes_candidatos_para_curso(curso)

        if not docentes_candidatos:
            return {
                "id_restriccion": "RH-02",
                "descripcion": (
                    f"No hay docentes disponibles para el curso '{curso.nombre}'. "
                    f"Registre al menos un docente elegible para este curso o deje un docente sin materia asignada para que actúe como flexible."
                ),
                "entidad_tipo": "Curso",
                "entidad_id": curso.id
            }

        inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo

        aulas_candidatas = [
            a for a in self.datos.get("aulas", [])
            if a.estado
            and a.capacidad >= inscritos
            and (not curso.requiere_computadores or a.tiene_computadores)
            and (not curso.requiere_sillas_moviles or a.tiene_sillas_moviles)
        ]

        if not aulas_candidatas:
            return {
                "id_restriccion": "RH-07/RH-09",
                "descripcion": (
                    f"No hay aulas compatibles para el grupo '{grupo.nombre_grupo}' "
                    f"del curso '{curso.nombre}'. Verifique capacidad, computadores o sillas móviles."
                ),
                "entidad_tipo": "Aula",
                "entidad_id": 0
            }

        franjas_disponibles = [
            f for f in self.datos.get("franjas", [])
            if not f.bloqueada
        ]

        if not franjas_disponibles:
            return {
                "id_restriccion": "RH-05",
                "descripcion": "No hay franjas horarias disponibles. Todas están bloqueadas o no existen.",
                "entidad_tipo": "Franja",
                "entidad_id": 0
            }

        disponibilidades_por_docente = self._disponibilidades_por_docente()

        algun_docente_tiene_franja_util = False

        for item_docente in docentes_candidatos:
            docente = item_docente["docente"]
            franjas_restringidas = disponibilidades_por_docente.get(docente.id)

            if not franjas_restringidas:
                algun_docente_tiene_franja_util = True
                break

            for franja in franjas_disponibles:
                if franja.id in franjas_restringidas:
                    algun_docente_tiene_franja_util = True
                    break

            if algun_docente_tiene_franja_util:
                break

        if not algun_docente_tiene_franja_util:
            return {
                "id_restriccion": "RH-01",
                "descripcion": (
                    f"Los docentes candidatos para el curso '{curso.nombre}' tienen restricciones horarias, "
                    f"pero ninguna coincide con las franjas disponibles."
                ),
                "entidad_tipo": "Docente",
                "entidad_id": 0
            }

        return None