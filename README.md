# Programación de Horarios de Clase

Sistema web académico para la **programación automática de horarios de clase**, desarrollado con **FastAPI, PostgreSQL, SQLAlchemy, HTML, CSS y JavaScript**.

El sistema permite registrar docentes, cursos, grupos, aulas, franjas horarias, disponibilidad docente y elegibilidad docente-curso. Además, incluye un **motor de generación de horarios mediante Backtracking**, validación de restricciones, autenticación JWT, roles de usuario, publicación de horario oficial y exportación a CSV.

---

## 1. Tecnologías utilizadas

- **Backend:** FastAPI
- **Frontend:** HTML, CSS y JavaScript
- **Base de datos:** PostgreSQL
- **ORM:** SQLAlchemy
- **Autenticación:** JWT
- **Contenedores:** Docker y Docker Compose
- **Servicio auxiliar:** Redis
- **Algoritmo:** Backtracking para generación de horarios

---

## 2. Funcionalidades principales

El sistema permite:

- Iniciar sesión con usuario y contraseña.
- Proteger operaciones mediante JWT y roles.
- Registrar docentes.
- Registrar cursos.
- Registrar grupos.
- Registrar aulas.
- Registrar franjas horarias.
- Configurar parámetros del semestre.
- Registrar disponibilidad docente.
- Registrar elegibilidad docente-curso.
- Cargar datos académicos iniciales.
- Generar horarios automáticamente.
- Validar restricciones duras y blandas.
- Registrar conflictos cuando un horario no es factible.
- Consultar historial de horarios generados.
- Publicar un horario como oficial.
- Evitar eliminar horarios oficiales.
- Exportar horarios en formato CSV.

---

## 3. Estructura del proyecto

```text
programacion-horarios-app/
│
├── main.py
├── database.py
├── models.py
├── schemas.py
├── crud.py
├── auth.py
├── seed.py
├── seed_data.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
│
├── motor/
│   ├── __init__.py
│   ├── generador.py
│   ├── restricciones.py
│   └── validador.py
│
├── static/
│   ├── app.js
│   └── styles.css
│
└── templates/
    └── index.html
```

---

## 4. Requisitos previos

Para ejecutar el proyecto se requiere tener instalado:

- Docker Desktop
- Git
- Navegador web

No es necesario instalar PostgreSQL manualmente, porque se ejecuta mediante Docker.

---

## 5. Ejecución del proyecto con Docker

### 5.1. Clonar el repositorio

```bash
git clone https://github.com/JimeneZz007/programacion-horarios-app.git
cd programacion-horarios-app
```

### 5.2. Levantar el sistema completo

```bash
docker compose up --build -d
```

Este comando levanta los siguientes servicios:

```text
horarios_backend   FastAPI
horarios_postgres  PostgreSQL
horarios_redis     Redis
```

### 5.3. Verificar contenedores activos

```bash
docker ps
```

Debe verse algo similar a:

```text
horarios_backend
horarios_postgres
horarios_redis
```

### 5.4. Abrir la aplicación

```text
http://localhost:8000
```

### 5.5. Abrir documentación Swagger

```text
http://localhost:8000/docs
```

---

## 6. Usuario administrador inicial

Al iniciar el sistema por primera vez, se crea automáticamente un usuario administrador:

```text
Correo: admin@horarios.edu
Contraseña: admin123
Rol: Administrador
```

Estas credenciales pueden modificarse desde el archivo `docker-compose.yml`:

```yaml
ADMIN_EMAIL: admin@horarios.edu
ADMIN_PASSWORD: admin123
ADMIN_NAME: Administrador del Sistema
```

---

## 7. Carga de datos iniciales

El sistema incluye una carga inicial de datos académicos para pruebas.

### Opción 1: Desde la interfaz web

1. Entrar a:

```text
http://localhost:8000
```

2. Iniciar sesión con:

```text
admin@horarios.edu
admin123
```

3. Ir a la sección:

```text
Datos Iniciales
```

4. Hacer clic en:

```text
Cargar Datos Iniciales
```

La carga crea datos de prueba como:

- Docentes
- Cursos
- Grupos
- Aulas
- Franjas horarias
- Disponibilidad docente
- Elegibilidad docente-curso
- Sesiones reales para el motor

La carga es **idempotente**, es decir, si los datos ya existen, no los duplica.

### Opción 2: Desde Docker

También puede ejecutarse el seed desde terminal:

```bash
docker compose exec backend python seed.py
```

---

## 8. Flujo básico de uso

1. Levantar el sistema con Docker.
2. Iniciar sesión con el usuario administrador.
3. Cargar datos iniciales.
4. Revisar docentes, cursos, grupos, aulas y franjas.
5. Generar horario.
6. Revisar resultados.
7. Publicar horario válido como oficial.
8. Exportar horario en CSV.

---

## 9. Motor de generación de horarios

El sistema implementa un motor de generación de horarios basado en **Backtracking**.

El proceso general es:

1. Preparar sesiones reales para cada grupo.
2. Construir candidatos combinando:
   - docente,
   - aula,
   - franja horaria.
3. Validar restricciones duras.
4. Calcular penalizaciones por restricciones blandas.
5. Asignar tentativamente.
6. Retroceder si una asignación impide completar el horario.
7. Registrar conflictos si no se encuentra solución factible.

El endpoint principal del motor es:

```text
POST /api/generar-horario
```

---

## 10. Restricciones implementadas

El sistema valida restricciones como:

- Disponibilidad del docente.
- Elegibilidad docente-curso.
- No cruce de docente en la misma franja.
- No cruce de aula en la misma franja.
- No cruce de grupo en la misma franja.
- Capacidad del aula frente al número de inscritos.
- Recursos requeridos por el curso.
- Rango académico de lunes a viernes.
- Rango académico de sábado.
- Franja de almuerzo bloqueada.
- Máximo de sesiones semanales.
- Mínimo de inscritos para cierre de grupo.
- Publicación de horario oficial.
- Protección de horarios oficiales frente a eliminación.

---

## 11. Parámetros del semestre

El sistema permite configurar parámetros como:

```text
Nombre del semestre
Horario lunes a viernes
Horario sábado
Franja de almuerzo
Máximo de sesiones semanales
Mínimo de inscritos para cierre de grupo
```

Estos parámetros influyen directamente en la validación del motor de horarios.

---

## 12. Publicación de horario oficial

Cuando un horario se genera con estado:

```text
Valido
```

puede publicarse como horario oficial.

Al publicarse:

- Cambia su estado a `Oficial`.
- Queda marcado como versión oficial.
- No puede eliminarse desde el sistema.

Endpoint:

```text
POST /api/horarios/{horario_id}/publicar
```

---

## 13. Exportación de horario

El sistema permite exportar un horario generado en formato CSV.

Endpoint:

```text
GET /api/horarios/{horario_id}/exportar-csv
```

El archivo exportado puede abrirse en Excel e incluye:

- ID del horario
- Estado
- Curso
- Grupo
- Sesión
- Docente
- Aula
- Día
- Hora inicio
- Hora fin
- Penalización

---

## 14. Autenticación y roles

El sistema utiliza autenticación basada en JWT.

Roles principales:

```text
Administrador
Coordinador
Docente
Consulta
```

Las operaciones críticas requieren sesión activa, por ejemplo:

- Crear datos.
- Eliminar datos.
- Generar horarios.
- Publicar horarios.
- Cargar datos iniciales.

---

## 15. Servicios Docker

El archivo `docker-compose.yml` levanta los siguientes servicios:

```text
backend   Aplicación FastAPI
postgres  Base de datos PostgreSQL
redis     Servicio Redis
```

### Apagar servicios

```bash
docker compose down
```

### Apagar y borrar volúmenes de base de datos

```bash
docker compose down -v
```

### Reconstruir desde cero

```bash
docker compose up --build -d
```

---

## 16. Ver logs del backend

```bash
docker logs horarios_backend
```

Para ver logs en tiempo real:

```bash
docker logs -f horarios_backend
```

---

## 17. Verificar la base de datos

Entrar a PostgreSQL:

```bash
docker exec -it horarios_postgres psql -U horarios_user -d horarios_db
```

Ver tablas:

```sql
\dt
```

Consultar horarios:

```sql
SELECT * FROM horarios;
```

Consultar sesiones:

```sql
SELECT id, id_grupo, numero_sesion, estado
FROM sesiones_clase
ORDER BY id;
```

Consultar asignaciones:

```sql
SELECT id, id_sesion, id_docente, id_aula, id_franja, id_horario
FROM asignaciones
ORDER BY id;
```

Salir:

```sql
\q
```

---

## 18. Comandos útiles

### Levantar todo

```bash
docker compose up --build -d
```

### Ver contenedores

```bash
docker ps
```

### Ver logs

```bash
docker logs horarios_backend
```

### Ejecutar seed

```bash
docker compose exec backend python seed.py
```

### Apagar contenedores

```bash
docker compose down
```

### Reiniciar todo desde cero

```bash
docker compose down -v
docker compose up --build -d
```

---

## 19. Ejecución local alternativa

También se puede ejecutar sin Docker para desarrollo local.

### Crear entorno virtual

```bash
python -m venv venv
```

### Activar entorno virtual en Windows

```bash
venv\Scripts\activate
```

### Instalar dependencias

```bash
pip install -r requirements.txt
```

### Ejecutar FastAPI

```bash
uvicorn main:app --reload --port 8000
```

> Para ejecución local se requiere tener PostgreSQL disponible o usar el PostgreSQL levantado por Docker.

---

## 20. Estado del proyecto

El proyecto implementa una versión funcional avanzada del sistema de programación de horarios, incluyendo:

- Backend con FastAPI.
- Frontend funcional.
- Base de datos PostgreSQL.
- Docker Compose.
- Autenticación JWT.
- Roles.
- Motor Backtracking.
- Sesiones reales.
- Restricciones.
- Publicación oficial.
- Exportación CSV.
- Datos iniciales.
- Administrador automático.

---

## 21. Autor
 
Proyecto académico desarrollado para la asignatura de Proyecto Nuleo II. 

Integrantes: Valentina Calderon, Sebastian Castillo & Santiago Jiemenez.

Sistema: **Programación de Horarios de Clase**