"""
seed.py
=======
Script ejecutable para cargar datos académicos iniciales.

Uso con Docker:
docker compose exec backend python seed.py
"""

import models
from database import engine, SessionLocal
from seed_data import cargar_datos_academicos_iniciales


def main():
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        resultado = cargar_datos_academicos_iniciales(db)

        print("Seed ejecutado correctamente")
        print(resultado)

    except Exception as error:
        db.rollback()
        print(f"Error ejecutando seed: {error}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()