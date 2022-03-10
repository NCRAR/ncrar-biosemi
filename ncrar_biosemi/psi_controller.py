import asyncio
import json
import subprocess
import websockets


class PSIController:

    def __init__(self, uri):
        self.uri = uri

    async def __aenter__(self):
        cmd_args = ['psi', 'biosemi-eeg', '--debug-level-console', 'ERROR']
        process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE)
        self.ws = await websockets.connect(self.uri)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()
        await self.ws.close()

    async def start(self):
        await self.ws.send(json.dumps({'command': 'psi.controller.start'}))
        while True:
            result = json.loads(await self.ws.recv())
            if result['event'] == 'experiment_start':
                break

    async def stop(self):
        await self.ws.send(json.dumps({'command': 'psi.controller.stop'}))

    async def monitor(self, timeout):
        await asyncio.sleep(timeout)
        results = []
        while True:
            try:
                result = await asyncio.wait_for(self.ws.recv(), 0.001)
                result = json.loads(result)
                if result.get('event') == 'experiment_end':
                    raise Exception
                results.append(result)
            except asyncio.TimeoutError:
                break
        return results
