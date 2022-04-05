import time
from threading import Thread
import sounddevice


def run_babyface():
    import importlib

    from ncrar_biosemi.experiments import load_stim_set
    from ncrar_audio import babyface, cpod

    print('Initializing Babyface')
    sd = babyface.Babyface('earphones', 'XLR', use_osc=False)
    print('Initializing cPod')
    cp = cpod.CPod()
    wav_files = load_stim_set(sd.fs)

    print('Starting cPod')
    with cp.set_code(1):
        print('Playing sound')
        sd.play_stereo(wav_files['ka'])
    print('sleeping')
    time.sleep(0.5)


thread = Thread(target=run_babyface)
thread.start()
thread.join()
