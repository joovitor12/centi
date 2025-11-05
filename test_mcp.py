import asyncio
import logging
from dotenv import load_dotenv
import httpx
import json
import os

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_connection():
    """Testa a conexão com o servidor MCP do Supabase"""
    mcp_url = "https://mcp.supabase.com/mcp?project_ref=qmgkgpebhtgydncacvah"
    
    # Headers com autenticação
    headers = {
        "Content-Type": "application/json"
    }
    
    # Adiciona chave de API se disponível
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    if supabase_key and supabase_key != "your_supabase_anon_key_here":
        headers["Authorization"] = f"Bearer {supabase_key}"
        headers["apikey"] = supabase_key
        logger.info("Usando chave de autenticação do Supabase")
    else:
        logger.warning("SUPABASE_ANON_KEY não encontrada no .env")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Teste 1: Listar ferramentas disponíveis
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        
        try:
            logger.info("Testando conexão com MCP Supabase...")
            response = await client.post(
                mcp_url,
                json=payload,
                headers=headers
            )
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    tools = result["result"].get("tools", [])
                    logger.info(f"Ferramentas disponíveis: {len(tools)}")
                    for tool in tools[:5]:  # Mostra apenas as primeiras 5
                        logger.info(f"- {tool.get('name', 'N/A')}: {tool.get('description', 'N/A')}")
                else:
                    logger.error(f"Erro na resposta: {result}")
            
        except Exception as e:
            logger.error(f"Erro ao testar MCP: {e}")

        # Teste 2: Tentar selecionar dados da tabela appointments
        payload2 = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "supabase_select",
                "arguments": {
                    "table": "appointments",
                    "select": "*",
                    "limit": 5
                }
            }
        }
        
        try:
            logger.info("\nTestando busca na tabela appointments...")
            response2 = await client.post(
                mcp_url,
                json=payload2,
                headers=headers
            )
            logger.info(f"Status: {response2.status_code}")
            result2 = response2.json()
            logger.info(f"Response: {json.dumps(result2, indent=2)}")
            
        except Exception as e:
            logger.error(f"Erro ao buscar appointments: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())