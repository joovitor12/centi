import asyncio
import logging
import parlant.sdk as p
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from typing import List, Optional
import json
from datetime import datetime
import os

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Appointment(BaseModel):
    id: Optional[int] = None
    time: str
    description: str
    created_at: Optional[str] = None

class MCPSupabaseClient:
    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def call_mcp_tool(self, tool_name: str, arguments: dict):
        """Chama uma ferramenta do servidor MCP"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        # Headers com autenticação
        headers = {
            "Content-Type": "application/json"
        }
        
        # Adiciona chave de API se disponível
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        if supabase_key:
            headers["Authorization"] = f"Bearer {supabase_key}"
            headers["apikey"] = supabase_key
        
        try:
            response = await self.client.post(
                self.mcp_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                logger.error(f"MCP Error: {result['error']}")
                return None
            
            return result.get("result", {}).get("content", [])
        
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return None
    
    async def create_reminder(self, time: str, description: str) -> bool:
        """Cria um novo lembrete no Supabase"""
        arguments = {
            "table": "appointments",
            "data": {
                "time": time,
                "description": description,
                "created_at": datetime.now().isoformat()
            }
        }
        
        result = await self.call_mcp_tool("supabase_insert", arguments)
        return result is not None
    
    async def get_reminders(self, query: Optional[str] = None) -> List[Appointment]:
        """Recupera lembretes do Supabase"""
        arguments = {
            "table": "appointments",
            "select": "*"
        }
        
        # Se houver uma query, adiciona filtro de busca
        if query:
            arguments["filter"] = {
                "or": [
                    {"description": {"ilike": f"%{query}%"}},
                    {"time": {"ilike": f"%{query}%"}}
                ]
            }
        
        result = await self.call_mcp_tool("supabase_select", arguments)
        
        if result:
            try:
                # Processa o resultado do MCP
                appointments = []
                for item in result:
                    if isinstance(item, dict) and "text" in item:
                        # Parse do JSON retornado pelo MCP
                        data = json.loads(item["text"])
                        if isinstance(data, list):
                            for row in data:
                                appointments.append(Appointment(**row))
                        else:
                            appointments.append(Appointment(**data))
                return appointments
            except Exception as e:
                logger.error(f"Error parsing MCP result: {e}")
                return []
        
        return []
    
    async def close(self):
        await self.client.aclose()

async def main():
    # Inicializa o cliente MCP do Supabase
    mcp_client = MCPSupabaseClient("https://mcp.supabase.com/mcp?project_ref=qmgkgpebhtgydncacvah")
    
    @p.tool
    async def find_appointments(context: p.ToolContext, query: str = "") -> p.ToolResult:
        """Find appointments/reminders based on query. If no query provided, returns all appointments."""
        try:
            logger.info(f"Searching appointments with query: '{query}'")
            
            appointments = await mcp_client.get_reminders(query if query else None)
            
            if not appointments:
                return p.ToolResult(data=[], message="Nenhum lembrete encontrado.")
            
            return p.ToolResult(
                data=appointments,
                message=f"Encontrados {len(appointments)} lembrete(s)."
            )
            
        except Exception as e:
            logger.error(f"Error finding appointments: {e}")
            return p.ToolResult(error=str(e))
    
    @p.tool
    async def create_reminder(context: p.ToolContext, time: str, description: str) -> p.ToolResult:
        """Create a new reminder/appointment with specified time and description."""
        try:
            logger.info(f"Creating reminder: {time} - {description}")
            
            success = await mcp_client.create_reminder(time, description)
            
            if success:
                return p.ToolResult(
                    data={"time": time, "description": description},
                    message="Lembrete criado com sucesso!"
                )
            else:
                return p.ToolResult(error="Falha ao criar o lembrete.")
                
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return p.ToolResult(error=str(e))
    
    try:
        logger.info("Starting Parlant server...")
        async with p.Server() as server:
            logger.info("Creating agent...")
            agent = await server.create_agent(
                name="Centi",
                description="You are a professional assistant like Jarvis from Ironman. You can help users create and manage reminders/appointments.",
            )
            
            logger.info("Attaching tools...")
            await agent.attach_tool(
                condition="When user asks about appointments, schedule, calendar, or wants to find/search reminders", 
                tool=find_appointments
            )
            
            await agent.attach_tool(
                condition="When user wants to create, add, schedule, or set a reminder or appointment",
                tool=create_reminder
            )
            
            logger.info("Agent initialized successfully with Supabase MCP integration")
            logger.info("Server is running. Press Ctrl+C to stop.")
            
            # Mantém o servidor rodando
            try:
                while True:
                    await asyncio.sleep(5)
            except KeyboardInterrupt:
                logger.info("Shutting down agent...")
            finally:
                await mcp_client.close()
            
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        await mcp_client.close()
        raise
        
if __name__ == "__main__":
    asyncio.run(main())