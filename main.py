import asyncio
import logging
from typing import List
import parlant.sdk as p
from pydantic import BaseModel
from dotenv import load_dotenv

# SQLAlchemy imports para conexão com Postgres
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:54322/postgres"

# Criação da engine SQLAlchemy
engine = create_engine(DATABASE_URL, echo=True, future=True)

# Teste simples de conexão
def test_db_connection():
    try:
        with engine.connect() as conn:
            logger.info("Conexão com o banco de dados estabelecida com sucesso!")
    except OperationalError as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")

class Appointment(BaseModel):
    time: str
    description: str

async def main():
    @p.tool
    async def find_appointments(context: p.ToolContext, query: str) -> p.ToolResult:
        """Find appointments based on query."""
        try:
            logger.info(f"Query received: {query}")
            
            # Simulação de dados - substituir por chamada real ao banco
            appointments = [
                Appointment(time="10 AM tomorrow", description="Meeting with the team"),
                Appointment(time="2 PM today", description="Doctor appointment"),
            ]
            
            return p.ToolResult(data=appointments)
        except Exception as e:
            logger.error(f"Error finding appointments: {e}")
            return p.ToolResult(error=str(e))
    
    try:
        async with p.Server() as server:
            agent = await server.create_agent(
                name="Centi",
                description="You are a professional assistant like Jarvis from Ironman.",
            )
            
            await agent.attach_tool(
                condition="When user asks about appointments, schedule, or calendar", 
                tool=find_appointments
            )
            
            logger.info("Agent initialized successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise

if __name__ == "__main__":
    test_db_connection()
    asyncio.run(main())