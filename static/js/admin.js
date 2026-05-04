// ==========================================================
// admin.js
// Panel del Administrador.
// ==========================================================

async function cargarUsuarios() {
  const usuarios = await api("/api/usuarios");
  const tabla = document.getElementById("tabla-usuarios");

  const usuarioActual = obtenerUsuario();

  const totalAdminsActivos = usuarios.filter(u =>
    u.rol === "Administrador" && u.estado
  ).length;

  tabla.innerHTML = usuarios.map(u => {
    const esMiUsuario = usuarioActual && Number(usuarioActual.id) === Number(u.id);
    const esUltimoAdminActivo =
      u.rol === "Administrador" &&
      u.estado &&
      totalAdminsActivos <= 1;

    let accion = "";

    if (!u.estado) {
      accion = `<span class="badge badge-warning">Inactivo</span>`;
    } else if (esMiUsuario) {
      accion = `<span class="badge">Usuario actual</span>`;
    } else if (esUltimoAdminActivo) {
      accion = `<span class="badge badge-warning">Último admin</span>`;
    } else {
      accion = `
        <button type="button" onclick="eliminarUsuario(${u.id}, '${u.nombre.replace(/'/g, "\\'")}')">
          Eliminar
        </button>
      `;
    }

    return `
      <tr>
        <td>${u.id}</td>
        <td>${u.nombre}</td>
        <td>${u.correo}</td>
        <td><span class="badge">${u.rol}</span></td>
        <td>${u.estado ? "Activo" : "Inactivo"}</td>
        <td>${accion}</td>
      </tr>
    `;
  }).join("");
}

async function crearUsuario() {
  const usuario = {
    nombre: document.getElementById("usuario-nombre").value.trim(),
    correo: document.getElementById("usuario-correo").value.trim(),
    password: document.getElementById("usuario-password").value.trim(),
    rol: document.getElementById("usuario-rol").value,
    estado: true
  };

  if (!usuario.nombre || !usuario.correo || !usuario.password) {
    alert("Debe completar nombre, correo y contraseña.");
    return;
  }

  if (usuario.password.length < 6) {
    alert("La contraseña debe tener mínimo 6 caracteres.");
    return;
  }

  await api("/api/usuarios", {
    method: "POST",
    body: JSON.stringify(usuario)
  });

  document.getElementById("usuario-nombre").value = "";
  document.getElementById("usuario-correo").value = "";
  document.getElementById("usuario-password").value = "";
  document.getElementById("usuario-rol").value = "Consulta";

  await cargarUsuarios();
  alert("Usuario creado correctamente.");
}

async function eliminarUsuario(id, nombre) {
  if (!confirm(`¿Deseas eliminar/desactivar al usuario "${nombre}"?`)) {
    return;
  }

  await api(`/api/usuarios/${id}`, {
    method: "DELETE"
  });

  alert("Usuario eliminado correctamente. El usuario quedó inactivo y ya no podrá iniciar sesión.");
  await cargarUsuarios();
}

async function cargarDatosIniciales() {
  if (!confirm("¿Deseas cargar los datos académicos iniciales?")) return;

  const resultado = await api("/api/seed/datos-academicos", { method: "POST" });
  const contenedor = document.getElementById("seed-resultado");

  if (!contenedor) return;

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

async function cargarHorarios() {
  const horarios = await api("/api/horarios");
  const tabla = document.getElementById("tabla-horarios");

  tabla.innerHTML = horarios.map(h => {
    const fecha = h.fecha_generacion ? new Date(h.fecha_generacion).toLocaleString() : "";

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
          <button type="button" onclick="exportarHorarioCSV(${h.id})">Exportar CSV</button>
          ${!h.es_oficial ? `<button type="button" onclick="eliminarHorario(${h.id})">Eliminar</button>` : ""}
        </td>
      </tr>
    `;
  }).join("");
}

async function eliminarHorario(id) {
  if (!confirm("¿Eliminar este horario? Solo se permite si no es oficial.")) return;

  await api(`/api/horarios/${id}`, { method: "DELETE" });
  alert("Horario eliminado correctamente.");
  await cargarHorarios();
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
  if (!protegerPagina(["Administrador"])) return;

  mostrarUsuarioActual();

  await cargarUsuarios();
  await cargarHorarios();
});