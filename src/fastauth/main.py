"""FastAuth CLI for managing the application."""

import asyncio

import typer
import uvicorn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastauth.core.config import settings
from fastauth.core.security import get_password_hash
from fastauth.db.session import async_session, init_db
from fastauth.models.user import User, UserStatus

app = typer.Typer(
    name="fastauth",
    help="FastAuth - High-performance authentication system CLI",
    add_completion=False,
)


@app.command(name="run-server")
def run_server(
    host: str = typer.Option(
        settings.host,
        "--host",
        "-h",
        help="Host to bind the server to",
    ),
    port: int = typer.Option(
        settings.port,
        "--port",
        "-p",
        help="Port to bind the server to",
    ),
    reload: bool = typer.Option(
        settings.debug,
        "--reload",
        "-r",
        help="Enable auto-reload on code changes",
    ),
) -> None:
    """Start the FastAuth application server."""
    typer.echo(f"🚀 Starting FastAuth server on {host}:{port}")
    typer.echo(f"📝 Debug mode: {settings.debug}")
    typer.echo(f"🗄️  Database: {settings.database_url.split('://')[0]}")

    uvicorn.run(
        "fastauth.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info" if settings.debug else "warning",
    )


@app.command(name="create-superuser")
def create_superuser(
    email: str = typer.Option(
        ...,
        "--email",
        "-e",
        prompt="Email",
        help="Superuser email address",
    ),
    password: str = typer.Option(
        ...,
        "--password",
        "-p",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Superuser password",
    ),
    first_name: str = typer.Option(
        None,
        "--first-name",
        "-f",
        prompt="First name (optional)",
        help="Superuser first name",
    ),
    last_name: str = typer.Option(
        None,
        "--last-name",
        "-l",
        prompt="Last name (optional)",
        help="Superuser last name",
    ),
) -> None:
    """Create a superuser account."""
    asyncio.run(_create_superuser(email, password, first_name, last_name))


async def _create_superuser(
    email: str,
    password: str,
    first_name: str | None,
    last_name: str | None,
) -> None:
    """Async helper to create a superuser."""
    typer.echo("\n🔧 Initializing database...")

    # Initialize database
    await init_db()

    async with async_session() as session:
        session: AsyncSession

        # Check if user already exists
        result = await session.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            typer.echo(f"❌ User with email '{email}' already exists!", err=True)
            raise typer.Exit(code=1)

        # Create superuser
        hashed_password = get_password_hash(password)
        superuser = User(
            email=email,
            hashed_password=hashed_password,
            first_name=first_name or "",
            last_name=last_name or "",
            is_active=True,
            is_superuser=True,
            status=UserStatus.ACTIVE,
        )

        session.add(superuser)
        await session.commit()
        await session.refresh(superuser)

        typer.echo("\n✅ Superuser created successfully!")
        typer.echo(f"📧 Email: {superuser.email}")
        typer.echo(f"👤 Name: {superuser.first_name} {superuser.last_name}".strip())
        typer.echo(f"🆔 ID: {superuser.id}")
        typer.echo(f"⚡ Status: {superuser.status.value}")


@app.command(name="init-db")
def init_database() -> None:
    """Initialize the database tables."""
    typer.echo("🔧 Initializing database...")

    asyncio.run(_init_database())

    typer.echo("✅ Database initialized successfully!")
    typer.echo(f"🗄️  Database: {settings.database_url}")


async def _init_database() -> None:
    """Async helper to initialize database."""
    await init_db()


@app.command(name="version")
def version() -> None:
    """Show FastAuth version information."""
    typer.echo(f"FastAuth v{settings.app_version}")
    typer.echo(f"Database: {settings.database_url.split('://')[0]}")
    typer.echo(f"Python JWT Algorithm: {settings.algorithm}")


if __name__ == "__main__":
    app()
