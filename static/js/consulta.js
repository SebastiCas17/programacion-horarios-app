// ==========================================================
// consulta.js
// Panel de consulta de horarios.
// ==========================================================

let asignacionesActuales = [];

async function cargarHorariosConsulta() {
  const horarios = await api("/api/horarios");
  const tabla = document.getElementById("tabla-horarios");

  tabla.innerHTML = horarios.map(h => {
    const fecha = h.fecha_generacion ? new Date(h.fecha_generacion).toLocaleString() : "";
    const claseOficial = h.es_oficial ? "badge badge-ok" : "badge";

    return `
      <tr>
        <td>${h.id}</td>
        <td>${fecha}</td>
        <td>${h.estado}</td>
        <td><span class="${claseOficial}">${h.es_oficial ? "Sí" : "No"}</span></td>
        <td>${h.num_asignaciones}</td>
        <td>${h.num_conflictos}</td>
        <td>
          <button onclick="verHorario(${h.id})">Ver</button>
          <button onclick="exportarHorarioCSV(${h.id})">Exportar CSV</button>
        </td>
      </tr>
    `;
  }).join("");
}

async function verHorario(id) {
  const horario = await api(`/api/horarios/${id}`);
  asignacionesActuales = horario.asignaciones || [];

  const resumen = document.getElementById("detalle-resumen");
  resumen.innerHTML = `
    <strong>Horario ID:</strong> ${horario.id}<br>
    <strong>Estado:</strong> ${horario.estado}<br>
    <strong>Oficial:</strong> ${horario.es_oficial ? "Sí" : "No"}<br>
    <strong>Total asignaciones:</strong> ${asignacionesActuales.length}<br>
    <strong>Total conflictos:</strong> ${(horario.conflictos || []).length}
  `;

  pintarAsignaciones(asignacionesActuales);
}

function pintarAsignaciones(asignaciones) {
  const tabla = document.getElementById("tabla-detalle-horario");

  tabla.innerHTML = asignaciones.map(a => `
    <tr>
      <td>${a.curso_nombre || ""}</td>
      <td>${a.grupo_nombre || ""}</td>
      <td>${a.numero_sesion || ""}</td>
      <td>${a.docente_nombre || ""}</td>
      <td>${a.aula_codigo || ""}</td>
      <td>${a.franja_dia || ""}</td>
      <td>${a.franja_inicio || ""} - ${a.franja_fin || ""}</td>
    </tr>
  `).join("");
}

function aplicarFiltroHorario() {
  const filtro = document.getElementById("filtro-horario").value.toLowerCase().trim();

  if (!filtro) {
    pintarAsignaciones(asignacionesActuales);
    return;
  }

  const filtradas = asignacionesActuales.filter(a => {
    const texto = [
      a.curso_nombre,
      a.grupo_nombre,
      a.docente_nombre,
      a.aula_codigo,
      a.franja_dia,
      a.franja_inicio,
      a.franja_fin
    ].join(" ").toLowerCase();

    return texto.includes(filtro);
  });

  pintarAsignaciones(filtradas);
}

async function exportarHorarioCSV(id) {
  const token = obtenerToken();
  const headers = token ? { "Authorization": `Bearer ${token}` } : {};

  const response = await fetch(`/api/horarios/${id}/exportar-csv`, { headers });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    alert(data?.detail || "No se pudo exportar el horario");
    return;
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
}

document.addEventListener("DOMContentLoaded", async () => {
  if (!protegerPagina(["Administrador", "Coordinador", "Consulta"])) return;
  await cargarHorariosConsulta();
});
