import importlib
import pkgutil
from flask_restx import Namespace, Api

def load_routes( rest_api: Api, package: str = "app.routes") -> None:
    """
    Dynamically import all modules under `package` and register any Flask-RESTX Namespace found.

    Enterprise-style contract:
      - each route module exports a Namespace object either as `api` (enterprise style)
        or `ns` (your current style).
    """
    pkg = importlib.import_module(package)
    
    for modinfo in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        if modinfo.ispkg:
            continue  # skip sub-packages, only load modules

        module = importlib.import_module(modinfo.name)

        namespace = getattr(module, "api", None) or getattr(module, "ns", None)
        if isinstance(namespace, Namespace):
            rest_api.add_namespace(namespace)
