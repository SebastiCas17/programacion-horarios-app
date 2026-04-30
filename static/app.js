// ==========================================================
// app.js
// Frontend para Programación de Horarios de Clase
// Incluye JWT, roles, seed académico, motor, historial,
// publicación oficial y exportación CSV.
// ==========================================================


// ==========================================================
// SESIÓN / JWT
// ==========================================================

function obtenerToken() {
  return localStorage.getItem("token");
}

function obtenerUsuario() {
  const usuario = localStorage.getItem("usuario");

  if (!usuario) return null;

  try {
    return JSON.parse(usuario);
  } catch (error) {
    console.error("Error leyendo usuario del localStorage:", error);
    return null;
  }
}

function guardarSesion(data) {
  const tokenLimpio = data.access_token.replace("Bearer ", "").trim();

  localStorage.setItem("token", tokenLimpio);
  localStorage.setItem("usuario", JSON.stringify(data.usuario));
}

function cerrarSesion() {
  localStorage.removeItem("token");
  localStorage.removeItem("usuario");
}

function actualizarEstadoLogin() {
  const estado = document.getElementById("login-estado");
  if (!estado) return;

  const usuario = obtenerUsuario();

  if (!usuario) {
    estado.innerHTML = "No has iniciado sesión.";
    return;
  }

  estado.innerHTML = `
    <strong>Sesión activa</strong><br>
    Usuario: ${usuario.nombre}<br>
    Correo: ${usuario.correo}<br>
    Rol: ${usuario.rol}
  `;
}

async function loginUsuario() {
  const correo = document.getElementById("login-correo").value.trim();
  const password = document.getElementById("login-password").value.trim();

  if (!correo || !password) {
    alert("Debe ingresar correo y contraseña.");
    return;
  }

  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ correo, password })
  });

  guardarSesion(data);
  actualizarEstadoLogin();

  alert("Inicio de sesión exitoso");
}

function logoutUsuario() {
  cerrarSesion();
  actualizarEstadoLogin();
  alert("Sesión cerrada");
}


// ==========================================================
// FUNCIÓN GENERAL PARA CONSUMIR API
// ==========================================================

async function api(url, options = {}) {
  try {
    const token = obtenerToken();

    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const detalle = data?.detail || "Error en la petición";

      if (response.status === 401) {
        cerrarSesion();
        actualizarEstadoLogin();
      }

      throw new Error(detalle);
    }

    return data;
  } catch (error) {
    console.error(error);
    alert(error.message);
    throw error;
  }
}

function option(value, text) {
  return `<option value="${value}">${text}</option>`;
}


// ==========================================================
// CARGA INICIAL
// ==========================================================

async function cargarTodo() {
  await Promise.all([
    cargarParametroSemestre(),
    cargarDocentes(),
    cargarCursos(),
    cargarGrupos(),
    cargarAulas(),
    cargarFranjas(),
    cargarDisponibilidad(),
    cargarElegibilidad(),
    cargarHorarios()
  ]);
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

  document.getElementById("tabla-docentes").innerHTML = docentes.map(d => `
    <tr>
      <td>${d.id}</td>
      <td>${d.nombre}</td>
      <td>${d.correo}</td>
      <td>${d.tipo_vinculacion}</td>
      <td><button onclick="eliminarDocente(${d.id})">Eliminar</button></td>
    </tr>
  `).join("");

  const opciones = docentes.map(d => option(d.id, `${d.id} - ${d.nombre}`)).join("");

  document.getElementById("disp-docente").innerHTML = opciones;
  document.getElementById("eleg-docente").innerHTML = opciones;
}

async function crearDocente() {
  const docente = {
    nombre: document.getElementById("docente-nombre").value.trim(),
    correo: document.getElementById("docente-correo").value.trim(),
    tipo_vinculacion: document.getElementById("docente-tipo").value,
    estado: true
  };

  if (!docente.nombre || !docente.correo) {
    alert("Debe ingresar nombre y correo del docente.");
    return;
  }

  await api("/api/docentes", {
    method: "POST",
    body: JSON.stringify(docente)
  });

  document.getElementById("docente-nombre").value = "";
  document.getElementById("docente-correo").value = "";
  document.getElementById("docente-tipo").value = "TC";

  await cargarDocentes();
}

async function eliminarDocente(id) {
  if (!confirm("¿Eliminar este docente?")) return;

  await api(`/api/docentes/${id}`, {
    method: "DELETE"
  });

  await cargarDocentes();
  await cargarDisponibilidad();
  await cargarElegibilidad();
}


// ==========================================================
// CURSOS
// ==========================================================

async function cargarCursos() {
  const cursos = await api("/api/cursos");

  document.getElementById("tabla-cursos").innerHTML = cursos.map(c => `
    <tr>
      <td>${c.id}</td>
      <td>${c.nombre}</td>
      <td>${c.codigo}</td>
      <td>${c.sesiones_semana}</td>
      <td><button onclick="eliminarCurso(${c.id})">Eliminar</button></td>
    </tr>
  `).join("");

  const opciones = cursos.map(c => option(c.id, `${c.id} - ${c.nombre}`)).join("");

  document.getElementById("grupo-curso").innerHTML = opciones;
  document.getElementById("eleg-curso").innerHTML = opciones;
}

async function crearCurso() {
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

  if (!curso.nombre || !curso.codigo) {
    alert("Debe ingresar nombre y código del curso.");
    return;
  }

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
}

async function eliminarCurso(id) {
  if (!confirm("¿Eliminar este curso?")) return;

  await api(`/api/cursos/${id}`, {
    method: "DELETE"
  });

  await cargarCursos();
  await cargarGrupos();
  await cargarElegibilidad();
}


// ==========================================================
// GRUPOS
// ==========================================================

async function cargarGrupos() {
  const grupos = await api("/api/grupos");

  document.getElementById("tabla-grupos").innerHTML = grupos.map(g => `
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
  const grupo = {
    id_curso: Number(document.getElementById("grupo-curso").value),
    nombre_grupo: document.getElementById("grupo-nombre").value.trim(),
    cupo_objetivo: Number(document.getElementById("grupo-cupo").value),
    inscritos: Number(document.getElementById("grupo-inscritos").value),
    estado: "Activo"
  };

  if (!grupo.id_curso || !grupo.nombre_grupo) {
    alert("Debe seleccionar un curso e ingresar nombre del grupo.");
    return;
  }

  await api("/api/grupos", {
    method: "POST",
    body: JSON.stringify(grupo)
  });

  document.getElementById("grupo-nombre").value = "";
  document.getElementById("grupo-cupo").value = 40;
  document.getElementById("grupo-inscritos").value = 0;

  await cargarGrupos();
}

async function eliminarGrupo(id) {
  if (!confirm("¿Eliminar este grupo?")) return;

  await api(`/api/grupos/${id}`, {
    method: "DELETE"
  });

  await cargarGrupos();
}


// ==========================================================
// AULAS
// ==========================================================

async function cargarAulas() {
  const aulas = await api("/api/aulas");

  document.getElementById("tabla-aulas").innerHTML = aulas.map(a => `
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
  const aula = {
    codigo: document.getElementById("aula-codigo").value.trim(),
    capacidad: Number(document.getElementById("aula-capacidad").value),
    tiene_computadores: document.getElementById("aula-computadores").checked,
    tiene_sillas_moviles: document.getElementById("aula-sillas").checked,
    edificio: document.getElementById("aula-edificio").value.trim(),
    estado: true
  };

  if (!aula.codigo || !aula.capacidad) {
    alert("Debe ingresar código y capacidad del aula.");
    return;
  }

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
}

async function eliminarAula(id) {
  if (!confirm("¿Eliminar esta aula?")) return;

  await api(`/api/aulas/${id}`, {
    method: "DELETE"
  });

  await cargarAulas();
}


// ==========================================================
// PARAMETROS DE SEMESTRE
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

  await api("/api/parametros-semestre", {
    method: "POST",
    body: JSON.stringify(parametro)
  });

  await cargarParametroSemestre();
  alert("Parámetros del semestre guardados correctamente");
}


// ==========================================================
// FRANJAS HORARIAS
// ==========================================================

async function cargarFranjas() {
  const franjas = await api("/api/franjas");

  document.getElementById("tabla-franjas").innerHTML = franjas.map(f => `
    <tr>
      <td>${f.id}</td>
      <td>${f.dia_semana}</td>
      <td>${f.hora_inicio}</td>
      <td>${f.hora_fin}</td>
      <td>${f.bloqueada ? "Sí" : "No"}</td>
      <td><button onclick="eliminarFranja(${f.id})">Eliminar</button></td>
    </tr>
  `).join("");

  document.getElementById("disp-franja").innerHTML = franjas.map(f =>
    option(f.id, `${f.id} - ${f.dia_semana} ${f.hora_inicio}-${f.hora_fin}`)
  ).join("");
}

async function crearFranja() {
  const franja = {
    dia_semana: document.getElementById("franja-dia").value,
    hora_inicio: document.getElementById("franja-inicio").value.trim(),
    hora_fin: document.getElementById("franja-fin").value.trim(),
    bloqueada: document.getElementById("franja-bloqueada").checked
  };

  if (!franja.hora_inicio || !franja.hora_fin) {
    alert("Debe ingresar hora de inicio y hora de fin.");
    return;
  }

  await api("/api/franjas", {
    method: "POST",
    body: JSON.stringify(franja)
  });

  document.getElementById("franja-inicio").value = "";
  document.getElementById("franja-fin").value = "";
  document.getElementById("franja-bloqueada").checked = false;

  await cargarFranjas();
}

async function eliminarFranja(id) {
  if (!confirm("¿Eliminar esta franja?")) return;

  await api(`/api/franjas/${id}`, {
    method: "DELETE"
  });

  await cargarFranjas();
  await cargarDisponibilidad();
}


// ==========================================================
// DISPONIBILIDAD DOCENTE
// ==========================================================

async function cargarDisponibilidad() {
  const disponibilidad = await api("/api/disponibilidad");

  document.getElementById("tabla-disponibilidad").innerHTML = disponibilidad.map(d => `
    <tr>
      <td>${d.id}</td>
      <td>${d.id_docente}</td>
      <td>${d.id_franja}</td>
      <td><button onclick="eliminarDisponibilidad(${d.id})">Eliminar</button></td>
    </tr>
  `).join("");
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
}

async function eliminarDisponibilidad(id) {
  if (!confirm("¿Eliminar esta disponibilidad?")) return;

  await api(`/api/disponibilidad/${id}`, {
    method: "DELETE"
  });

  await cargarDisponibilidad();
}


// ==========================================================
// ELEGIBILIDAD DOCENTE-CURSO
// ==========================================================

async function cargarElegibilidad() {
  const elegibilidad = await api("/api/elegibilidad");

  document.getElementById("tabla-elegibilidad").innerHTML = elegibilidad.map(e => `
    <tr>
      <td>${e.id}</td>
      <td>${e.id_docente}</td>
      <td>${e.id_curso}</td>
      <td><button onclick="eliminarElegibilidad(${e.id})">Eliminar</button></td>
    </tr>
  `).join("");
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
}

async function eliminarElegibilidad(id) {
  if (!confirm("¿Eliminar esta elegibilidad?")) return;

  await api(`/api/elegibilidad/${id}`, {
    method: "DELETE"
  });

  await cargarElegibilidad();
}


// ==========================================================
// MOTOR DE HORARIOS
// ==========================================================

async function generarHorario() {
  const resultado = await api("/api/generar-horario", {
    method: "POST"
  });

  document.getElementById("resultado-resumen").innerHTML = `
    <p><strong>Horario ID:</strong> ${resultado.horario_id}</p>
    <p><strong>Estado:</strong> ${resultado.estado}</p>
    <p><strong>Puntaje total:</strong> ${resultado.puntaje_total}</p>
    <p><strong>Total asignadas:</strong> ${resultado.total_asignadas}</p>
    <p><strong>Total conflictos:</strong> ${resultado.total_conflictos}</p>
  `;

  document.getElementById("tabla-resultados").innerHTML =
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

  document.getElementById("lista-conflictos").innerHTML =
    (resultado.conflictos || []).map(c => `
      <li>
        <strong>${c.id_restriccion}</strong>: ${c.descripcion}
      </li>
    `).join("");

  await cargarHorarios();
}


// ==========================================================
// HISTORIAL, PUBLICACIÓN Y EXPORTACIÓN DE HORARIOS
// ==========================================================

async function cargarHorarios() {
  const horarios = await api("/api/horarios");

  const tabla = document.getElementById("tabla-horarios");

  if (!tabla) return;

  tabla.innerHTML = horarios.map(h => {
    const fecha = h.fecha_generacion
      ? new Date(h.fecha_generacion).toLocaleString()
      : "";

    const puedePublicar = h.estado === "Valido" && !h.es_oficial;

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
          ${!h.es_oficial ? `<button onclick="eliminarHorario(${h.id})">Eliminar</button>` : ""}
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

document.addEventListener("DOMContentLoaded", () => {
  actualizarEstadoLogin();
  cargarTodo();
});