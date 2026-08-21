from pathlib import Path


def test_sidebar_background_not_lowered_below_ctkframe_canvas():
    src = Path('ui/app_sidebar.py').read_text(encoding='utf-8')
    assert '\n        label.lower()\n' not in src
    assert 'label.lower(hijos[0])' in src
    assert 'label.place(x=0, y=0, relwidth=1, relheight=1)' in src


def test_sidebar_uses_full_surface_cover_wallpaper():
    src = Path('ui/app_sidebar.py').read_text(encoding='utf-8')
    assert 'ImageOps.fit' in src
    assert 'relwidth=1, relheight=1' in src
    assert '_FONDOS_SIDEBAR' in src
    assert 'ImageTk.PhotoImage' in src
    assert 'background_label = tk.Label' in src
