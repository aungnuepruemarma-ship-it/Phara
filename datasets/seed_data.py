"""
Seed script: creates demo data for local development.
Run from the repo root: python datasets/seed_data.py
Requires the backend dependencies and a running Postgres/Qdrant.
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://phara:changeme@localhost:5432/pharalab")

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

ADMIN_EMAIL = "admin@lab.local"
ADMIN_PASSWORD = "Admin1234!"


async def main():
    from app.models.user import User, Role
    from app.models.project import Project
    from app.models.experiment import Experiment
    from app.services.auth_service import hash_password

    async with SessionLocal() as db:
        # Admin user
        from sqlalchemy import select
        existing = (await db.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one_or_none()
        if not existing:
            admin = User(
                id=uuid.uuid4(),
                email=ADMIN_EMAIL,
                full_name="Lab Admin",
                hashed_password=hash_password(ADMIN_PASSWORD),
                role=Role.admin,
            )
            db.add(admin)
            await db.flush()
        else:
            admin = existing

        # Researcher user
        researcher_email = "researcher@lab.local"
        existing_r = (await db.execute(select(User).where(User.email == researcher_email))).scalar_one_or_none()
        if not existing_r:
            researcher = User(
                id=uuid.uuid4(),
                email=researcher_email,
                full_name="Demo Researcher",
                hashed_password=hash_password("Research123!"),
                role=Role.researcher,
            )
            db.add(researcher)
            await db.flush()
        else:
            researcher = existing_r

        # Projects
        p1 = Project(id=uuid.uuid4(), owner_id=admin.id, name="Mathematical Intelligence", description="Exploring formal models of intelligence and learning theory.", tags=["math", "learning-theory", "intelligence"])
        p2 = Project(id=uuid.uuid4(), owner_id=admin.id, name="Neural Scaling Laws", description="Investigating empirical laws governing large neural network behavior.", tags=["scaling", "deep-learning", "empirical"])
        db.add_all([p1, p2])
        await db.flush()

        # Experiments
        exp1 = Experiment(id=uuid.uuid4(), project_id=p1.id, title="PAC-Learning Bounds Review", description="Systematic review of PAC-learning bounds for neural architectures.", parameters={"model_class": "neural_nets", "complexity_measure": "VC_dimension"}, status="draft")
        exp2 = Experiment(id=uuid.uuid4(), project_id=p2.id, title="Chinchilla Scaling Analysis", description="Reproducing and extending Chinchilla scaling law experiments.", parameters={"dataset": "pile", "param_range": "1M-70B"}, status="draft")
        db.add_all([exp1, exp2])

        await db.commit()
        print(f"✓ Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"✓ Researcher: {researcher_email} / Research123!")
        print(f"✓ Projects: '{p1.name}', '{p2.name}'")
        print(f"✓ Experiments: '{exp1.title}', '{exp2.title}'")
        print("\nTo upload sample papers and run a workflow, start the app and use the UI or API.")


if __name__ == "__main__":
    asyncio.run(main())
