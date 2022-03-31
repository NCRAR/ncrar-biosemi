import asyncio
import json
import subprocess
import websockets


class PSIController:

    def __init__(self, uri, logging_level='ERROR'):
        self.uri = uri
        self.logging_level = logging_level

    async def __aenter__(self):
        cmd_args = ['psi', 'biosemi-eeg', '--debug-level-console',
                    self.logging_level]
        process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE)
        self.ws = await websockets.connect(self.uri)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()
        await self.ws.close()

    async def start(self):
        await asyncio.gather(
            self.ws.send(json.dumps({'command': 'psi.controller.start'})),
            self.running()
        )

    async def running(self):
        while True:
            result = json.loads(await self.ws.recv())
            if result.get('event') == 'experiment_start':
                break

    async def stop(self):
        print('sending messages')
        await asyncio.gather(
            self.ws.send(json.dumps({'command': 'psi.controller.stop'})),
            #self.ws.send(json.dumps({'command': 'enaml.workbench.ui.close_window'})),
        )
        print('done sending')

    async def monitor(self, timeout):
        await asyncio.sleep(timeout)
        results = []
        while True:
            try:
                result = await asyncio.wait_for(self.ws.recv(), 0.001)
                result = json.loads(result)
                if result.get('event') == 'experiment_end':
                    print('Experiment ended')
                    raise Exception
                if 't0' in result:
                    md = result['metadata']
                    md['t0'] = result['t0']
                    results.append(md)
            except asyncio.TimeoutError:
                break
        return results
