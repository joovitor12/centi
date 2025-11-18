# Estrutura Modular do Centi

Este documento descreve a estrutura modular do projeto Centi, seguindo as melhores práticas do Parlant.

## 📁 Estrutura de Diretórios

```
app/
├── __init__.py
├── config/              # Configurações e variáveis de ambiente
│   ├── __init__.py
│   └── settings.py      # Settings e validação de env vars
├── services/            # Serviços externos
│   ├── __init__.py
│   └── supabase_service.py      # Serviço para Supabase
├── tools/               # Tools do Parlant
│   ├── __init__.py
│   └── appointments.py  # Tools de gerenciamento de appointments
└── agent/               # Configuração do agente
    ├── __init__.py
    └── guidelines.py    # Guidelines do agente
```

## 🏗️ Arquitetura

### 1. Config (`app/config/`)

Centraliza todas as configurações e variáveis de ambiente:
- `settings.py`: Classe `Settings` com validação de variáveis obrigatórias

### 2. Services (`app/services/`)

Abstrai interações com serviços externos:

- **SupabaseService**: 
  - `get_all_appointments()`: Busca todos os appointments
  - `get_appointment_by_id()`: Busca por ID
  - `create_appointment()`: Cria novo appointment
  - `update_appointment()`: Atualiza appointment
  - `delete_appointment()`: Deleta appointment

### 3. Tools (`app/tools/`)

Tools do Parlant organizados por funcionalidade:

- **appointments.py**: 
  - `find_appointments`: Busca appointments
  - `add_appointment`: Adiciona appointment
  - `edit_appointment`: Edita appointment
  - `delete_appointment`: Deleta appointment

Cada arquivo de tools exporta uma função factory que recebe as dependências (services) e retorna uma lista de tools.

### 4. Agent (`app/agent/`)

Configuração do agente Parlant:

- **guidelines.py**: 
  - `setup_guidelines()`: Configura todas as guidelines do agente
  - Organizado por funcionalidade para fácil manutenção

## 🔌 Como Adicionar Novas Funcionalidades

### Adicionar um novo Service:

1. Crie `app/services/novo_service.py`
2. Implemente a classe do serviço
3. Importe e use no `main.py`

### Adicionar novas Tools:

1. Crie `app/tools/nova_funcionalidade.py`
2. Crie função factory `create_*_tools(services)`
3. Importe no `main.py` e adicione ao agente

### Adicionar novas Guidelines:

1. Edite `app/agent/guidelines.py`
2. Adicione nova guideline na função `setup_guidelines()`

## 📝 Boas Práticas

1. **Separação de Responsabilidades**: Cada módulo tem uma responsabilidade clara
2. **Dependency Injection**: Services são injetados nas tools via factory functions
3. **Error Handling**: Todos os services têm tratamento de erro adequado
4. **Logging**: Uso consistente de logging em todos os módulos
5. **Type Hints**: Código tipado para melhor manutenibilidade

