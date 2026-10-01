"""Responsive layout helpers for AXIA Desktop.

The application is desktop-first. These helpers preserve the existing visual
identity while adapting spacing/sidebar width to the *actual* window area,
which also accounts for Windows DPI/display scaling.
"""

def install_responsive_shell(app, sidebar=None):
    state = {"after": None, "mode": None}

    def apply(_event=None):
        try:
            if state["after"]:
                app.after_cancel(state["after"])
        except Exception:
            pass
        def _do():
            try:
                w = max(1, app.winfo_width())
                h = max(1, app.winfo_height())
                mode = "compact" if (w < 1450 or h < 820) else "normal"
                if mode == state["mode"]:
                    return
                state["mode"] = mode
                app._axia_responsive_mode = mode
                sb = sidebar or getattr(app, "sidebar", None)
                if sb is not None and sb.winfo_exists():
                    sb.configure(width=220 if mode == "compact" else 230)
            except Exception:
                pass
        try:
            state["after"] = app.after(80, _do)
        except Exception:
            _do()

    app.bind("<Configure>", apply, add="+")
    app.after_idle(apply)
    return apply
