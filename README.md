# 🗓️ Programación de Horarios de Clase — MVP

**Proyecto Núcleo II · Universidad El Bosque · Ingeniería de Sistemas**

Sistema web para generación automática de horarios académicos con motor de backtracking y validación de restricciones duras y blandas.

---

## 📋 Descripción del Proyecto

Este MVP implementa el núcleo funcional de un sistema de programación de horarios académicos. El componente central **no es la interfaz de registro**, sino el **Motor de Horarios**: un algoritmo de backtracking con heurísticas de ordenamiento que asigna docentes, aulas y franjas horarias a cada sesión de clase respetando un conjunto formalizado de restricciones.

---

## ⚙️ Requisitos Previos

- Python 3.11+
- Docker Desktop
- Visual Studio Code
- Git

---

## Tecnologías

- FastAPI
- SQLAlchemy
- PostgreSQL 15
- HTML, CSS y JavaScript
- Redis 7
- Docker Compose

## 🚀 Instalación

```bash
# 1. Clonar o descomprimir el proyecto
cd horarios-app

# 2. Crear entorno virtual
python -m venv venv

# En Windows:
venv\Scripts\activate

# En Mac/Linux:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## ▶️ Ejecución

```bash
# Asegúrate de tener el entorno virtual activo
uvicorn main:app --reload --port 8000
```

Abre el navegador en: **http://localhost:8000**

La base de datos SQLite (`horarios.db`) se crea automáticamente al iniciar.


## Ejecución con PostgreSQL

### 1. Levantar PostgreSQL y Redis

```bash
docker compose up -d


---

## 📁 Estructura del Proyecto

```
horarios-app/
│
├── README.md              ← Este archivo
├── requirements.txt       ← Dependencias Python
├── main.py                ← Servidor FastAPI, rutas y endpoints
├── database.py            ← Conexión SQLite + sesión SQLAlchemy
├── models.py              ← Modelos ORM (tablas de la BD)
├── schemas.py             ← Esquemas Pydantic (validación de datos)
├── crud.py                ← Operaciones CRUD sobre la base de datos
│
├── motor/
│   ├── __init__.py        ← Módulo del motor
│   ├── generador.py       ← Algoritmo de backtracking principal
│   ├── validador.py       ← Validación de restricciones duras
│   └── restricciones.py   ← Cálculo de restricciones blandas
│
├── static/
│   ├── styles.css         ← Estilos de la interfaz
│   └── app.js             ← Lógica frontend (fetch API)
│
└── templates/
    └── index.html         ← Interfaz web SPA
```

---

## 🖥️ Uso Básico

### Flujo recomendado:

1. **Registrar Franjas Horarias** → Define los bloques de tiempo disponibles (ej: Lunes 07:00-09:00)
2. **Registrar Aulas** → Ingresa aulas con capacidad y recursos
3. **Registrar Docentes** → Crea docentes con tipo de vinculación
4. **Registrar Disponibilidad** → Indica en qué franjas puede trabajar cada docente
5. **Registrar Cursos** → Define cursos con sesiones semanales requeridas
6. **Registrar Grupos** → Asocia grupos a cursos con cupo
7. **Registrar Elegibilidad** → Indica qué docentes pueden dictar qué cursos
8. **Generar Horario** → Ejecuta el motor de backtracking
9. **Ver Resultados** → Revisa el horario generado o los conflictos detectados

---

## 🧠 Explicación del Motor de Horarios

El motor implementa **búsqueda con retroceso (backtracking)** con las siguientes etapas:

### 1. Ordenamiento por dificultad (heurística)
Las sesiones se ordenan de mayor a menor dificultad antes de intentar asignarlas. La dificultad se calcula como el número de candidatos posibles (docentes elegibles × aulas compatibles × franjas disponibles). Esto reduce el retroceso tardío.

### 2. Generación de candidatos
Para cada sesión, el motor genera todas las combinaciones válidas de `(docente, aula, franja)`.

### 3. Validación de restricciones duras
Cada candidato es evaluado contra **todas las restricciones duras**. Si viola alguna, se descarta.

### 4. Cálculo de penalización blanda
Los candidatos válidos reciben una puntuación de penalización por restricciones blandas (días consecutivos, aprovechamiento docente). Se toma el de menor penalización.

### 5. Retroceso
Si ningún candidato es válido para una sesión, el motor retrocede (backtrack) y prueba otra asignación para la sesión anterior.

---

## 🔒 Restricciones Implementadas

### Restricciones Duras (invalidan la asignación)
| ID | Descripción |
|----|-------------|
| RA-01 | Un docente no puede estar en dos sesiones simultáneas |
| RA-02 | Un aula no puede tener dos sesiones simultáneas |
| RA-03 | Un grupo no puede estar en dos sesiones simultáneas |
| RH-01 | El docente debe estar disponible en la franja |
| RH-02 | El docente debe ser elegible para el curso |
| RH-07 | El aula debe tener los recursos requeridos por el curso |
| RH-08 | Solo se usan aulas del inventario activo |
| RH-09 | La capacidad del aula >= tamaño del grupo |
| RH-05 | No se usan franjas bloqueadas |

### Restricciones Blandas (penalizan pero no invalidan)
| ID | Descripción | Penalización |
|----|-------------|--------------|
| RS-01 | Sesiones del mismo curso en días consecutivos | +10 puntos por par consecutivo |
| RS-02 | Bajo aprovechamiento del docente | +5 puntos si docente tiene pocas horas asignadas |


*Universidad El Bosque · Programa de Ingeniería de Sistemas · 2026*

