"""
motor/generador.py
==================
Motor de Generación de Horarios — Algoritmo de Backtracking.

Esta versión usa sesiones reales persistidas en la base de datos:
SesionClase -> Asignacion -> Horario.
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

    def _generar_candidatos(self, sesion: dict) -> list:
        """
        Genera combinaciones posibles: docente + aula + franja.
        """
        grupo = sesion["grupo"]
        curso = sesion["curso"]
        sesion_db = sesion["sesion"]

        candidatos = []

        docentes_elegibles_ids = set(
            e.id_docente for e in self.datos.get("elegibilidades", [])
            if e.id_curso == curso.id and e.activo
        )

        if not docentes_elegibles_ids:
            docentes_candidatos = [
                d for d in self.datos.get("docentes", [])
                if d.estado
            ]
        else:
            docentes_candidatos = [
                d for d in self.datos.get("docentes", [])
                if d.id in docentes_elegibles_ids and d.estado
            ]

        inscritos = grupo.inscritos if grupo.inscritos and grupo.inscritos > 0 else grupo.cupo_objetivo

        aulas_candidatas = [
            a for a in self.datos.get("aulas", [])
            if a.capacidad >= inscritos
            and a.estado
            and (not curso.requiere_computadores or a.tiene_computadores)
            and (not curso.requiere_sillas_moviles or a.tiene_sillas_moviles)
        ]

        franjas_disponibles = [
            f for f in self.datos.get("franjas", [])
            if not f.bloqueada
        ]

        for docente in docentes_candidatos:
            for franja in franjas_disponibles:
                for aula in aulas_candidatas:
                    candidatos.append({
                        "docente": docente,
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

        candidatos_raw = self._generar_candidatos(sesion)

        if not candidatos_raw:
            descripcion = (
                f"No hay candidatos para el grupo '{grupo.nombre_grupo}' "
                f"(curso: '{curso.nombre}', sesión {sesion_db.numero_sesion}). "
                f"Verifica docentes elegibles, aulas compatibles y franjas disponibles."
            )
            id_restriccion = "RH-08"
        else:
            primer_resultado = validar_candidato(
                candidatos_raw[0],
                self.asignaciones,
                self.datos
            )

            id_restriccion = primer_resultado.id_restriccion or "RA-01"
            descripcion = (
                f"No se pudo asignar el grupo '{grupo.nombre_grupo}' "
                f"(curso: '{curso.nombre}', sesión {sesion_db.numero_sesion}). "
                f"Causa probable: {primer_resultado.descripcion}"
            )

        self.conflictos.append({
            "id_restriccion": id_restriccion,
            "descripcion": descripcion,
            "entidad_tipo": "Grupo",
            "entidad_id": grupo.id,
            "id_sesion": sesion_db.id
        })