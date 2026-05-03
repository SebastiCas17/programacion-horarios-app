// ==========================================================
// coordinador.js
// Panel del Coordinador: gestión académica y motor de horarios.
// Usa los endpoints existentes del backend.
// ==========================================================

let docentesCache = [];
let cursosCache = [];
let franjasCache = [];

// ==========================================================
// VALIDACIONES GENERALES DEL FRONTEND
// ==========================================================

const MAX_ESTUDIANTES = 40;
const MIN_INSCRITOS = 10;

const REGEX_TEXTO_GENERAL = /^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 .,_-]+$/;
const REGEX_NOMBRE_PERSONA = /^[A-Za-zÁÉÍÓÚáéíóúÑñ .'-]+$/;
const REGEX_CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const REGEX_HORA = /^(?:[01]\d|2[0-3]):[0-5]\d$/;

function mostrarErrorValidacion(mensaje) {
  alert(mensaje);
  return false;
}

function validarTextoGeneral(valor, campo, min = 2, max = 100) {
  if (!valor || valor.trim().length < min) {
    return mostrarErrorValidacion(`${campo} debe tener mínimo ${min} caracteres.`);
  }

  if (valor.trim().length > max) {
    return mostrarErrorValidacion(`${campo} no puede superar ${max} caracteres.`);
  }

  if (!REGEX_TEXTO_GENERAL.test(valor.trim())) {
    return mostrarErrorValidacion(`${campo} contiene caracteres no permitidos. No uses signos como @, #, $, %, *, /.`);
  }

  return true;
}

function validarNombrePersona(valor, campo) {
  if (!valor || valor.trim().length < 2) {
    return mostrarErrorValidacion(`${campo} debe tener mínimo 2 caracteres.`);
  }

  if (valor.trim().length > 100) {
    return mostrarErrorValidacion(`${campo} no puede superar 100 caracteres.`);
  }

  if (!REGEX_NOMBRE_PERSONA.test(valor.trim())) {
    return mostrarErrorValidacion(`${campo} contiene caracteres no permitidos. No uses signos como @, #, $, %, *, /.`);
  }

  return true;
}

function validarCorreo(valor) {
  if (!valor || !REGEX_CORREO.test(valor.trim())) {
    return mostrarErrorValidacion("El correo institucional no tiene un formato válido.");
  }

  return true;
}

function validarEntero(valor, campo, min, max) {
  if (valor === "" || valor === null || valor === undefined) {
    return mostrarErrorValidacion(`${campo} es obligatorio.`);
  }

  const numero = Number(valor);

  if (!Number.isInteger(numero)) {
    return mostrarErrorValidacion(`${campo} debe ser un número entero.`);
  }

  if (numero < min || numero > max) {
    return mostrarErrorValidacion(`${campo} debe estar entre ${min} y ${max}.`);
  }

  return true;
}

function horaAMinutos(hora) {
  const partes = hora.split(":");
  return Number(partes[0]) * 60 + Number(partes[1]);
}

function validarHora(valor, campo) {
  if (!valor || !REGEX_HORA.test(valor)) {
    return mostrarErrorValidacion(`${campo} debe estar en formato militar HH:MM.`);
  }

  return true;
}

function validarRangoHoras(inicio, fin, campoInicio, campoFin) {
  if (!validarHora(inicio, campoInicio)) return false;
  if (!validarHora(fin, campoFin)) return false;

  if (horaAMinutos(inicio) >= horaAMinutos(fin)) {
    return mostrarErrorValidacion(`${campoInicio} debe ser menor que ${campoFin}.`);
  }

  return true;
}

function manejarErrorFormulario(error) {
  console.error(error);
}

// ==========================================================
// CARGA GENERAL
// ==========================================================

async function cargarTodo() {
  await cargarParametroSemestre();

  await cargarDocentes();
  await cargarCursos();
  await cargarGrupos();
  await cargarAulas();
  await cargarFranjas();

  await cargarDisponibilidad();
  await cargarElegibilidad();
  await cargarHorarios();
}

// ==========================================================
// DATOS INICIALES / SEED ACADÉMICO
// ==========================================================

async function cargarDatosIniciales() {
  if (!confirm("¿Deseas cargar los datos académicos iniciales? No se duplicarán datos existentes.")) {
    return;
  }

  const resultado = await api("/api/seed/datos-academicos", {
    method: "POST"
  });

  const contenedor = document.getElementById("seed-resultado");

  if (contenedor) {
    contenedor.innerHTML = `
      <strong>${resultado.mensaje}</strong><br>
      Docentes creados: ${resultado.creados_en_esta_ejecucion.docentes}<br>
      Cursos creados: ${resultado.creados_en_esta_ejecucion.cursos}<br>
      Grupos creados: ${resultado.creados_en_esta_ejecucion.grupos}<br>
      Aulas creadas: ${resultado.creados_en_esta_ejecucion.aulas}<br>
      Franjas creadas: ${resultado.creados_en_esta_ejecucion.franjas}<br>
      Elegibilidades creadas: ${resultado.creados_en_esta_ejecucion.elegibilidades}<br>
      Disponibilidades creadas: ${resultado.creados_en_esta_ejecucion.disponibilidades}<br>
      Sesiones preparadas: ${resultado.total_sesiones_preparadas}
    `;
  }

  await cargarTodo();

  alert("Datos iniciales cargados correctamente");
}

// ==========================================================
// DOCENTES
// ==========================================================

async function cargarDocentes() {
  const docentes = await api("/api/docentes");

  docentesCache = docentes;

  const tabla = document.getElementById("tabla-docentes");

  if (tabla) {
    tabla.innerHTML = docentes.map(d => `
      <tr>
        <td>${d.id}</td>
        <td>${d.nombre}</td>
        <td>${d.correo}</td>
        <td>${d.tipo_vinculacion}</td>
        <td><button onclick="eliminarDocente(${d.id})">Eliminar</button></td>
      </tr>
    `).join("");
  }

  const opciones = docentes.map(d =>
    option(d.id, `${d.nombre} - ${d.tipo_vinculacion}`)
  ).join("");

  const selectDisponibilidad = document.getElementById("disp-docente");
  const selectElegibilidad = document.getElementById("eleg-docente");

  if (selectDisponibilidad) {
    selectDisponibilidad.innerHTML = opciones || `<option value="">No hay docentes registrados</option>`;
  }

  if (selectElegibilidad) {
    selectElegibilidad.innerHTML = opciones || `<option value="">No hay docentes registrados</option>`;
  }
}

async function crearDocente() {
  try {
    const docente = {
      nombre: document.getElementById("docente-nombre").value.trim(),
      correo: document.getElementById("docente-correo").value.trim(),
      tipo_vinculacion: document.getElementById("docente-tipo").value,
      estado: true
    };

    if (!validarNombrePersona(docente.nombre, "Nombre del docente")) return;
    if (!validarCorreo(docente.correo)) return;

    await api("/api/docentes", {
      method: "POST",
      body: JSON.stringify(docente)
    });

    document.getElementById("docente-nombre").value = "";
    document.getElementById("docente-correo").value = "";
    document.getElementById("docente-tipo").value = "TC";

    await cargarDocentes();
    await cargarDisponibilidad();

    alert("Docente guardado correctamente");
  } catch (error) {
    manejarErrorFormulario(error);
  }
}

async function eliminarDocente(id) {
  if (!confirm("¿Eliminar este docente?")) return;

  await api(`/api/docentes/${id}`, {
    method: "DELETE"
  });

  await cargarDocentes();
  await cargarDisponibilidad();
  await cargarElegibilidad();

  alert("Docente eliminado correctamente");
}

// ==========================================================
// CURSOS
// ==========================================================

async function cargarCursos() {
  const cursos = await api("/api/cursos");

  cursosCache = cursos;

  const tabla = document.getElementById("tabla-cursos");

  if (tabla) {
    tabla.innerHTML = cursos.map(c => `
      <tr>
        <td>${c.id}</td>
        <td>${c.nombre}</td>
        <td>${c.codigo}</td>
        <td>${c.sesiones_semana}</td>
        <td><button onclick="eliminarCurso(${c.id})">Eliminar</button></td>
      </tr>
    `).join("");
  }

  const opciones = cursos.map(c =>
    option(c.id, `${c.id} - ${c.nombre}`)
  ).join("");

  const selectGrupoCurso = document.getElementById("grupo-curso");
  const selectElegCurso = document.getElementById("eleg-curso");

  if (selectGrupoCurso) {
    selectGrupoCurso.innerHTML = opciones || `<option value="">No hay cursos registrados</option>`;
  }

  if (selectElegCurso) {
    selectElegCurso.innerHTML = opciones || `<option value="">No hay cursos registrados</option>`;
  }
}

async function crearCurso() {
  try {
    const curso = {
      nombre: document.getElementById("curso-nombre").value.trim(),
      codigo: document.getElementById("curso-codigo").value.trim(),
      creditos: Number(document.getElementById("curso-creditos").value),
      sesiones_semana: Number(document.getElementById("curso-sesiones").value),
      duracion_sesion_h: 2,
      requiere_computadores: document.getElementById("curso-computadores").checked,
      requiere_sillas_moviles: document.getElementById("curso-sillas").checked,
      estado: true
    };

    if (!validarTextoGeneral(curso.nombre, "Nombre del curso", 2, 120)) return;
    if (!validarTextoGeneral(curso.codigo, "Código del curso", 2, 30)) return;
    if (!validarEntero(document.getElementById("curso-creditos").value, "Créditos", 1, 6)) return;
    if (!validarEntero(document.getElementById("curso-sesiones").value, "Sesiones por semana", 1, 4)) return;

    await api("/api/cursos", {
      method: "POST",
      body: JSON.stringify(curso)
    });

    document.getElementById("curso-nombre").value = "";
    document.getElementById("curso-codigo").value = "";
    document.getElementById("curso-creditos").value = 3;
    document.getElementById("curso-sesiones").value = 2;
    document.getElementById("curso-computadores").checked = false;
    document.getElementById("curso-sillas").checked = false;

    await cargarCursos();

    alert("Curso guardado correctamente");
  } catch (error) {
    manejarErrorFormulario(error);
  }
}

async function eliminarCurso(id) {
  if (!confirm("¿Eliminar este curso?")) return;

  await api(`/api/cursos/${id}`, {
    method: "DELETE"
  });

  await cargarCursos();
  await cargarGrupos();
  await cargarElegibilidad();

  alert("Curso eliminado correctamente");
}

// ==========================================================
// GRUPOS
// ==========================================================

async function cargarGrupos() {
  const grupos = await api("/api/grupos");

  const tabla = document.getElementById("tabla-grupos");

  if (!tabla) return;

  tabla.innerHTML = grupos.map(g => `
    <tr>
      <td>${g.id}</td>
      <td>${g.id_curso}</td>
      <td>${g.nombre_grupo}</td>
      <td>${g.cupo_objetivo}</td>
      <td>${g.inscritos}</td>
      <td><button onclick="eliminarGrupo(${g.id})">Eliminar</button></td>
    </tr>
  `).join("");
}

async function crearGrupo() {
  try {
    const idCurso = Number(document.getElementById("grupo-curso").value);
    const nombreGrupo = document.getElementById("grupo-nombre").value.trim();
    const cupo = Number(document.getElementById("grupo-cupo").value);
    const inscritos = Number(document.getElementById("grupo-inscritos").value);

    const grupo = {
      id_curso: idCurso,
      nombre_grupo: nombreGrupo,
      cupo_objetivo: cupo,
      inscritos: inscritos,
      estado: "Activo"
    };

    if (!grupo.id_curso) {
      alert("Debe seleccionar un curso.");
      return;
    }

    if (!validarTextoGeneral(grupo.nombre_grupo, "Nombre del grupo", 2, 50)) return;
    if (!validarEntero(document.getElementById("grupo-cupo").value, "Cupo objetivo", 1, MAX_ESTUDIANTES)) return;
    if (!validarEntero(document.getElementById("grupo-inscritos").value, "Número de inscritos", MIN_INSCRITOS, MAX_ESTUDIANTES)) return;

    if (inscritos > cupo) {
      alert("El número de inscritos no puede superar el cupo objetivo del grupo.");
      return;
    }

    await api("/api/grupos", {
      method: "POST",
      body: JSON.stringify(grupo)
    });

    document.getElementById("grupo-nombre").value = "";
    document.getElementById("grupo-cupo").value = 40;
    document.getElementById("grupo-inscritos").value = 10;

    await cargarGrupos();

    alert("Grupo guardado correctamente");
  } catch (error) {
    manejarErrorFormulario(error);
  }
}

async function eliminarGrupo(id) {
  if (!confirm("¿Eliminar este grupo?")) return;

  await api(`/api/grupos/${id}`, {
    method: "DELETE"
  });

  await cargarGrupos();

  alert("Grupo eliminado correctamente");
}

// ==========================================================
// AULAS
// ==========================================================

async function cargarAulas() {
  const aulas = await api("/api/aulas");

  const tabla = document.getElementById("tabla-aulas");

  if (!tabla) return;

  tabla.innerHTML = aulas.map(a => `
    <tr>
      <td>${a.id}</td>
      <td>${a.codigo}</td>
      <td>${a.capacidad}</td>
      <td>${a.tiene_computadores ? "Sí" : "No"}</td>
      <td>${a.tiene_sillas_moviles ? "Sí" : "No"}</td>
      <td><button onclick="eliminarAula(${a.id})">Eliminar</button></td>
    </tr>
  `).join("");
}

async function crearAula() {
  try {
    const aula = {
      codigo: document.getElementById("aula-codigo").value.trim(),
      capacidad: Number(document.getElementById("aula-capacidad").value),
      tiene_computadores: document.getElementById("aula-computadores").checked,
      tiene_sillas_moviles: document.getElementById("aula-sillas").checked,
      edificio: document.getElementById("aula-edificio").value.trim(),
      estado: true
    };

    if (!validarTextoGeneral(aula.codigo, "Código del aula", 1, 30)) return;
    if (!validarEntero(document.getElementById("aula-capacidad").value, "Capacidad del aula", 1, MAX_ESTUDIANTES)) return;

    if (aula.edificio && !validarTextoGeneral(aula.edificio, "Edificio", 1, 60)) return;

    await api("/api/aulas", {
      method: "POST",
      body: JSON.stringify(aula)
    });

    document.getElementById("aula-codigo").value = "";
    document.getElementById("aula-capacidad").value = 40;
    document.getElementById("aula-edificio").value = "";
    document.getElementById("aula-computadores").checked = false;
    document.getElementById("aula-sillas").checked = false;

    await cargarAulas();

    alert("Aula guardada correctamente");
  } catch (error) {
    manejarErrorFormulario(error);
  }
}

async function eliminarAula(id) {
  if (!confirm("¿Eliminar esta aula?")) return;

  await api(`/api/aulas/${id}`, {
    method: "DELETE"
  });

  await cargarAulas();

  alert("Aula eliminada correctamente");
}

// ==========================================================
// PARÁMETROS DE SEMESTRE
// ==========================================================

async function cargarParametroSemestre() {
  const parametro = await api("/api/parametros-semestre/activo");

  const estado = document.getElementById("parametro-estado");

  document.getElementById("param-nombre").value = parametro.nombre;
  document.getElementById("param-hora-inicio-lv").value = parametro.hora_inicio_lv;
  document.getElementById("param-hora-fin-lv").value = parametro.hora_fin_lv;
  document.getElementById("param-hora-inicio-sab").value = parametro.hora_inicio_sab;
  document.getElementById("param-hora-fin-sab").value = parametro.hora_fin_sab;
  document.getElementById("param-inicio-almuerzo").value = parametro.inicio_almuerzo;
  document.getElementById("param-fin-almuerzo").value = parametro.fin_almuerzo;
  document.getElementById("param-max-sesiones").value = parametro.max_sesiones_semana;
  document.getElementById("param-min-cierre").value = parametro.min_inscritos_cierre;
  document.getElementById("param-activo").checked = parametro.activo;

  if (estado) {
    estado.innerHTML = `
      <strong>Semestre activo:</strong> ${parametro.nombre}<br>
      <strong>Lun-Vie:</strong> ${parametro.hora_inicio_lv} - ${parametro.hora_fin_lv}<br>
      <strong>Sábado:</strong> ${parametro.hora_inicio_sab} - ${parametro.hora_fin_sab}<br>
      <strong>Almuerzo:</strong> ${parametro.inicio_almuerzo} - ${parametro.fin_almuerzo}<br>
      <strong>Máx. sesiones:</strong> ${parametro.max_sesiones_semana}<br>
      <strong>Mín. cierre grupo:</strong> ${parametro.min_inscritos_cierre}
    `;
  }
}

async function guardarParametroSemestre() {
  try {
    const parametro = {
      nombre: document.getElementById("param-nombre").value.trim(),
      hora_inicio_lv: document.getElementById("param-hora-inicio-lv").value.trim(),
      hora_fin_lv: document.getElementById("param-hora-fin-lv").value.trim(),
      hora_inicio_sab: document.getElementById("param-hora-inicio-sab").value.trim(),
      hora_fin_sab: document.getElementById("param-hora-fin-sab").value.trim(),
      inicio_almuerzo: document.getElementById("param-inicio-almuerzo").value.trim(),
      fin_almuerzo: document.getElementById("param-fin-almuerzo").value.trim(),
      max_sesiones_semana: Number(document.getElementById("param-max-sesiones").value),
      min_inscritos_cierre: Number(document.getElementById("param-min-cierre").value),
      activo: document.getElementById("param-activo").checked
    };

    if (!validarTextoGeneral(parametro.nombre, "Nombre del semestre", 3, 30)) return;

    if (!validarRangoHoras(parametro.hora_inicio_lv, parametro.hora_fin_lv, "Hora inicio lunes a viernes", "Hora fin lunes a viernes")) return;
    if (!validarRangoHoras(parametro.hora_inicio_sab, parametro.hora_fin_sab, "Hora inicio sábado", "Hora fin sábado")) return;
    if (!validarRangoHoras(parametro.inicio_almuerzo, parametro.fin_almuerzo, "Inicio del almuerzo", "Fin del almuerzo")) return;

    if (!validarEntero(document.getElementById("param-max-sesiones").value, "Máximo de sesiones por semana", 1, 4)) return;
    if (!validarEntero(document.getElementById("param-min-cierre").value, "Mínimo de inscritos para cierre", 10, 40)) return;

    await api("/api/parametros-semestre", {
      method: "POST",
      body: JSON.stringify(parametro)
    });

    await cargarParametroSemestre();

    alert("Parámetros del semestre guardados correctamente");
  } catch (error) {
    manejarErrorFormulario(error);
  }
}

// ==========================================================
// FRANJAS HORARIAS
// ==========================================================

async function cargarFranjas() {
  const franjas = await api("/api/franjas");

  franjasCache = franjas;

  const tabla = document.getElementById("tabla-franjas");

  if (tabla) {
    tabla.innerHTML = franjas.map(f => `
      <tr>
        <td>${f.id}</td>
        <td>${f.dia_semana}</td>
        <td>${f.hora_inicio}</td>
        <td>${f.hora_fin}</td>
        <td>${f.bloqueada ? "Sí" : "No"}</td>
        <td><button onclick="eliminarFranja(${f.id})">Eliminar</button></td>
      </tr>
    `).join("");
  }

  const opciones = franjas.map(f =>
    option(
      f.id,
      `${f.dia_semana} ${f.hora_inicio} - ${f.hora_fin}${f.bloqueada ? " (Bloqueada)" : ""}`
    )
  ).join("");

  const selectFranja = document.getElementById("disp-franja");

  if (selectFranja) {
    selectFranja.innerHTML = opciones || `<option value="">No hay franjas registradas</option>`;
  }
}

async function crearFranja() {
  try {
    const franja = {
      dia_semana: document.getElementById("franja-dia").value,
      hora_inicio: document.getElementById("franja-inicio").value.trim(),
      hora_fin: document.getElementById("franja-fin").value.trim(),
      bloqueada: document.getElementById("franja-bloqueada").checked
    };

    if (!validarRangoHoras(franja.hora_inicio, franja.hora_fin, "Hora de inicio", "Hora de fin")) return;

    await api("/api/franjas", {
      method: "POST",
      body: JSON.stringify(franja)
    });

    document.getElementById("franja-inicio").value = "";
    document.getElementById("franja-fin").value = "";
    document.getElementById("franja-bloqueada").checked = false;

    await cargarFranjas();
    await cargarDisponibilidad();

    alert("Franja guardada correctamente");
  } catch (error) {
    manejarErrorFormulario(error);
  }
}

async function eliminarFranja(id) {
  if (!confirm("¿Eliminar esta franja?")) return;

  await api(`/api/franjas/${id}`, {
    method: "DELETE"
  });

  await cargarFranjas();
  await cargarDisponibilidad();

  alert("Franja eliminada correctamente");
}

// ==========================================================
// DISPONIBILIDAD DOCENTE
// ==========================================================

async function cargarDisponibilidad() {
  const disponibilidad = await api("/api/disponibilidad");

  const docentesPorId = {};
  const franjasPorId = {};

  docentesCache.forEach(docente => {
    docentesPorId[docente.id] = docente;
  });

  franjasCache.forEach(franja => {
    franjasPorId[franja.id] = franja;
  });

  const tabla = document.getElementById("tabla-disponibilidad");

  if (!tabla) return;

  tabla.innerHTML = disponibilidad.map(d => {
    const docente = docentesPorId[d.id_docente];
    const franja = franjasPorId[d.id_franja];

    const nombreDocente = docente
      ? `${docente.nombre} (${docente.tipo_vinculacion})`
      : `Docente ID ${d.id_docente}`;

    const textoFranja = franja
      ? `${franja.dia_semana} ${franja.hora_inicio} - ${franja.hora_fin}`
      : `Franja ID ${d.id_franja}`;

    return `
      <tr>
        <td>${d.id}</td>
        <td>${nombreDocente}</td>
        <td>${textoFranja}</td>
        <td><button onclick="eliminarDisponibilidad(${d.id})">Eliminar</button></td>
      </tr>
    `;
  }).join("");
}

async function crearDisponibilidad() {
  const disponibilidad = {
    id_docente: Number(document.getElementById("disp-docente").value),
    id_franja: Number(document.getElementById("disp-franja").value)
  };

  if (!disponibilidad.id_docente || !disponibilidad.id_franja) {
    alert("Debe seleccionar docente y franja.");
    return;
  }

  await api("/api/disponibilidad", {
    method: "POST",
    body: JSON.stringify(disponibilidad)
  });

  await cargarDisponibilidad();

  alert("Disponibilidad docente guardada correctamente");
}

async function eliminarDisponibilidad(id) {
  if (!confirm("¿Eliminar esta disponibilidad?")) return;

  await api(`/api/disponibilidad/${id}`, {
    method: "DELETE"
  });

  await cargarDisponibilidad();

  alert("Disponibilidad eliminada correctamente");
}

// ==========================================================
// ELEGIBILIDAD DOCENTE-CURSO
// ==========================================================

async function cargarElegibilidad() {
  const elegibilidad = await api("/api/elegibilidad");

  const docentesPorId = {};
  const cursosPorId = {};

  docentesCache.forEach(docente => {
    docentesPorId[docente.id] = docente;
  });

  cursosCache.forEach(curso => {
    cursosPorId[curso.id] = curso;
  });

  const tabla = document.getElementById("tabla-elegibilidad");

  if (!tabla) return;

  tabla.innerHTML = elegibilidad.map(e => {
    const docente = docentesPorId[e.id_docente];
    const curso = cursosPorId[e.id_curso];

    const textoDocente = docente
      ? `${docente.id} - ${docente.nombre} (${docente.tipo_vinculacion})`
      : `Docente ID ${e.id_docente}`;

    const textoCurso = curso
      ? `${curso.id} - ${curso.nombre} (${curso.codigo})`
      : `Curso ID ${e.id_curso}`;

    return `
      <tr>
        <td>${e.id}</td>
        <td>${textoDocente}</td>
        <td>${textoCurso}</td>
        <td><button onclick="eliminarElegibilidad(${e.id})">Eliminar</button></td>
      </tr>
    `;
  }).join("");
}

async function crearElegibilidad() {
  const elegibilidad = {
    id_docente: Number(document.getElementById("eleg-docente").value),
    id_curso: Number(document.getElementById("eleg-curso").value),
    activo: true
  };

  if (!elegibilidad.id_docente || !elegibilidad.id_curso) {
    alert("Debe seleccionar docente y curso.");
    return;
  }

  await api("/api/elegibilidad", {
    method: "POST",
    body: JSON.stringify(elegibilidad)
  });

  await cargarElegibilidad();

  alert("Elegibilidad guardada correctamente");
}

async function eliminarElegibilidad(id) {
  if (!confirm("¿Eliminar esta elegibilidad?")) return;

  await api(`/api/elegibilidad/${id}`, {
    method: "DELETE"
  });

  await cargarElegibilidad();

  alert("Elegibilidad eliminada correctamente");
}

// ==========================================================
// MOTOR DE HORARIOS
// ==========================================================

async function generarHorario() {
  const resultado = await api("/api/generar-horario", {
    method: "POST"
  });

  const resumen = document.getElementById("resultado-resumen");
  const tablaResultados = document.getElementById("tabla-resultados");
  const listaConflictos = document.getElementById("lista-conflictos");

  if (resumen) {
    resumen.innerHTML = `
      <p><strong>Horario ID:</strong> ${resultado.horario_id}</p>
      <p><strong>Estado:</strong> ${resultado.estado}</p>
      <p><strong>Puntaje total:</strong> ${resultado.puntaje_total}</p>
      <p><strong>Total asignadas:</strong> ${resultado.total_asignadas}</p>
      <p><strong>Total conflictos:</strong> ${resultado.total_conflictos}</p>
    `;
  }

  if (tablaResultados) {
    tablaResultados.innerHTML =
      (resultado.asignaciones || []).map(a => `
        <tr>
          <td>${a.curso_nombre || ""}</td>
          <td>${a.grupo_nombre || ""}</td>
          <td>${a.docente_nombre || ""}</td>
          <td>${a.aula_codigo || ""}</td>
          <td>${a.franja_dia || ""}</td>
          <td>${a.franja_inicio || ""} - ${a.franja_fin || ""}</td>
          <td>${a.penalizacion ?? 0}</td>
        </tr>
      `).join("");
  }

  if (listaConflictos) {
    listaConflictos.innerHTML =
      (resultado.conflictos || []).map(c => `
        <li>
          <strong>${c.id_restriccion}</strong>: ${c.descripcion}
        </li>
      `).join("");
  }

  await cargarHorarios();
}

// ==========================================================
// HISTORIAL, PUBLICACIÓN Y EXPORTACIÓN DE HORARIOS
// ==========================================================

async function cargarHorarios() {
  const horarios = await api("/api/horarios");

  const tabla = document.getElementById("tabla-horarios");

  if (!tabla) return;

  const usuario = obtenerUsuario();
  const esAdministrador = usuario && usuario.rol === "Administrador";

  tabla.innerHTML = horarios.map(h => {
    const fecha = h.fecha_generacion
      ? new Date(h.fecha_generacion).toLocaleString()
      : "";

    const puedePublicar = h.estado === "Valido" && !h.es_oficial;
    const puedeEliminar = esAdministrador && !h.es_oficial;

    return `
      <tr>
        <td>${h.id}</td>
        <td>${fecha}</td>
        <td>${h.estado}</td>
        <td>${h.es_oficial ? "Sí" : "No"}</td>
        <td>${h.num_asignaciones}</td>
        <td>${h.num_conflictos}</td>
        <td>${h.puntaje_total ?? 0}</td>
        <td>
          ${puedePublicar ? `<button onclick="publicarHorario(${h.id})">Publicar</button>` : ""}
          <button onclick="exportarHorarioCSV(${h.id})">Exportar CSV</button>
          ${puedeEliminar ? `<button onclick="eliminarHorario(${h.id})">Eliminar</button>` : ""}
        </td>
      </tr>
    `;
  }).join("");
}

async function publicarHorario(id) {
  if (!confirm("¿Deseas marcar este horario como oficial? Esta acción lo dejará como versión oficial.")) {
    return;
  }

  await api(`/api/horarios/${id}/publicar`, {
    method: "POST"
  });

  alert("Horario publicado como oficial");
  await cargarHorarios();
}

async function eliminarHorario(id) {
  if (!confirm("¿Eliminar este horario? Solo se permite si no es oficial.")) {
    return;
  }

  await api(`/api/horarios/${id}`, {
    method: "DELETE"
  });

  alert("Horario eliminado correctamente");
  await cargarHorarios();
}

async function exportarHorarioCSV(id) {
  try {
    const token = obtenerToken();

    const headers = {};

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`/api/horarios/${id}/exportar-csv`, {
      method: "GET",
      headers
    });

    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.detail || "No se pudo exportar el horario");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `horario_${id}.csv`;
    document.body.appendChild(a);
    a.click();

    a.remove();
    window.URL.revokeObjectURL(url);

  } catch (error) {
    console.error(error);
    alert(error.message);
  }
}

// ==========================================================
// INICIO DE LA PÁGINA
// ==========================================================

document.addEventListener("DOMContentLoaded", async () => {
  if (!protegerPagina(["Administrador", "Coordinador"])) return;

  mostrarUsuarioActual();

  await cargarTodo();
});