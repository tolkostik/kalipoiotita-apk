"""
Σάρωση barcode με τον επίσημο σαρωτή της Google (ML Kit Code Scanner).

Τρόπος 1: απευθείας από την Python (pyjnius) – δεν χρειάζεται δικό μας κώδικα Java.
Τρόπος 2 (εφεδρικός): η Java κλάση org.poiotita.Scanner, αν υπάρχει στο APK.
"""
from kivy.utils import platform

IS_ANDROID = platform == "android"

_state = {"busy": False, "result": None, "error": None, "mode": None}
_keep = []          # κρατάμε ζωντανούς τους «ακροατές», για να μην τους σβήσει η μνήμη


def available():
    return IS_ANDROID


def _pyjnius_scan():
    from jnius import PythonJavaClass, autoclass, java_method

    class Success(PythonJavaClass):
        __javainterfaces__ = ["com/google/android/gms/tasks/OnSuccessListener"]
        __javacontext__ = "app"

        @java_method("(Ljava/lang/Object;)V")
        def onSuccess(self, obj):
            try:
                _state["result"] = obj.getRawValue()
            except Exception as e:  # noqa: BLE001
                _state["error"] = f"ανάγνωση αποτελέσματος: {e}"
            _state["busy"] = False

    class Failure(PythonJavaClass):
        __javainterfaces__ = ["com/google/android/gms/tasks/OnFailureListener"]
        __javacontext__ = "app"

        @java_method("(Ljava/lang/Exception;)V")
        def onFailure(self, e):
            try:
                _state["error"] = str(e.getMessage())
            except Exception:  # noqa: BLE001
                _state["error"] = "άγνωστο σφάλμα σαρωτή"
            _state["busy"] = False

    class Canceled(PythonJavaClass):
        __javainterfaces__ = ["com/google/android/gms/tasks/OnCanceledListener"]
        __javacontext__ = "app"

        @java_method("()V")
        def onCanceled(self):
            _state["error"] = "cancel"
            _state["busy"] = False

    from android.runnable import run_on_ui_thread

    GmsBarcodeScanning = autoclass("com.google.mlkit.vision.codescanner.GmsBarcodeScanning")
    act = autoclass("org.kivy.android.PythonActivity").mActivity

    @run_on_ui_thread
    def go():
        try:
            client = GmsBarcodeScanning.getClient(act)
            s, f, c = Success(), Failure(), Canceled()
            _keep[:] = [s, f, c, client]
            task = client.startScan()
            task.addOnSuccessListener(s)
            task.addOnFailureListener(f)
            task.addOnCanceledListener(c)
        except Exception as e:  # noqa: BLE001
            _state["error"] = f"άνοιγμα σαρωτή: {e}"
            _state["busy"] = False
    go()


def start():
    """Ξεκινά τη σάρωση. Σηκώνει εξαίρεση με εξήγηση αν δεν γίνεται με κανέναν τρόπο."""
    _state.update(busy=True, result=None, error=None)
    errors = []
    try:
        _pyjnius_scan()
        _state["mode"] = "py"
        return
    except Exception as e:  # noqa: BLE001
        errors.append(f"Τρόπος 1: {e}")
    try:
        from jnius import autoclass
        S = autoclass("org.poiotita.Scanner")
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        S.scan(act)
        _state["mode"] = "java"
        return
    except Exception as e:  # noqa: BLE001
        errors.append(f"Τρόπος 2: {e}")
    _state["busy"] = False
    raise RuntimeError(" | ".join(errors))


def poll():
    """(σε εξέλιξη, αποτέλεσμα, σφάλμα)"""
    if _state["mode"] == "java":
        from jnius import autoclass
        S = autoclass("org.poiotita.Scanner")
        return bool(S.busy), S.result, S.error
    return _state["busy"], _state["result"], _state["error"]
