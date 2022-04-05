import time
import asyncio
from ncrar_biosemi.psi_controller import PSIController


async def main(autostart=True):
    async with PSIController('ws://localhost:8765') as psi:
        print('Successfully opened controller')
        if autostart:
            time.sleep(2)
            await psi.start()
        else:
            await psi.running()
        print('Controller running')

        time.sleep(2)
        await psi.stop()
        print('Controller stopped')


if __name__ == '__main__':
    asyncio.run(main(False))
