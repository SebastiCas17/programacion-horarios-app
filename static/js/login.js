// ==========================================================
// login.js
// Inicio de sesión con JWT y redirección según rol
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

function mostrarCredencialesPorRol() {
  const rol = document.getElementById("login-rol").value;
  const correo = document.getElementById("login-correo");
  const password = document.getElementById("login-password");

  if (rol === "Administrador") {
    correo.value = "admin@horarios.edu";
    password.value = "admin123";
  }

  if (rol === "Coordinador") {
    correo.value = "coordinador@horarios.edu";
    password.value = "coord123";
  }

  if (rol === "Consulta") {
    correo.value = "consulta@horarios.edu";
    password.value = "consulta123";
  }
}

function redirigirPorRol(usuario) {
  if (!usuario || !usuario.rol) {
    alert("No se pudo identificar el rol del usuario.");
    return;
  }

  if (usuario.rol === "Administrador") {
    window.location.href = "/admin";
    return;
  }

  if (usuario.rol === "Coordinador") {
    window.location.href = "/coordinador";
    return;
  }

  if (usuario.rol === "Consulta") {
    window.location.href = "/consulta";
    return;
  }

  alert("Rol no reconocido: " + usuario.rol);
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
  redirigirPorRol(data.usuario);
}

function logoutUsuario() {
  cerrarSesion();
  window.location.href = "/login";
}

document.addEventListener("DOMContentLoaded", () => {
  const usuario = obtenerUsuario();

  if (usuario) {
    redirigirPorRol(usuario);
    return;
  }

  const selectorRol = document.getElementById("login-rol");

  if (selectorRol) {
    selectorRol.addEventListener("change", mostrarCredencialesPorRol);
    mostrarCredencialesPorRol();
  }
});
