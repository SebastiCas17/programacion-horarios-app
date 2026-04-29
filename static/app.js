async function api(url, options = {}) {
  try {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(data?.detail || "Error en la petición");
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

async function cargarTodo() {
  await Promise.all([
    cargarDocentes(),
    cargarCursos(),
    cargarGrupos(),
    cargarAulas(),
    cargarFranjas(),
    cargarDisponibilidad(),
    cargarElegibilidad()
  ]);
}

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
    nombre: document.getElementById("docente-nombre").value,
    correo: document.getElementById("docente-correo").value,
    tipo_vinculacion: document.getElementById("docente-tipo").value,
    estado: true
  };

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

  await api(`/api/docentes/${id}`, { method: "DELETE" });
  await cargarDocentes();
  await cargarDisponibilidad();
  await cargarElegibilidad();
}

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
    nombre: document.getElementById("curso-nombre").value,
    codigo: document.getElementById("curso-codigo").value,
    creditos: Number(document.getElementById("curso-creditos").value),
    sesiones_semana: Number(document.getElementById("curso-sesiones").value),
    duracion_sesion_h: 2,
    requiere_computadores: document.getElementById("curso-computadores").checked,
    requiere_sillas_moviles: document.getElementById("curso-sillas").checked,
    estado: true
  };

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

  await api(`/api/cursos/${id}`, { method: "DELETE" });
  await cargarCursos();
  await cargarGrupos();
  await cargarElegibilidad();
}

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
    nombre_grupo: document.getElementById("grupo-nombre").value,
    cupo_objetivo: Number(document.getElementById("grupo-cupo").value),
    inscritos: Number(document.getElementById("grupo-inscritos").value),
    estado: "Activo"
  };

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

  await api(`/api/grupos/${id}`, { method: "DELETE" });
  await cargarGrupos();
}

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
    codigo: document.getElementById("aula-codigo").value,
    capacidad: Number(document.getElementById("aula-capacidad").value),
    tiene_computadores: document.getElementById("aula-computadores").checked,
    tiene_sillas_moviles: document.getElementById("aula-sillas").checked,
    edificio: document.getElementById("aula-edificio").value,
    estado: true
  };

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

  await api(`/api/aulas/${id}`, { method: "DELETE" });
  await cargarAulas();
}

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
    hora_inicio: document.getElementById("franja-inicio").value,
    hora_fin: document.getElementById("franja-fin").value,
    bloqueada: document.getElementById("franja-bloqueada").checked
  };

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

  await api(`/api/franjas/${id}`, { method: "DELETE" });
  await cargarFranjas();
  await cargarDisponibilidad();
}

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

  await api("/api/disponibilidad", {
    method: "POST",
    body: JSON.stringify(disponibilidad)
  });

  await cargarDisponibilidad();
}

async function eliminarDisponibilidad(id) {
  if (!confirm("¿Eliminar esta disponibilidad?")) return;

  await api(`/api/disponibilidad/${id}`, { method: "DELETE" });
  await cargarDisponibilidad();
}

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

  await api("/api/elegibilidad", {
    method: "POST",
    body: JSON.stringify(elegibilidad)
  });

  await cargarElegibilidad();
}

async function eliminarElegibilidad(id) {
  if (!confirm("¿Eliminar esta elegibilidad?")) return;

  await api(`/api/elegibilidad/${id}`, { method: "DELETE" });
  await cargarElegibilidad();
}

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
}

document.addEventListener("DOMContentLoaded", cargarTodo);