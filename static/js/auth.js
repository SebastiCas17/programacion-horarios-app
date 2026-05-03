// ==========================================================
// auth.js
// Funciones generales de sesión, JWT, API, protección de páginas y cierre de sesión
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
    console.error("Error leyendo usuario desde localStorage:", error);
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

  sessionStorage.removeItem("token");
  sessionStorage.removeItem("usuario");
}

function cerrarSesionYSalir() {
  cerrarSesion();
  window.location.replace("/login");
}

// Alias por si alguna página usa otro nombre
function logoutUsuario() {
  cerrarSesionYSalir();
}

function cerrarSesionUsuario() {
  cerrarSesionYSalir();
}

function redirigirPorRol(usuario) {
  if (!usuario || !usuario.rol) {
    alert("No se pudo identificar el rol del usuario.");
    window.location.replace("/login");
    return;
  }

  if (usuario.rol === "Administrador") {
    window.location.replace("/admin");
    return;
  }

  if (usuario.rol === "Coordinador") {
    window.location.replace("/coordinador");
    return;
  }

  if (usuario.rol === "Consulta") {
    window.location.replace("/consulta");
    return;
  }

  alert("Rol no reconocido: " + usuario.rol);
  window.location.replace("/login");
}

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

      if (response.status === 401 || response.status === 403) {
        cerrarSesion();
        window.location.replace("/login");
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

function protegerPagina(rolesPermitidos = []) {
  const usuario = obtenerUsuario();
  const token = obtenerToken();

  if (!usuario || !token) {
    window.location.replace("/login");
    return false;
  }

  if (rolesPermitidos.length > 0 && !rolesPermitidos.includes(usuario.rol)) {
    alert("No tienes permisos para acceder a esta página.");
    redirigirPorRol(usuario);
    return false;
  }

  return true;
}

function option(value, text) {
  return `<option value="${value}">${text}</option>`;
}

function mostrarUsuarioActual() {
  const contenedor = document.getElementById("usuario-actual");
  const usuario = obtenerUsuario();

  if (!contenedor) return;

  if (!usuario) {
    contenedor.innerHTML = "Usuario no identificado";
    return;
  }

  contenedor.innerHTML = `${usuario.nombre} · ${usuario.rol}`;
}