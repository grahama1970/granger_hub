# Aider Implementation Roadmap

## Phase 1: Foundation (Weeks 1-2)

### 1.1 Fork and Setup
```bash
# Fork aider repository
git clone https://github.com/Aider-AI/aider.git aider-daemon
cd aider-daemon
git checkout -b daemon-mode

# Set up development environment
python -m venv venv
source venv/bin/activate
pip install -e .
pip install websockets asyncio
```

### 1.2 Daemon Mode Prototype
```python
# aider/daemon.py
import asyncio
import websockets
import json
from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model

class AiderDaemon:
    def __init__(self, model_name='gpt-4', host='localhost', port=8765):
        self.model_name = model_name
        self.host = host
        self.port = port
        self.coder = None
        self.io = None
        
    async def initialize(self):
        # Initialize non-interactive IO
        self.io = InputOutput(
            yes=True,
            chat_history_file=f".aider.daemon.{self.port}.history",
            input_history_file=None,
            check_update=False
        )
        
        # Initialize model and coder
        model = Model(self.model_name)
        self.coder = Coder.create(
            main_model=model,
            io=self.io,
            stream=False,
            use_git=False
        )
    
    async def handle_client(self, websocket, path):
        try:
            async for message in websocket:
                request = json.loads(message)
                response = await self.process_request(request)
                await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            pass
    
    async def process_request(self, request):
        request_id = request.get('id')
        action = request.get('action')
        
        try:
            if action == 'chat':
                result = self.coder.run(request.get('message'))
                return {
                    'id': request_id,
                    'success': True,
                    'result': result
                }
            elif action == 'add_files':
                files = request.get('files', [])
                for file in files:
                    self.coder.add_rel_fname(file)
                return {
                    'id': request_id,
                    'success': True,
                    'files_added': files
                }
            # Add more actions as needed
        except Exception as e:
            return {
                'id': request_id,
                'success': False,
                'error': str(e)
            }
    
    async def start(self):
        await self.initialize()
        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        print(f"Aider daemon started on ws://{self.host}:{self.port}")
        await server.wait_closed()

# CLI entry point
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='gpt-4')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    
    daemon = AiderDaemon(model_name=args.model, port=args.port)
    asyncio.run(daemon.start())
```

## Phase 2: Client Library (Week 3)

### 2.1 Python Client
```python
# aider_client.py
import asyncio
import websockets
import json
import uuid

class AiderClient:
    def __init__(self, uri='ws://localhost:8765'):
        self.uri = uri
        self.websocket = None
        
    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        
    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            
    async def send_request(self, action, **kwargs):
        request = {
            'id': str(uuid.uuid4()),
            'action': action,
            **kwargs
        }
        
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        return json.loads(response)
        
    async def chat(self, message):
        return await self.send_request('chat', message=message)
        
    async def add_files(self, files):
        return await self.send_request('add_files', files=files)

# Example usage
async def main():
    client = AiderClient()
    await client.connect()
    
    # Add files to context
    await client.add_files(['src/main.py', 'src/utils.py'])
    
    # Send chat message
    response = await client.chat("Add error handling to the main function")
    print(response)
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Phase 3: Module Communicator Integration (Weeks 4-5)

### 3.1 Aider Adapter
```python
# src/claude_coms/core/adapters/aider_adapter.py
from typing import Dict, List, Any, Optional
import asyncio
import json
from dataclasses import dataclass
from .base_adapter import BaseAdapter, AdapterConfig

@dataclass
class AiderInstance:
    name: str
    uri: str
    model: str
    capabilities: List[str]
    client: Optional[Any] = None

class AiderAdapter(BaseAdapter):
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.instances: Dict[str, AiderInstance] = {}
        self._load_instances()
        
    def _load_instances(self):
        """Load instance configurations from config"""
        for inst_config in self.config.get('instances', []):
            instance = AiderInstance(
                name=inst_config['name'],
                uri=f"ws://localhost:{inst_config['port']}",
                model=inst_config['model'],
                capabilities=inst_config.get('capabilities', [])
            )
            self.instances[instance.name] = instance
    
    async def connect(self):
        """Connect to all configured Aider instances"""
        for instance in self.instances.values():
            try:
                client = AiderClient(instance.uri)
                await client.connect()
                instance.client = client
                self.logger.info(f"Connected to Aider instance: {instance.name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {instance.name}: {e}")
    
    async def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to appropriate instance"""
        action = data.get('action')
        target_instance = data.get('instance')
        
        if target_instance:
            # Direct routing
            instance = self.instances.get(target_instance)
            if not instance or not instance.client:
                return {'success': False, 'error': f'Instance {target_instance} not available'}
            
            return await self._send_to_instance(instance, data)
        else:
            # Capability-based routing
            capability_needed = self._determine_capability(action)
            instance = self._find_instance_by_capability(capability_needed)
            
            if not instance:
                return {'success': False, 'error': f'No instance available for {capability_needed}'}
            
            return await self._send_to_instance(instance, data)
    
    async def broadcast(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Send request to all instances"""
        results = {}
        tasks = []
        
        for instance in self.instances.values():
            if instance.client:
                task = self._send_to_instance(instance, data)
                tasks.append((instance.name, task))
        
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                results[name] = {'success': False, 'error': str(e)}
        
        return results
    
    async def _send_to_instance(self, instance: AiderInstance, data: Dict[str, Any]):
        """Send request to specific instance"""
        try:
            # Map Module Communicator actions to Aider actions
            aider_action = self._map_action(data.get('action'))
            
            if aider_action == 'chat':
                response = await instance.client.chat(data.get('message', ''))
            elif aider_action == 'add_files':
                response = await instance.client.add_files(data.get('files', []))
            else:
                response = await instance.client.send_request(aider_action, **data)
            
            return {
                'success': True,
                'instance': instance.name,
                'model': instance.model,
                'result': response
            }
        except Exception as e:
            return {
                'success': False,
                'instance': instance.name,
                'error': str(e)
            }
    
    def _determine_capability(self, action: str) -> str:
        """Determine required capability from action"""
        capability_map = {
            'generate_code': 'code_generation',
            'review_code': 'code_review',
            'optimize': 'performance_optimization',
            'document': 'documentation',
            'security_check': 'security_analysis'
        }
        return capability_map.get(action, 'general')
    
    def _find_instance_by_capability(self, capability: str) -> Optional[AiderInstance]:
        """Find best instance for given capability"""
        for instance in self.instances.values():
            if capability in instance.capabilities and instance.client:
                return instance
        
        # Fallback to any available instance
        for instance in self.instances.values():
            if instance.client:
                return instance
        
        return None
    
    def _map_action(self, action: str) -> str:
        """Map Module Communicator actions to Aider actions"""
        action_map = {
            'generate_code': 'chat',
            'review_code': 'chat',
            'add_context': 'add_files',
            # Add more mappings
        }
        return action_map.get(action, action)
```

### 3.2 Configuration
```yaml
# config/adapters/aider.yaml
adapter:
  type: aider
  instances:
    - name: primary
      port: 8765
      model: gpt-4
      capabilities:
        - code_generation
        - general
        
    - name: claude
      port: 8766
      model: claude-3-opus-20240229
      capabilities:
        - code_review
        - documentation
        - refactoring
        
    - name: local
      port: 8767
      model: codellama:13b
      capabilities:
        - performance_optimization
        - security_analysis
        
    - name: fast
      port: 8768
      model: gpt-3.5-turbo
      capabilities:
        - quick_tasks
        - syntax_check
```

## Phase 4: Multi-Instance Manager (Week 6)

### 4.1 Instance Manager
```python
# aider/instance_manager.py
import subprocess
import psutil
import yaml
import asyncio
from typing import Dict, List

class AiderInstanceManager:
    def __init__(self, config_file='aider_instances.yaml'):
        self.config_file = config_file
        self.instances = {}
        self.processes = {}
        
    def load_config(self):
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
    
    async def start_all(self):
        """Start all configured instances"""
        config = self.load_config()
        
        for instance_config in config['instances']:
            await self.start_instance(instance_config)
    
    async def start_instance(self, config):
        """Start a single Aider daemon instance"""
        name = config['name']
        port = config['port']
        model = config['model']
        
        # Check if already running
        if name in self.processes:
            print(f"Instance {name} already running")
            return
        
        # Start daemon process
        cmd = [
            'python', '-m', 'aider.daemon',
            '--model', model,
            '--port', str(port)
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.processes[name] = process
        self.instances[name] = config
        
        # Wait for startup
        await asyncio.sleep(2)
        
        if process.poll() is None:
            print(f"Started instance {name} on port {port} with model {model}")
        else:
            print(f"Failed to start instance {name}")
            stderr = process.stderr.read()
            print(f"Error: {stderr.decode()}")
    
    def stop_all(self):
        """Stop all running instances"""
        for name, process in self.processes.items():
            process.terminate()
            process.wait()
            print(f"Stopped instance {name}")
        
        self.processes.clear()
    
    def status(self):
        """Get status of all instances"""
        status = {}
        
        for name, process in self.processes.items():
            if process.poll() is None:
                # Get process info
                p = psutil.Process(process.pid)
                status[name] = {
                    'status': 'running',
                    'pid': process.pid,
                    'cpu_percent': p.cpu_percent(),
                    'memory_mb': p.memory_info().rss / 1024 / 1024,
                    'port': self.instances[name]['port']
                }
            else:
                status[name] = {
                    'status': 'stopped',
                    'exit_code': process.returncode
                }
        
        return status

# CLI for instance management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['start', 'stop', 'status'])
    args = parser.parse_args()
    
    manager = AiderInstanceManager()
    
    if args.command == 'start':
        asyncio.run(manager.start_all())
    elif args.command == 'stop':
        manager.stop_all()
    elif args.command == 'status':
        status = manager.status()
        for name, info in status.items():
            print(f"{name}: {info}")
```

## Phase 5: Testing Framework (Week 7)

### 5.1 Integration Tests
```python
# tests/test_aider_integration.py
import pytest
import asyncio
from claude_coms.core.adapters.aider_adapter import AiderAdapter

@pytest.mark.asyncio
async def test_single_instance_communication():
    """Test basic communication with single Aider instance"""
    config = {
        'instances': [{
            'name': 'test',
            'port': 9999,
            'model': 'gpt-3.5-turbo',
            'capabilities': ['general']
        }]
    }
    
    adapter = AiderAdapter(config)
    await adapter.connect()
    
    response = await adapter.send({
        'action': 'generate_code',
        'message': 'Create a hello world function in Python'
    })
    
    assert response['success']
    assert 'def' in response['result']
    
@pytest.mark.asyncio
async def test_multi_instance_broadcast():
    """Test broadcasting to multiple instances"""
    config = {
        'instances': [
            {'name': 'instance1', 'port': 9998, 'model': 'gpt-4', 'capabilities': ['general']},
            {'name': 'instance2', 'port': 9997, 'model': 'claude-3', 'capabilities': ['general']}
        ]
    }
    
    adapter = AiderAdapter(config)
    await adapter.connect()
    
    responses = await adapter.broadcast({
        'action': 'generate_code',
        'message': 'Create a factorial function'
    })
    
    assert len(responses) == 2
    assert all(r['success'] for r in responses.values())
```

## Migration Strategy

### Step 1: Parallel Running
- Keep Claude Code integration active
- Deploy Aider instances alongside
- Route non-critical requests to Aider

### Step 2: Gradual Migration
- Move specific capabilities to Aider
- Monitor performance and reliability
- Gather user feedback

### Step 3: Full Cutover
- Disable Claude Code integration
- Update documentation
- Provide migration tools

## Performance Benchmarks

### Expected Metrics
- **Latency**: < 10ms for IPC (vs 50-100ms SQLite polling)
- **Throughput**: 100+ requests/second per instance
- **Concurrency**: 10+ simultaneous requests per instance
- **Memory**: ~500MB per instance (model-dependent)

## Success Metrics

1. **Week 2**: Daemon mode prototype working
2. **Week 4**: Single instance integration complete
3. **Week 6**: Multi-instance system operational
4. **Week 8**: Performance targets met
5. **Week 10**: Production deployment ready

## Next Steps

1. **Approval**: Get stakeholder buy-in
2. **Team Formation**: Assign developers
3. **Environment Setup**: Development infrastructure
4. **Kickoff**: Begin Phase 1 implementation
