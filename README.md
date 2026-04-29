# 🗓️ Programación de Horarios de Clase — MVP

**Proyecto Núcleo II · Universidad El Bosque · Ingeniería de Sistemas**

Sistema web para generación automática de horarios académicos con motor de backtracking y validación de restricciones duras y blandas.

---

## 📋 Descripción del Proyecto

Este MVP implementa el núcleo funcional de un sistema de programación de horarios académicos. El componente central **no es la interfaz de registro**, sino el **Motor de Horarios**: un algoritmo de backtracking con heurísticas de ordenamiento que asigna docentes, aulas y franjas horarias a cada sesión de clase respetando un conjunto formalizado de restricciones.

---

## ⚙️ Requisitos Previos

- Python 3.11 o superior
- pip (gestor de paquetes de Python)
- Visual Studio Code (recomendado)
- Navegador web moderno

---

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

---

## 📝 Commits Sugeridos (Evidencia de Participación Individual)

```bash
# Commit 1 - Sebastián Castillo
git commit -m "feat: estructura inicial del proyecto - FastAPI, SQLite, carpetas motor y templates"

# Commit 2 - David Jiménez  
git commit -m "feat: modelos ORM y base de datos - Docente, Curso, Grupo, Aula, FranjaHoraria, SesionClase"

# Commit 3 - Valentina Calderón
git commit -m "feat: schemas Pydantic y CRUD básico para todas las entidades"

# Commit 4 - Sebastián Castillo
git commit -m "feat: validador de restricciones duras (RA-01, RA-02, RA-03, RH-01 a RH-09)"

# Commit 5 - David Jiménez
git commit -m "feat: motor de backtracking con heurísticas de ordenamiento por dificultad"

# Commit 6 - Valentina Calderón
git commit -m "feat: restricciones blandas RS-01 y RS-02, cálculo de penalización"

# Commit 7 - Sebastián Castillo
git commit -m "feat: endpoints FastAPI para generación de horario y consulta de resultados"

# Commit 8 - David Jiménez
git commit -m "feat: frontend HTML/CSS/JS - formularios de registro y visualización de horario"

# Commit 9 - Valentina Calderón
git commit -m "feat: reporte de conflictos con ID de restricción violada y entidad responsable"

# Commit 10 - Todo el equipo
git commit -m "docs: README completo, pruebas finales y evidencia de restricciones"
```

---

## ✅ Cómo Probar que el Motor Cumple el MVP

### Prueba 1: Generación exitosa
1. Registra 2 franjas (Lunes 07:00-09:00, Martes 07:00-09:00)
2. Registra 1 aula (capacidad 30)
3. Registra 1 docente
4. Registra disponibilidad del docente en ambas franjas
5. Registra 1 curso con 2 sesiones/semana
6. Registra 1 grupo con 25 inscritos
7. Registra elegibilidad docente-curso
8. Clic en "Generar Horario"
9. **Esperado**: Horario válido con 2 sesiones asignadas

### Prueba 2: Detección de conflicto RA-01 (docente duplicado)
1. Misma configuración anterior pero solo 1 franja disponible y 2 grupos del mismo curso
2. **Esperado**: Conflicto RA-01 reportado con descripción del docente afectado

### Prueba 3: Restricción RH-02 (elegibilidad)
1. Registra docente SIN elegibilidad para el curso
2. **Esperado**: Conflicto RH-02 "Docente no elegible para el curso"

### Prueba 4: Restricción RH-09 (capacidad)
1. Aula con capacidad 10, grupo con 30 inscritos
2. **Esperado**: Conflicto RH-09 "Capacidad insuficiente"

### Endpoint directo para pruebas:
```
POST http://localhost:8000/api/generar-horario
GET  http://localhost:8000/api/horario/{id}
GET  http://localhost:8000/docs  ← Swagger UI para pruebas interactivas
```

---

## 🔮 Ampliaciones Futuras (No implementadas en MVP)

- **Celery + Redis**: Para procesamiento asíncrono de la generación (reemplaza la ejecución síncrona actual)
- **JWT**: Autenticación por roles (Administrador, Coordinador, Docente)
- **PostgreSQL**: Migración desde SQLite para producción (solo cambia `DATABASE_URL` en `database.py`)
- **Algoritmos genéticos / recocido simulado**: Para mejorar la calidad de las restricciones blandas

---

*Universidad El Bosque · Programa de Ingeniería de Sistemas · 2026*
