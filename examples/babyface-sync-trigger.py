import time

from ncrar_audio import babyface, cpod
from ncrar_biosemi.experiments import load_stim_set

sd = babyface.Babyface('earphones', 'XLR', use_osc=False)
cp = cpod.CPod()
wav_files = load_stim_set(sd.fs)
with cp.set_code(1):
    sd.play_stereo(wav_files['ka'])
time.sleep(0.5)
