from typing import Any, Callable
from data.logger import create_logger
import importlib
import inspect
import sys
import os

logger = create_logger('AppLoader', index=False, ecosystem=False)


def register_by(register_funcname: str, app: Any, extra_process: Callable[..., bool] | None = None):
    apps_path = os.path.join(os.getcwd(), 'apps')
    for app_name in os.listdir(apps_path):
        if app_name.startswith('disable_'): continue
        app_path = os.path.join(apps_path, app_name)
        if not os.path.isdir(app_path): continue
        if not os.path.exists(os.path.join(app_path, '__init__.py')): continue
        # Add sub-app to import path
        sys.path.append(app_path)
        try:
            # Import sub-app
            module = importlib.import_module(f'apps.{app_name}')
            if not hasattr(module, register_funcname):
                # logger.error(f"App: {app_name} does not have {register_funcname}")
                continue
            # Get on_init object
            module_func = getattr(module, register_funcname)
            # If on_init is a router object, register routes
            if extra_process and extra_process(module_func, app):
                logger.info(f"Imported App: {app_name}")
            # If on_inits is a function
            elif callable(module_func):
                sig = inspect.signature(module_func)
                params = sig.parameters.values()
                # If only 1 parameter, and it's app. Then call (i.e., execute each app's on_init(app) function)
                if len(params) == 1 and list(params)[0].annotation == app.__class__:
                    module_func(app)
                    logger.info(f"Imported App: {app_name}")
                else:
                    logger.error(f"App: {app_name} {register_funcname} signature error")
            else:
                logger.error(f"App: {app_name} {register_funcname} type error")
        except Exception as e:
            logger.exception(f"Importing App: {app_name} Error: {e}")