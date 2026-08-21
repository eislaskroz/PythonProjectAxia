from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wallpapers_retirados_de_levantamientos():
    vista = (ROOT / 'views' / 'levantamiento_view.py').read_text(encoding='utf-8')
    assert 'instalar_fondo_en_frame' not in vista
    assert not (ROOT / 'ui' / 'form_backgrounds.py').exists()
    assert not list((ROOT / 'assets').glob('fondo_*.png'))
